from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import (
    BrokerAccountModel,
    RiskEventModel,
    RiskRuleModel,
    RiskRuleVersionModel,
    UserModel,
)
from app.modules.risk.schemas import _validate_rule_config


DEFAULT_RISK_RULES: tuple[dict[str, Any], ...] = (
    {
        "name": "Single order notional limit",
        "description": "Block orders whose notional exceeds the account limit.",
        "rule_type": "MAX_SINGLE_ORDER_NOTIONAL",
        "scope": "ACCOUNT",
        "scope_symbols": [],
        "config": {"max_notional": 50000.0},
        "enabled": True,
        "change_reason": "Seeded baseline risk rule.",
    },
    {
        "name": "Restricted symbols",
        "description": "Block trading in restricted symbols.",
        "rule_type": "RESTRICTED_SYMBOLS",
        "scope": "ACCOUNT_AND_SYMBOL",
        "scope_symbols": ["GME", "AMC", "DOGE"],
        "config": {"symbols": ["GME", "AMC", "DOGE"]},
        "enabled": True,
        "change_reason": "Seeded baseline risk rule.",
    },
    {
        "name": "Trading hours",
        "description": "Only allow trades inside the regular session.",
        "rule_type": "TRADING_WINDOW",
        "scope": "ACCOUNT",
        "scope_symbols": [],
        "config": {
            "start_time": "09:30",
            "end_time": "16:00",
            "timezone": "America/New_York",
            "weekdays": ["MON", "TUE", "WED", "THU", "FRI"],
        },
        "enabled": True,
        "change_reason": "Seeded baseline risk rule.",
    },
    {
        "name": "Daily loss threshold",
        "description": "Block new orders after the account day loss limit is hit.",
        "rule_type": "DAILY_LOSS_THRESHOLD",
        "scope": "ACCOUNT",
        "scope_symbols": [],
        "config": {"max_daily_loss": 5000.0},
        "enabled": True,
        "change_reason": "Seeded baseline risk rule.",
    },
)

DEFAULT_RISK_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "rule_type": "MAX_SINGLE_ORDER_NOTIONAL",
        "client_order_id": "ord_seed_risk_001",
        "severity": "MEDIUM",
        "event_type": "risk.rule_triggered",
        "reason": "Seed event: order notional reached 72% of configured threshold.",
        "status": "OPEN",
        "payload": {"symbol": "TSLA", "notional": 36000, "max_notional": 50000},
        "dedupe_key": "seed-risk-event-notional-warning",
        "offset_minutes": 5,
    },
    {
        "rule_type": "RESTRICTED_SYMBOLS",
        "client_order_id": "ord_seed_risk_002",
        "severity": "HIGH",
        "event_type": "risk.rule_triggered",
        "reason": "Seed event: restricted symbol GME was blocked before routing.",
        "status": "BLOCKED",
        "payload": {"symbol": "GME", "symbols": ["GME", "AMC", "DOGE"]},
        "dedupe_key": "seed-risk-event-restricted-symbol",
        "offset_minutes": 35,
    },
    {
        "rule_type": "TRADING_WINDOW",
        "client_order_id": "ord_seed_risk_003",
        "severity": "LOW",
        "event_type": "risk.rule_triggered",
        "reason": "Seed event: pre-market order was reviewed and closed by operations.",
        "status": "RESOLVED",
        "payload": {"symbol": "NVDA", "window": {"start_time": "09:30", "end_time": "16:00"}},
        "dedupe_key": "seed-risk-event-trading-window",
        "offset_minutes": 120,
    },
)


