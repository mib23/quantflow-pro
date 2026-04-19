from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_sync_engine
from app.core.exceptions import ApiException
from app.core.ids import coerce_uuid
from app.core.models import (
    AccountBalanceModel,
    AuditLogModel,
    BrokerAccountModel,
    RiskEventModel,
    RiskRuleModel,
    RiskRuleVersionModel,
)
from app.core.settings import get_settings
from app.modules.risk.schemas import (
    PreTradeCheckRequest,
    RiskCheckResult,
    RiskEventItem,
    RiskEventListResponse,
    RiskHardLimits,
    RiskRestrictions,
    RiskRule,
    RiskRuleCreateRequest,
    RiskRuleListResponse,
    RiskRuleUpdateRequest,
    RiskRuleVersion,
    RiskSummaryResponse,
    RiskScope,
)


@lru_cache
def get_risk_session_factory() -> Callable[[], Session]:
    engine = create_sync_engine(get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class RiskRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def get_broker_account(self, broker_account_id: str) -> dict[str, object] | None:
        with self._session_factory() as session:
            row = session.execute(
                select(BrokerAccountModel).where(BrokerAccountModel.id == self._coerce_uuid(broker_account_id))
            ).scalars().first()
        return self._serialize_account(row) if row is not None else None

    def get_primary_account(self, user_id: str) -> dict[str, object] | None:
        with self._session_factory() as session:
            row = session.execute(
                select(BrokerAccountModel)
                .where(BrokerAccountModel.user_id == self._coerce_uuid(user_id))
                .order_by(BrokerAccountModel.created_at.desc(), BrokerAccountModel.id.asc())
            ).scalars().first()
        return self._serialize_account(row) if row is not None else None

    def get_latest_balance(self, broker_account_id: str) -> dict[str, object] | None:
        with self._session_factory() as session:
            row = session.execute(
                select(AccountBalanceModel)
                .where(AccountBalanceModel.broker_account_id == coerce_uuid(broker_account_id))
                .order_by(AccountBalanceModel.snapshot_at.desc(), AccountBalanceModel.id.desc())
            ).scalars().first()
        return self._serialize_balance(row) if row is not None else None

    def list_rules(
        self,
        *,
        user_id: str,
        broker_account_id: str | None = None,
        enabled: bool | None = None,
        rule_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RiskRuleListResponse:
        with self._session_factory() as session:
            rows = session.execute(
                select(RiskRuleModel)
                .where(RiskRuleModel.created_by == self._coerce_uuid(user_id))
                .order_by(RiskRuleModel.updated_at.desc(), RiskRuleModel.version.desc(), RiskRuleModel.id.desc())
            ).scalars().all()

        filtered = [
            row
            for row in rows
            if (enabled is None or bool(row.enabled) == enabled)
            and (rule_type is None or str(row.rule_type).upper() == rule_type.upper())
            and (broker_account_id is None or self._rule_applies_to_account(row, broker_account_id))
        ]
        total = len(filtered)
        start = (page - 1) * page_size
        items = [self._serialize_rule(row) for row in filtered[start : start + page_size]]
        return RiskRuleListResponse(items=items, page=page, page_size=page_size, total=total)

    def get_rule(self, rule_id: str) -> RiskRule | None:
        with self._session_factory() as session:
            row = session.execute(select(RiskRuleModel).where(RiskRuleModel.id == self._coerce_uuid(rule_id))).scalars().first()
        if row is None:
            return None
        rule = self._serialize_rule(row)
        rule.history = self.list_rule_versions(rule_id)
        return rule

    def list_rule_versions(self, rule_id: str) -> list[RiskRuleVersion]:
        with self._session_factory() as session:
            rows = session.execute(
                select(RiskRuleVersionModel)
                .where(RiskRuleVersionModel.risk_rule_id == self._coerce_uuid(rule_id))
                .order_by(RiskRuleVersionModel.version.desc(), RiskRuleVersionModel.changed_at.desc())
            ).scalars().all()
        return [self._serialize_version(row) for row in rows]

    def create_rule(self, payload: RiskRuleCreateRequest, *, created_by: str, trace_id: str | None = None) -> RiskRule:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                row = RiskRuleModel(
                    id=uuid4(),
                    created_by=coerce_uuid(created_by),
                    name=payload.name,
                    description=payload.description,
                    scope=self._scope_label(payload.scope),
                    scope_accounts=payload.scope.account_ids,
                    scope_symbols=payload.scope.symbols,
                    rule_type=payload.rule_type,
                    config=payload.config,
                    enabled=payload.enabled,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
                self._append_version(session, row, change_reason=payload.change_reason or "Rule created.", changed_by=created_by, changed_at=now)
                self._append_audit_log(
                    session,
                    user_id=created_by,
                    resource_type="RISK_RULE",
                    resource_id=str(row.id),
                    action="RISK_RULE_CREATED",
                    after_state=self._rule_snapshot(row),
                    trace_id=trace_id,
                )
        rule = self.get_rule(str(row.id))
        if rule is None:
            raise ValueError("Risk rule could not be created.")
        return rule

    def update_rule(
        self,
        rule_id: str,
        payload: RiskRuleUpdateRequest,
        *,
        changed_by: str,
        trace_id: str | None = None,
    ) -> RiskRule:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                row = session.execute(select(RiskRuleModel).where(RiskRuleModel.id == self._coerce_uuid(rule_id))).scalars().first()
                if row is None:
                    raise ApiException("RISK_RULE_NOT_FOUND", "Risk rule not found.", status.HTTP_404_NOT_FOUND)

                before = self._rule_snapshot(row)
                if payload.name is not None:
                    row.name = payload.name
                if payload.description is not None:
                    row.description = payload.description
                if payload.scope is not None:
                    row.scope = self._scope_label(payload.scope)
                    row.scope_accounts = payload.scope.account_ids
                    row.scope_symbols = payload.scope.symbols
                if payload.config is not None:
                    row.config = self._normalize_config(str(row.rule_type), payload.config)
                row.version += 1
                row.updated_at = now
                session.flush()
                self._append_version(session, row, change_reason=payload.change_reason or "Rule updated.", changed_by=changed_by, changed_at=now)
                self._append_audit_log(
                    session,
                    user_id=changed_by,
                    resource_type="RISK_RULE",
                    resource_id=str(row.id),
                    action="RISK_RULE_UPDATED",
                    before_state=before,
                    after_state=self._rule_snapshot(row),
                    trace_id=trace_id,
                )
        rule = self.get_rule(rule_id)
        if rule is None:
            raise ValueError("Risk rule could not be updated.")
        return rule

    def set_rule_enabled(
        self,
        rule_id: str,
        *,
        enabled: bool,
        changed_by: str,
        trace_id: str | None = None,
    ) -> RiskRule:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                row = session.execute(select(RiskRuleModel).where(RiskRuleModel.id == self._coerce_uuid(rule_id))).scalars().first()
                if row is None:
                    raise ApiException("RISK_RULE_NOT_FOUND", "Risk rule not found.", status.HTTP_404_NOT_FOUND)

                before = self._rule_snapshot(row)
                row.enabled = enabled
                row.version += 1
                row.updated_at = now
                session.flush()
                self._append_version(
                    session,
                    row,
                    change_reason="Rule activated." if enabled else "Rule deactivated.",
                    changed_by=changed_by,
                    changed_at=now,
                )
                self._append_audit_log(
                    session,
                    user_id=changed_by,
                    resource_type="RISK_RULE",
                    resource_id=str(row.id),
                    action="RISK_RULE_ACTIVATED" if enabled else "RISK_RULE_DEACTIVATED",
                    before_state=before,
                    after_state=self._rule_snapshot(row),
                    trace_id=trace_id,
                )
        rule = self.get_rule(rule_id)
        if rule is None:
            raise ValueError("Risk rule could not be updated.")
        return rule

    def list_events(
        self,
        *,
        user_id: str,
        broker_account_id: str | None = None,
        rule_id: str | None = None,
        severity: str | None = None,
        status_value: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RiskEventListResponse:
        with self._session_factory() as session:
            rows = session.execute(
                select(RiskEventModel, RiskRuleModel.name, RiskRuleModel.rule_type)
                .join(RiskRuleModel, RiskRuleModel.id == RiskEventModel.risk_rule_id)
                .join(BrokerAccountModel, BrokerAccountModel.id == RiskEventModel.broker_account_id)
                .where(BrokerAccountModel.user_id == self._coerce_uuid(user_id))
                .order_by(RiskEventModel.occurred_at.desc(), RiskEventModel.id.desc())
            ).all()

        items: list[RiskEventItem] = []
        for event_row, rule_name, rule_type in rows:
            if broker_account_id is not None and str(event_row.broker_account_id) != broker_account_id:
                continue
            if rule_id is not None and str(event_row.risk_rule_id) != rule_id:
                continue
            if severity is not None and str(event_row.severity).upper() != severity.upper():
                continue
            if status_value is not None and str(event_row.status).upper() != status_value.upper():
                continue
            items.append(self._serialize_event(event_row, rule_name=rule_name, rule_type=rule_type))

        total = len(items)
        start = (page - 1) * page_size
        return RiskEventListResponse(items=items[start : start + page_size], page=page, page_size=page_size, total=total)

    def list_recent_events(self, *, user_id: str, broker_account_id: str | None = None, limit: int = 10) -> list[RiskEventItem]:
        return self.list_events(user_id=user_id, broker_account_id=broker_account_id, page=1, page_size=limit).items

    def get_summary(self, *, user_id: str, broker_account_id: str | None = None) -> RiskSummaryResponse:
        account = self._resolve_account(user_id=user_id, broker_account_id=broker_account_id)
        if account is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        latest_balance = self.get_latest_balance(str(account["id"]))

        with self._session_factory() as session:
            rule_rows = session.execute(
                select(RiskRuleModel).where(RiskRuleModel.created_by == self._coerce_uuid(user_id))
            ).scalars().all()

        active_rules = [row for row in rule_rows if bool(row.enabled) and self._rule_applies_to_account(row, str(account["id"]))]
        recent_events = self.list_recent_events(user_id=user_id, broker_account_id=str(account["id"]), limit=10)
        all_recent_events = self.list_events(user_id=user_id, broker_account_id=str(account["id"]), page=1, page_size=1000).items
        reference_candidates = [self._as_utc_datetime(event.occurred_at) for event in all_recent_events]
        if latest_balance is not None and latest_balance.get("snapshot_at") is not None:
            reference_candidates.append(self._as_utc_datetime(latest_balance["snapshot_at"]))
        reference_time = max(reference_candidates, default=datetime.now(UTC))
        window_start = reference_time - self._day_delta()
        total_events_24h = sum(1 for event in all_recent_events if self._as_utc_datetime(event.occurred_at) >= window_start)
        blocked_orders_today = sum(
            1
            for event in all_recent_events
            if self._as_utc_datetime(event.occurred_at) >= window_start
            and any(token in event.status.upper() for token in ("BLOCK", "REJECT", "DENY"))
        )
        unresolved_events = sum(1 for event in all_recent_events if event.status.upper() not in {"RESOLVED", "CLOSED"})
        equity = Decimal(str((latest_balance or {}).get("equity") or 0))
        max_single_order_value = self._extract_min_notional(active_rules)
        max_daily_loss = self._extract_min_daily_loss(active_rules)
        max_position_size_percent = float((Decimal(str(max_single_order_value)) / equity * Decimal("100")) if max_single_order_value and equity > 0 else 0)

        return RiskSummaryResponse(
            account_id=str(account["id"]),
            hard_limits=RiskHardLimits(
                max_daily_loss=max_daily_loss,
                max_single_order_value=max_single_order_value,
                max_position_size_percent=round(max_position_size_percent, 2) if max_position_size_percent else 0,
            ),
            restrictions=RiskRestrictions(
                restricted_symbols=self._extract_restricted_symbols(active_rules),
                market_hours_only=any(str(rule.rule_type).upper() == "TRADING_WINDOW" for rule in active_rules),
            ),
            recent_events=recent_events,
            active_rules=len(active_rules),
            total_events_24h=total_events_24h,
            triggered_today=total_events_24h,
            blocked_orders_today=blocked_orders_today,
            unresolved_events=unresolved_events,
            updated_at=reference_time,
        )

    def evaluate_pre_trade(
        self,
        request: PreTradeCheckRequest,
        *,
        user_id: str | None = None,
        broker_account: dict[str, object] | None = None,
        persist: bool = True,
        trace_id: str | None = None,
    ) -> RiskCheckResult:
        account = broker_account or self._resolve_account(user_id=user_id, broker_account_id=request.broker_account_id)
        if account is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        if user_id is not None and str(account["user_id"]) != user_id:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)

        balance = self.get_latest_balance(str(account["id"]))
        evaluated_at = request.evaluated_at or datetime.now(UTC)
        rules = self._list_applicable_rules(user_id=str(account["user_id"]), broker_account_id=str(account["id"]), symbol=request.symbol)
        events: list[RiskEventItem] = []
        for rule in rules:
            event = self._evaluate_rule(rule, request, account=account, balance=balance, evaluated_at=evaluated_at)
            if event is not None:
                events.append(event)

        reason = "; ".join(event.reason for event in events) if events else None
        if persist and events:
            events = self.record_risk_events(
                events,
                account_id=str(account["id"]),
                user_id=str(account["user_id"]),
                client_order_id=request.client_order_id,
                idempotency_key=request.idempotency_key,
                trace_id=trace_id,
            )

        return RiskCheckResult(
            passed=not events,
            reason=reason,
            events=events,
            rule_ids=[event.rule_id for event in events],
            checked_at=evaluated_at,
        )

    def record_risk_events(
        self,
        events: list[RiskEventItem],
        *,
        account_id: str,
        user_id: str,
        client_order_id: str | None = None,
        idempotency_key: str | None = None,
        trace_id: str | None = None,
    ) -> list[RiskEventItem]:
        persisted: list[RiskEventItem] = []
        with self._session_factory() as session:
            with session.begin():
                for event in events:
                    dedupe_key = self._build_dedupe_key(
                        account_id=account_id,
                        client_order_id=client_order_id,
                        idempotency_key=idempotency_key,
                        rule_id=event.rule_id,
                        event_type=event.event_type,
                    )
                    if dedupe_key is not None:
                        existing = session.execute(select(RiskEventModel).where(RiskEventModel.dedupe_key == dedupe_key)).scalars().first()
                        if existing is not None:
                            persisted.append(self._serialize_event(existing, rule_name=event.rule_name, rule_type=event.rule_type))
                            continue

                    row = RiskEventModel(
                        id=uuid4(),
                        risk_rule_id=UUID(event.rule_id),
                        broker_account_id=UUID(account_id),
                        runtime_instance_id=UUID(event.runtime_instance_id) if event.runtime_instance_id else None,
                        order_id=None,
                        client_order_id=client_order_id,
                        severity=event.severity,
                        event_type=event.event_type,
                        reason=event.reason,
                        status=event.status,
                        payload=event.payload,
                        dedupe_key=dedupe_key,
                        occurred_at=event.occurred_at,
                    )
                    session.add(row)
                    session.flush()
                    self._append_audit_log(
                        session,
                        user_id=user_id,
                        resource_type="RISK_EVENT",
                        resource_id=str(row.id),
                        action="RISK_EVENT_TRIGGERED",
                        after_state=self._event_snapshot(row),
                        trace_id=trace_id,
                    )
                    persisted.append(self._serialize_event(row, rule_name=event.rule_name, rule_type=event.rule_type))

        for event in persisted:
            self._publish_risk_event(event)
        return persisted

    def _resolve_account(self, *, user_id: str | None, broker_account_id: str | None) -> dict[str, object] | None:
        with self._session_factory() as session:
            stmt = select(BrokerAccountModel)
            if broker_account_id is not None:
                stmt = stmt.where(BrokerAccountModel.id == self._coerce_uuid(broker_account_id))
            elif user_id is not None:
                stmt = stmt.where(BrokerAccountModel.user_id == self._coerce_uuid(user_id)).order_by(
                    BrokerAccountModel.created_at.desc(),
                    BrokerAccountModel.id.asc(),
                )
            row = session.execute(stmt).scalars().first()
        return self._serialize_account(row) if row is not None else None

    def _list_applicable_rules(self, *, user_id: str, broker_account_id: str, symbol: str) -> list[RiskRuleModel]:
        with self._session_factory() as session:
            rows = session.execute(
                select(RiskRuleModel).where(
                    RiskRuleModel.created_by == self._coerce_uuid(user_id),
                    RiskRuleModel.enabled.is_(True),
                )
            ).scalars().all()
        return [row for row in rows if self._rule_applies_to_context(row, broker_account_id, symbol)]

    def _evaluate_rule(
        self,
        rule: RiskRuleModel,
        request: PreTradeCheckRequest,
        *,
        account: dict[str, object],
        balance: dict[str, object] | None,
        evaluated_at: datetime,
    ) -> RiskEventItem | None:
        rule_type = str(rule.rule_type).upper()
        config = dict(rule.config or {})
        symbol = request.symbol.upper()
        if rule_type == "MAX_SINGLE_ORDER_NOTIONAL":
            max_notional = Decimal(str(config.get("max_notional", 0)))
            effective_price = self._effective_price(request, symbol)
            notional = Decimal(str(request.quantity)) * effective_price
            if max_notional > 0 and notional > max_notional:
                return self._build_event(
                    rule,
                    account_id=str(account["id"]),
                    client_order_id=request.client_order_id,
                    request=request,
                    evaluated_at=evaluated_at,
                    severity="HIGH",
                    reason=f"Order notional {float(notional):.2f} exceeds max_notional {float(max_notional):.2f}.",
                    payload={"max_notional": float(max_notional), "effective_price": float(effective_price), "notional": float(notional)},
                )
        elif rule_type == "RESTRICTED_SYMBOLS":
            blocked = {str(item).upper() for item in config.get("symbols", [])}
            if symbol in blocked:
                return self._build_event(
                    rule,
                    account_id=str(account["id"]),
                    client_order_id=request.client_order_id,
                    request=request,
                    evaluated_at=evaluated_at,
                    severity="HIGH",
                    reason=f"Symbol {symbol} is restricted by rule {rule.name}.",
                    payload={"restricted_symbols": sorted(blocked)},
                )
        elif rule_type == "TRADING_WINDOW":
            if not self._is_in_trading_window(config, evaluated_at):
                return self._build_event(
                    rule,
                    account_id=str(account["id"]),
                    client_order_id=request.client_order_id,
                    request=request,
                    evaluated_at=evaluated_at,
                    severity="MEDIUM",
                    reason=f"Order outside permitted trading window for rule {rule.name}.",
                    payload={"window": config},
                )
        elif rule_type == "DAILY_LOSS_THRESHOLD":
            threshold = Decimal(str(config.get("max_daily_loss", 0)))
            pnl = Decimal(str((balance or {}).get("day_pnl") or 0))
            if threshold > 0 and pnl <= threshold * Decimal("-1"):
                return self._build_event(
                    rule,
                    account_id=str(account["id"]),
                    client_order_id=request.client_order_id,
                    request=request,
                    evaluated_at=evaluated_at,
                    severity="CRITICAL",
                    reason=f"Daily loss {float(abs(pnl)):.2f} exceeds threshold {float(threshold):.2f}.",
                    payload={"max_daily_loss": float(threshold), "day_pnl": float(pnl)},
                )
        return None

    @staticmethod
    def _effective_price(request: PreTradeCheckRequest, symbol: str) -> Decimal:
        if request.limit_price is not None:
            return Decimal(str(request.limit_price))
        if request.reference_price is not None:
            return Decimal(str(request.reference_price))
        from app.modules.market_data.service import get_latest_quote

        quote = get_latest_quote(symbol)
        return Decimal(str(quote.last or quote.bid or quote.ask or 0))

    @staticmethod
    def _build_event(
        rule: RiskRuleModel,
        *,
        account_id: str,
        client_order_id: str | None,
        request: PreTradeCheckRequest,
        evaluated_at: datetime,
        severity: str,
        reason: str,
        payload: dict[str, object],
    ) -> RiskEventItem:
        return RiskEventItem(
            id=str(uuid4()),
            rule_id=str(rule.id),
            rule_name=str(rule.name),
            rule_type=str(rule.rule_type),
            account_id=account_id,
            runtime_instance_id=request.runtime_instance_id,
            client_order_id=client_order_id,
            order_id=None,
            severity=severity,
            event_type="risk.rule_triggered",
            status="BLOCKED",
            reason=reason,
            message=reason,
            payload={
                "account_id": account_id,
                "client_order_id": client_order_id,
                "idempotency_key": request.idempotency_key,
                "symbol": request.symbol,
                "side": request.side,
                "order_type": request.order_type,
                "quantity": float(request.quantity),
                **payload,
            },
            occurred_at=evaluated_at,
        )

    @staticmethod
    def _is_in_trading_window(config: Mapping[str, object], evaluated_at: datetime) -> bool:
        try:
            from zoneinfo import ZoneInfo

            local_dt = evaluated_at.astimezone(ZoneInfo(str(config.get("timezone") or "America/New_York")))
        except Exception:
            local_dt = evaluated_at
        weekdays = [str(value).upper()[:3] for value in (config.get("weekdays") or [])] or ["MON", "TUE", "WED", "THU", "FRI"]
        if local_dt.strftime("%a").upper()[:3] not in weekdays:
            return False
        start_time = str(config.get("start_time") or "09:30")
        end_time = str(config.get("end_time") or "16:00")
        try:
            start_hour, start_minute = (int(part) for part in start_time.split(":", 1))
            end_hour, end_minute = (int(part) for part in end_time.split(":", 1))
        except Exception:
            return True
        now_minutes = local_dt.hour * 60 + local_dt.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        if start_minutes <= end_minutes:
            return start_minutes <= now_minutes <= end_minutes
        return now_minutes >= start_minutes or now_minutes <= end_minutes

    def _rule_applies_to_context(self, rule: RiskRuleModel, broker_account_id: str, symbol: str | None) -> bool:
        account_ids = [str(value) for value in (rule.scope_accounts or []) if str(value).strip()]
        symbols = [str(value).upper() for value in (rule.scope_symbols or []) if str(value).strip()]
        if account_ids and broker_account_id not in account_ids:
            return False
        if symbols and symbol and symbol.upper() not in symbols:
            return False
        return True

    def _rule_applies_to_account(self, rule: RiskRuleModel, broker_account_id: str) -> bool:
        return self._rule_applies_to_context(rule, broker_account_id, symbol=None)

    @staticmethod
    def _extract_min_notional(rules: Iterable[RiskRuleModel]) -> float | None:
        values = [float(rule.config.get("max_notional")) for rule in rules if str(rule.rule_type).upper() == "MAX_SINGLE_ORDER_NOTIONAL" and rule.config.get("max_notional") is not None]
        return min(values) if values else None

    @staticmethod
    def _extract_min_daily_loss(rules: Iterable[RiskRuleModel]) -> float | None:
        values = [float(rule.config.get("max_daily_loss")) for rule in rules if str(rule.rule_type).upper() == "DAILY_LOSS_THRESHOLD" and rule.config.get("max_daily_loss") is not None]
        return min(values) if values else None

    @staticmethod
    def _extract_restricted_symbols(rules: Iterable[RiskRuleModel]) -> list[str]:
        symbols: list[str] = []
        for rule in rules:
            if str(rule.rule_type).upper() != "RESTRICTED_SYMBOLS":
                continue
            for symbol in rule.config.get("symbols", []):
                cleaned = str(symbol).upper()
                if cleaned and cleaned not in symbols:
                    symbols.append(cleaned)
        return symbols

    @staticmethod
    def _scope_label(scope: RiskScope) -> str:
        if scope.account_ids and scope.symbols:
            return "ACCOUNT_AND_SYMBOL"
        if scope.account_ids:
            return "ACCOUNT"
        if scope.symbols:
            return "SYMBOL"
        return "GLOBAL"

    @staticmethod
    def _serialize_account(row: BrokerAccountModel) -> dict[str, object]:
        return {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "broker_name": row.broker_name,
            "broker_account_no": row.broker_account_no,
            "external_account_id": row.external_account_id,
            "environment": row.environment,
            "status": row.status,
        }

    @staticmethod
    def _serialize_balance(row: AccountBalanceModel) -> dict[str, object]:
        return {
            "id": str(row.id),
            "broker_account_id": str(row.broker_account_id),
            "equity": float(row.equity),
            "cash": float(row.cash),
            "buying_power": float(row.buying_power),
            "day_pnl": float(row.day_pnl),
            "snapshot_at": row.snapshot_at,
        }

    def _serialize_rule(self, row: RiskRuleModel) -> RiskRule:
        return RiskRule(
            id=str(row.id),
            name=str(row.name or "Unnamed risk rule"),
            description=row.description,
            rule_type=str(row.rule_type),
            scope=RiskScope(
                account_ids=[str(value) for value in (row.scope_accounts or [])],
                symbols=[str(value).upper() for value in (row.scope_symbols or [])],
            ),
            config=dict(row.config or {}),
            enabled=bool(row.enabled),
            version=int(row.version),
            created_by=str(row.created_by),
            created_at=row.created_at,
            updated_at=row.updated_at,
            history=self.list_rule_versions(str(row.id)),
        )

    @staticmethod
    def _serialize_version(row: RiskRuleVersionModel) -> RiskRuleVersion:
        return RiskRuleVersion(
            id=str(row.id),
            rule_id=str(row.risk_rule_id),
            version=int(row.version),
            snapshot=dict(row.snapshot or {}),
            change_reason=row.change_reason,
            changed_by=str(row.changed_by),
            changed_at=row.changed_at,
        )

    @staticmethod
    def _serialize_event(row: RiskEventModel, *, rule_name: str, rule_type: str) -> RiskEventItem:
        return RiskEventItem(
            id=str(row.id),
            rule_id=str(row.risk_rule_id),
            rule_name=rule_name,
            rule_type=rule_type,
            account_id=str(row.broker_account_id),
            runtime_instance_id=str(row.runtime_instance_id) if row.runtime_instance_id is not None else None,
            client_order_id=row.client_order_id,
            order_id=str(row.order_id) if row.order_id is not None else None,
            severity=str(row.severity),
            event_type=row.event_type,
            status=str(row.status),
            reason=row.reason,
            message=row.reason,
            payload=dict(row.payload or {}),
            occurred_at=row.occurred_at,
        )

    @staticmethod
    def _rule_snapshot(row: RiskRuleModel) -> dict[str, object]:
        return {
            "id": str(row.id),
            "name": row.name,
            "description": row.description,
            "rule_type": str(row.rule_type),
            "scope": {
                "account_ids": [str(value) for value in (row.scope_accounts or [])],
                "symbols": [str(value).upper() for value in (row.scope_symbols or [])],
            },
            "config": dict(row.config or {}),
            "enabled": bool(row.enabled),
            "version": int(row.version),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _event_snapshot(row: RiskEventModel) -> dict[str, object]:
        return {
            "id": str(row.id),
            "rule_id": str(row.risk_rule_id),
            "account_id": str(row.broker_account_id),
            "runtime_instance_id": str(row.runtime_instance_id) if row.runtime_instance_id is not None else None,
            "client_order_id": row.client_order_id,
            "severity": row.severity,
            "event_type": row.event_type,
            "reason": row.reason,
            "status": row.status,
            "payload": dict(row.payload or {}),
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        }

    @staticmethod
    def _append_version(
        session: Session,
        row: RiskRuleModel,
        *,
        change_reason: str | None,
        changed_by: str,
        changed_at: datetime,
    ) -> None:
        session.add(
            RiskRuleVersionModel(
                id=uuid4(),
                risk_rule_id=row.id,
                version=int(row.version),
                snapshot=RiskRepository._rule_snapshot(row),
                change_reason=change_reason,
                changed_by=UUID(changed_by),
                changed_at=changed_at,
            )
        )

    @staticmethod
    def _append_audit_log(
        session: Session,
        *,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        before_state: dict[str, object] | None = None,
        after_state: dict[str, object] | None = None,
        trace_id: str | None = None,
    ) -> None:
        session.add(
            AuditLogModel(
                id=uuid4(),
                user_id=UUID(user_id),
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                before_state=before_state,
                after_state=after_state,
                trace_id=trace_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _build_dedupe_key(
        *,
        account_id: str,
        client_order_id: str | None,
        idempotency_key: str | None,
        rule_id: str,
        event_type: str,
    ) -> str | None:
        reference = idempotency_key or client_order_id
        if not reference:
            return None
        return "::".join([account_id, reference, rule_id, event_type])

    @staticmethod
    def _normalize_config(rule_type: str, config: dict[str, object]) -> dict[str, object]:
        from app.modules.risk.schemas import _validate_rule_config

        return _validate_rule_config(rule_type, config)  # type: ignore[arg-type]

    def _publish_risk_event(self, event: RiskEventItem) -> None:
        try:
            import asyncio
            import inspect

            from app.core.realtime import realtime_hub

            loop = asyncio.get_running_loop()
            publish_result = realtime_hub.publish(
                f"risk.events.{event.account_id}",
                event.event_type,
                {
                    "rule_id": event.rule_id,
                    "rule_name": event.rule_name,
                    "rule_type": event.rule_type,
                    "account_id": event.account_id,
                    "runtime_instance_id": event.runtime_instance_id,
                    "client_order_id": event.client_order_id,
                    "severity": event.severity,
                    "message": event.message,
                    "reason": event.reason,
                    "status": event.status,
                    "occurred_at": event.occurred_at.isoformat(),
                },
            )
            if inspect.isawaitable(publish_result):
                loop.create_task(publish_result)
        except RuntimeError:
            import asyncio
            import inspect

            publish_result = realtime_hub.publish(
                f"risk.events.{event.account_id}",
                event.event_type,
                {
                    "rule_id": event.rule_id,
                    "rule_name": event.rule_name,
                    "rule_type": event.rule_type,
                    "account_id": event.account_id,
                    "runtime_instance_id": event.runtime_instance_id,
                    "client_order_id": event.client_order_id,
                    "severity": event.severity,
                    "message": event.message,
                    "reason": event.reason,
                    "status": event.status,
                    "occurred_at": event.occurred_at.isoformat(),
                },
            )
            if inspect.isawaitable(publish_result):
                asyncio.run(publish_result)

    @staticmethod
    def _coerce_uuid(value: str):
        return coerce_uuid(value)

    @staticmethod
    def _as_utc_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _day_delta():
        from datetime import timedelta

        return timedelta(days=1)