def seed_default_risk_data(
    session: Session,
    *,
    owner: UserModel,
    account: BrokerAccountModel,
    now: datetime | None = None,
) -> dict[str, int]:
    seeded_at = now or datetime.now(UTC)
    account_id = str(account.id)
    existing_rules = session.execute(
        select(RiskRuleModel).where(RiskRuleModel.created_by == owner.id)
    ).scalars().all()
    rule_by_key = {_rule_key(row): row for row in existing_rules}
    created_rules = 0

    for payload in DEFAULT_RISK_RULES:
        scope_accounts = [account_id] if payload["scope"] in {"ACCOUNT", "ACCOUNT_AND_SYMBOL"} else []
        scope_symbols = [str(symbol).upper() for symbol in payload["scope_symbols"]]
        key = _rule_seed_key(
            rule_type=str(payload["rule_type"]),
            scope_accounts=scope_accounts,
            scope_symbols=scope_symbols,
        )
        if key in rule_by_key:
            continue

        rule = RiskRuleModel(
            id=uuid.uuid4(),
            created_by=owner.id,
            name=str(payload["name"]),
            description=payload["description"],
            scope=str(payload["scope"]),
            scope_accounts=scope_accounts,
            scope_symbols=scope_symbols,
            rule_type=str(payload["rule_type"]),
            config=_validate_rule_config(str(payload["rule_type"]), dict(payload["config"])),
            enabled=bool(payload["enabled"]),
            version=1,
            created_at=seeded_at,
            updated_at=seeded_at,
        )
        session.add(rule)
        session.flush()
        session.add(
            RiskRuleVersionModel(
                id=uuid.uuid4(),
                risk_rule_id=rule.id,
                version=1,
                snapshot=_rule_snapshot(rule),
                change_reason=str(payload["change_reason"]),
                changed_by=owner.id,
                changed_at=seeded_at,
            )
        )
        rule_by_key[key] = rule
        created_rules += 1

    existing_event_keys = {
        dedupe_key
        for dedupe_key in session.execute(
            select(RiskEventModel.dedupe_key).where(
                RiskEventModel.broker_account_id == account.id,
                RiskEventModel.dedupe_key.is_not(None),
            )
        ).scalars()
        if dedupe_key
    }
    created_events = 0

    for payload in DEFAULT_RISK_EVENTS:
        dedupe_key = str(payload["dedupe_key"])
        if dedupe_key in existing_event_keys:
            continue

        rule = rule_by_key.get(
            _rule_seed_key(
                rule_type=str(payload["rule_type"]),
                scope_accounts=[account_id],
                scope_symbols=_default_scope_symbols(str(payload["rule_type"])),
            )
        )
        if rule is None:
            continue

        session.add(
            RiskEventModel(
                id=uuid.uuid4(),
                risk_rule_id=rule.id,
                broker_account_id=account.id,
                order_id=None,
                client_order_id=payload["client_order_id"],
                severity=str(payload["severity"]),
                event_type=str(payload["event_type"]),
                reason=str(payload["reason"]),
                status=str(payload["status"]),
                payload=dict(payload["payload"]),
                dedupe_key=dedupe_key,
                occurred_at=seeded_at - timedelta(minutes=int(payload["offset_minutes"])),
            )
        )
        existing_event_keys.add(dedupe_key)
        created_events += 1

    return {"rules_created": created_rules, "events_created": created_events}


def _rule_key(rule: RiskRuleModel) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return _rule_seed_key(
        rule_type=str(rule.rule_type),
        scope_accounts=[str(value) for value in (rule.scope_accounts or [])],
        scope_symbols=[str(value).upper() for value in (rule.scope_symbols or [])],
    )


def _rule_seed_key(
    *,
    rule_type: str,
    scope_accounts: list[str],
    scope_symbols: list[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        rule_type.upper(),
        tuple(sorted(str(value) for value in scope_accounts if str(value).strip())),
        tuple(sorted(str(value).upper() for value in scope_symbols if str(value).strip())),
    )


def _default_scope_symbols(rule_type: str) -> list[str]:
    for payload in DEFAULT_RISK_RULES:
        if str(payload["rule_type"]).upper() == rule_type.upper():
            return [str(symbol).upper() for symbol in payload["scope_symbols"]]
    return []


def _rule_snapshot(rule: RiskRuleModel) -> dict[str, Any]:
    return {
        "id": str(rule.id),
        "name": rule.name,
        "description": rule.description,
        "rule_type": str(rule.rule_type),
        "scope": {
            "account_ids": [str(value) for value in (rule.scope_accounts or [])],
            "symbols": [str(value).upper() for value in (rule.scope_symbols or [])],
        },
        "config": dict(rule.config or {}),
        "enabled": bool(rule.enabled),
        "version": int(rule.version),
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }
