from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_sync_engine
from app.core.exceptions import ApiException
from app.core.models import (
    AuditLogModel,
    BacktestJobModel,
    BacktestResultModel,
    BrokerAccountModel,
    DeploymentApprovalModel,
    OrderModel,
    RiskEventModel,
    RiskRuleModel,
    RuntimeAlertModel,
    RuntimeInstanceModel,
    RuntimeLogEntryModel,
    StrategyModel,
    StrategyVersionModel,
    UserModel,
)
from app.core.settings import get_settings
from app.modules.runtime.schemas import (
    DeploymentApprovalItem,
    RuntimeAlertItem,
    RuntimeInstanceDetail,
    RuntimeInstanceItem,
    RuntimeLogEntryItem,
    RuntimeLogListResponse,
    RuntimeOrderItem,
    RuntimeRiskEventItem,
)

_UNSET = object()


@lru_cache
def get_runtime_session_factory() -> Callable[[], Session]:
    engine = create_sync_engine(get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class RuntimeRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None):
        self._session_factory = session_factory or get_runtime_session_factory()

    def get_user(self, user_id: str) -> UserModel | None:
        with self._session_factory() as session:
            return session.get(UserModel, user_id)

    def get_strategy_version_bundle(self, strategy_version_id: str) -> tuple[StrategyVersionModel, StrategyModel] | None:
        with self._session_factory() as session:
            version = session.get(StrategyVersionModel, strategy_version_id)
            if version is None:
                return None
            strategy = session.get(StrategyModel, version.strategy_id)
            if strategy is None:
                return None
            return version, strategy

    def get_broker_account(self, broker_account_id: str) -> BrokerAccountModel | None:
        with self._session_factory() as session:
            return session.get(BrokerAccountModel, broker_account_id)

    def has_backtest_result(self, strategy_version_id: str) -> bool:
        with self._session_factory() as session:
            statement = (
                select(BacktestResultModel.id)
                .join(BacktestJobModel, BacktestJobModel.id == BacktestResultModel.backtest_job_id)
                .where(BacktestJobModel.strategy_version_id == strategy_version_id)
                .limit(1)
            )
            return session.execute(statement).scalar_one_or_none() is not None

    def has_enabled_risk_rules(self, *, owner_user_id: str, broker_account_id: str) -> bool:
        with self._session_factory() as session:
            rows = session.execute(
                select(RiskRuleModel).where(
                    RiskRuleModel.created_by == owner_user_id,
                    RiskRuleModel.enabled.is_(True),
                )
            ).scalars().all()
        for row in rows:
            account_scope = [str(value) for value in (row.scope_accounts or []) if str(value).strip()]
            if not account_scope or broker_account_id in account_scope:
                return True
        return False

    def create_instance(
        self,
        *,
        strategy: StrategyModel,
        version: StrategyVersionModel,
        broker_account: BrokerAccountModel,
        submitted_by: str,
        environment: str,
        approval_status: str,
        parameters_snapshot: dict,
        deployment_notes: str | None,
    ) -> RuntimeInstanceItem:
        now = datetime.now(timezone.utc)
        instance = RuntimeInstanceModel(
            id=str(uuid4()),
            strategy_id=strategy.id,
            strategy_version_id=version.id,
            broker_account_id=broker_account.id,
            submitted_by=submitted_by,
            environment=environment,
            status="CREATED",
            approval_status=approval_status,
            parameters_snapshot=parameters_snapshot,
            deployment_notes=deployment_notes,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        with self._session_factory() as session:
            with session.begin():
                session.add(instance)
                self._append_audit_log(
                    session,
                    user_id=submitted_by,
                    resource_type="RUNTIME_INSTANCE",
                    resource_id=instance.id,
                    action="RUNTIME_INSTANCE_CREATED",
                    after_state=self._runtime_snapshot(instance),
                )
            session.refresh(instance)
        return self.get_instance_item(instance.id, include_admin=True)

    def create_approval(self, *, runtime_instance_id: str, requested_by: str, note: str | None) -> DeploymentApprovalItem:
        now = datetime.now(timezone.utc)
        approval = DeploymentApprovalModel(
            id=str(uuid4()),
            runtime_instance_id=runtime_instance_id,
            requested_by=requested_by,
            reviewed_by=None,
            decision="PENDING",
            note=note,
            requested_at=now,
            decided_at=None,
            updated_at=now,
        )
        with self._session_factory() as session:
            with session.begin():
                session.add(approval)
                self._append_audit_log(
                    session,
                    user_id=requested_by,
                    resource_type="DEPLOYMENT_APPROVAL",
                    resource_id=approval.id,
                    action="DEPLOYMENT_APPROVAL_REQUESTED",
                    after_state=self._approval_snapshot(approval),
                )
            session.refresh(approval)
        return self._serialize_approval(approval)

    def set_approval_decision(
        self,
        *,
        runtime_instance_id: str,
        reviewed_by: str,
        decision: str,
        note: str | None,
    ) -> DeploymentApprovalItem:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            with session.begin():
                approval = session.execute(
                    select(DeploymentApprovalModel).where(DeploymentApprovalModel.runtime_instance_id == runtime_instance_id)
                ).scalar_one_or_none()
                if approval is None:
                    raise ApiException("DEPLOYMENT_APPROVAL_NOT_FOUND", "Deployment approval request not found.", 404)
                before = self._approval_snapshot(approval)
                approval.reviewed_by = reviewed_by
                approval.decision = decision
                approval.note = note
                approval.decided_at = now
                approval.updated_at = now
                runtime = session.get(RuntimeInstanceModel, runtime_instance_id)
                if runtime is None:
                    raise ApiException("RUNTIME_INSTANCE_NOT_FOUND", "Runtime instance not found.", 404)
                runtime.approval_status = "APPROVED" if decision == "APPROVED" else "REJECTED"
                runtime.updated_at = now
                self._append_audit_log(
                    session,
                    user_id=reviewed_by,
                    resource_type="DEPLOYMENT_APPROVAL",
                    resource_id=approval.id,
                    action=f"DEPLOYMENT_{decision}",
                    before_state=before,
                    after_state=self._approval_snapshot(approval),
                )
            session.refresh(approval)
        return self._serialize_approval(approval)

    def get_instance_item(
        self,
        instance_id: str,
        *,
        requester_user_id: str | None = None,
        include_admin: bool = False,
    ) -> RuntimeInstanceItem:
        detail = self.get_instance_detail(instance_id, requester_user_id=requester_user_id, include_admin=include_admin)
        return RuntimeInstanceItem(**detail.model_dump(exclude={"approval", "recent_logs", "recent_alerts", "recent_orders", "recent_risk_events"}))

    def list_instances(self, *, user_id: str, include_admin: bool, page: int, page_size: int) -> tuple[list[RuntimeInstanceItem], int]:
        with self._session_factory() as session:
            query = (
                select(RuntimeInstanceModel)
                .join(StrategyModel, StrategyModel.id == RuntimeInstanceModel.strategy_id)
                .join(BrokerAccountModel, BrokerAccountModel.id == RuntimeInstanceModel.broker_account_id)
                .order_by(RuntimeInstanceModel.created_at.desc(), RuntimeInstanceModel.id.desc())
            )
            if not include_admin:
                query = query.where(
                    (BrokerAccountModel.user_id == user_id) | (RuntimeInstanceModel.submitted_by == user_id)
                )
            total = session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            instances = session.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return [
            self.get_instance_item(
                instance.id,
                requester_user_id=user_id,
                include_admin=include_admin,
            )
            for instance in instances
        ], int(total)

    def get_instance_detail(
        self,
        instance_id: str,
        *,
        requester_user_id: str | None,
        include_admin: bool,
    ) -> RuntimeInstanceDetail:
        with self._session_factory() as session:
            query = (
                select(RuntimeInstanceModel, StrategyModel, StrategyVersionModel, BrokerAccountModel)
                .join(StrategyModel, StrategyModel.id == RuntimeInstanceModel.strategy_id)
                .join(StrategyVersionModel, StrategyVersionModel.id == RuntimeInstanceModel.strategy_version_id)
                .join(BrokerAccountModel, BrokerAccountModel.id == RuntimeInstanceModel.broker_account_id)
                .where(RuntimeInstanceModel.id == instance_id)
            )
            row = session.execute(query).first()
            if row is None:
                raise ApiException("RUNTIME_INSTANCE_NOT_FOUND", "Runtime instance not found.", 404)
            runtime, strategy, version, account = row
            if not include_admin and (
                requester_user_id is None
                or (str(account.user_id) != str(requester_user_id) and str(runtime.submitted_by) != str(requester_user_id))
            ):
                raise ApiException("RUNTIME_INSTANCE_NOT_FOUND", "Runtime instance not found.", 404)
            approval = session.execute(
                select(DeploymentApprovalModel).where(DeploymentApprovalModel.runtime_instance_id == runtime.id)
            ).scalar_one_or_none()
            logs = session.execute(
                select(RuntimeLogEntryModel)
                .where(RuntimeLogEntryModel.runtime_instance_id == runtime.id)
                .order_by(RuntimeLogEntryModel.created_at.desc(), RuntimeLogEntryModel.id.desc())
                .limit(20)
            ).scalars().all()
            alerts = session.execute(
                select(RuntimeAlertModel)
                .where(RuntimeAlertModel.runtime_instance_id == runtime.id)
                .order_by(RuntimeAlertModel.created_at.desc(), RuntimeAlertModel.id.desc())
                .limit(10)
            ).scalars().all()
            orders = session.execute(
                select(OrderModel)
                .where(OrderModel.runtime_instance_id == runtime.id)
                .order_by(OrderModel.submitted_at.desc(), OrderModel.id.desc())
                .limit(10)
            ).scalars().all()
            risk_rows = session.execute(
                select(RiskEventModel, RiskRuleModel.name, RiskRuleModel.rule_type)
                .join(RiskRuleModel, RiskRuleModel.id == RiskEventModel.risk_rule_id)
                .where(RiskEventModel.runtime_instance_id == runtime.id)
                .order_by(RiskEventModel.occurred_at.desc(), RiskEventModel.id.desc())
                .limit(10)
            ).all()
        return RuntimeInstanceDetail(
            **self._serialize_instance(runtime, strategy, version, account).model_dump(),
            approval=self._serialize_approval(approval) if approval is not None else None,
            recent_logs=[self._serialize_log(log) for log in logs],
            recent_alerts=[self._serialize_alert(alert) for alert in alerts],
            recent_orders=[self._serialize_order(order) for order in orders],
            recent_risk_events=[self._serialize_risk_event(event, rule_name, rule_type) for event, rule_name, rule_type in risk_rows],
        )

    def list_logs(self, instance_id: str) -> RuntimeLogListResponse:
        with self._session_factory() as session:
            logs = session.execute(
                select(RuntimeLogEntryModel)
                .where(RuntimeLogEntryModel.runtime_instance_id == instance_id)
                .order_by(RuntimeLogEntryModel.created_at.desc(), RuntimeLogEntryModel.id.desc())
            ).scalars().all()
        items = [self._serialize_log(log) for log in logs]
        return RuntimeLogListResponse(items=items, total=len(items))

    def list_running_instance_health(self) -> list[tuple[str, datetime | None, int]]:
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    RuntimeInstanceModel.id,
                    RuntimeInstanceModel.last_heartbeat_at,
                    RuntimeInstanceModel.heartbeat_timeout_seconds,
                ).where(RuntimeInstanceModel.status == "RUNNING")
            ).all()
        return [
            (
                str(instance_id),
                last_heartbeat_at,
                int(heartbeat_timeout_seconds or 0),
            )
            for instance_id, last_heartbeat_at, heartbeat_timeout_seconds in rows
        ]

    def update_runtime(
        self,
        *,
        instance_id: str,
        status: str | None = None,
        approval_status: str | None = None,
        started_at: datetime | None | object = _UNSET,
        stopped_at: datetime | None | object = _UNSET,
        last_heartbeat_at: datetime | None | object = _UNSET,
        restart_count: int | None = None,
        broker_failure_count: int | None = None,
        error_summary: str | None | object = _UNSET,
    ) -> RuntimeInstanceItem:
        with self._session_factory() as session:
            with session.begin():
                runtime = session.get(RuntimeInstanceModel, instance_id)
                if runtime is None:
                    raise ApiException("RUNTIME_INSTANCE_NOT_FOUND", "Runtime instance not found.", 404)
                if status is not None:
                    runtime.status = status
                if approval_status is not None:
                    runtime.approval_status = approval_status
                if started_at is not _UNSET:
                    runtime.started_at = started_at
                if stopped_at is not _UNSET:
                    runtime.stopped_at = stopped_at
                if last_heartbeat_at is not _UNSET:
                    runtime.last_heartbeat_at = last_heartbeat_at
                if restart_count is not None:
                    runtime.restart_count = restart_count
                if broker_failure_count is not None:
                    runtime.broker_failure_count = broker_failure_count
                if error_summary is not _UNSET:
                    runtime.error_summary = error_summary
                runtime.updated_at = datetime.now(timezone.utc)
            session.refresh(runtime)
        return self.get_instance_item(runtime.id, include_admin=True)

    def record_heartbeat(self, *, instance_id: str, when: datetime) -> RuntimeInstanceItem:
        return self.update_runtime(instance_id=instance_id, last_heartbeat_at=when, error_summary=None)

    def append_log(
        self,
        *,
        runtime_instance_id: str,
        level: str,
        source: str,
        message: str,
        context: dict | None = None,
    ) -> RuntimeLogEntryItem:
        log = RuntimeLogEntryModel(
            id=str(uuid4()),
            runtime_instance_id=runtime_instance_id,
            level=level,
            source=source,
            message=message,
            context=context or {},
            created_at=datetime.now(timezone.utc),
        )
        with self._session_factory() as session:
            with session.begin():
                session.add(log)
            session.refresh(log)
        return self._serialize_log(log)

    def append_alert(
        self,
        *,
        runtime_instance_id: str,
        severity: str,
        alert_type: str,
        message: str,
        recommendation: str | None = None,
        payload: dict | None = None,
    ) -> RuntimeAlertItem:
        alert = RuntimeAlertModel(
            id=str(uuid4()),
            runtime_instance_id=runtime_instance_id,
            severity=severity,
            alert_type=alert_type,
            status="OPEN",
            message=message,
            recommendation=recommendation,
            payload=payload or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with self._session_factory() as session:
            with session.begin():
                session.add(alert)
            session.refresh(alert)
        return self._serialize_alert(alert)

    def get_runtime_model(self, instance_id: str) -> RuntimeInstanceModel | None:
        with self._session_factory() as session:
            return session.get(RuntimeInstanceModel, instance_id)

    @staticmethod
    def _serialize_instance(
        runtime: RuntimeInstanceModel,
        strategy: StrategyModel,
        version: StrategyVersionModel,
        account: BrokerAccountModel,
    ) -> RuntimeInstanceItem:
        return RuntimeInstanceItem(
            id=str(runtime.id),
            strategy_id=str(runtime.strategy_id),
            strategy_name=str(strategy.name),
            strategy_version_id=str(runtime.strategy_version_id),
            strategy_version_number=int(version.version_number),
            broker_account_id=str(runtime.broker_account_id),
            broker_account_no=str(account.broker_account_no),
            environment=str(runtime.environment),
            status=str(runtime.status),
            approval_status=str(runtime.approval_status),
            parameters_snapshot=dict(runtime.parameters_snapshot or {}),
            deployment_notes=runtime.deployment_notes,
            submitted_by=str(runtime.submitted_by),
            submitted_at=runtime.submitted_at,
            started_at=runtime.started_at,
            stopped_at=runtime.stopped_at,
            last_heartbeat_at=runtime.last_heartbeat_at,
            heartbeat_timeout_seconds=int(runtime.heartbeat_timeout_seconds),
            restart_count=int(runtime.restart_count or 0),
            broker_failure_count=int(runtime.broker_failure_count or 0),
            error_summary=runtime.error_summary,
            created_at=runtime.created_at,
            updated_at=runtime.updated_at,
        )

    @staticmethod
    def _serialize_approval(approval: DeploymentApprovalModel) -> DeploymentApprovalItem:
        return DeploymentApprovalItem(
            id=str(approval.id),
            runtime_instance_id=str(approval.runtime_instance_id),
            requested_by=str(approval.requested_by),
            reviewed_by=str(approval.reviewed_by) if approval.reviewed_by is not None else None,
            decision=str(approval.decision),
            note=approval.note,
            requested_at=approval.requested_at,
            decided_at=approval.decided_at,
            updated_at=approval.updated_at,
        )

    @staticmethod
    def _serialize_log(log: RuntimeLogEntryModel) -> RuntimeLogEntryItem:
        return RuntimeLogEntryItem(
            id=str(log.id),
            runtime_instance_id=str(log.runtime_instance_id),
            level=str(log.level),
            source=str(log.source),
            message=log.message,
            context=dict(log.context or {}),
            created_at=log.created_at,
        )

    @staticmethod
    def _serialize_alert(alert: RuntimeAlertModel) -> RuntimeAlertItem:
        return RuntimeAlertItem(
            id=str(alert.id),
            runtime_instance_id=str(alert.runtime_instance_id),
            severity=str(alert.severity),
            alert_type=str(alert.alert_type),
            status=str(alert.status),
            message=alert.message,
            recommendation=alert.recommendation,
            payload=dict(alert.payload or {}),
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )

    @staticmethod
    def _serialize_order(order: OrderModel) -> RuntimeOrderItem:
        return RuntimeOrderItem(
            id=str(order.id),
            runtime_instance_id=str(order.runtime_instance_id) if order.runtime_instance_id is not None else None,
            broker_account_id=str(order.broker_account_id),
            client_order_id=str(order.client_order_id),
            symbol=str(order.symbol),
            side=str(order.side),
            order_type=str(order.order_type),
            quantity=float(order.quantity),
            limit_price=float(order.limit_price) if order.limit_price is not None else None,
            status=str(order.status),
            submitted_at=order.submitted_at,
            updated_at=order.updated_at,
        )

    @staticmethod
    def _serialize_risk_event(event: RiskEventModel, rule_name: str, rule_type: str) -> RuntimeRiskEventItem:
        return RuntimeRiskEventItem(
            id=str(event.id),
            runtime_instance_id=str(event.runtime_instance_id) if event.runtime_instance_id is not None else None,
            rule_id=str(event.risk_rule_id),
            rule_name=str(rule_name),
            rule_type=str(rule_type),
            account_id=str(event.broker_account_id),
            client_order_id=event.client_order_id,
            severity=str(event.severity),
            status=str(event.status),
            reason=event.reason,
            occurred_at=event.occurred_at,
        )

    @staticmethod
    def _runtime_snapshot(runtime: RuntimeInstanceModel) -> dict[str, object]:
        return {
            "id": str(runtime.id),
            "strategy_id": str(runtime.strategy_id),
            "strategy_version_id": str(runtime.strategy_version_id),
            "broker_account_id": str(runtime.broker_account_id),
            "environment": runtime.environment,
            "status": runtime.status,
            "approval_status": runtime.approval_status,
            "submitted_at": runtime.submitted_at.isoformat() if runtime.submitted_at else None,
        }

    @staticmethod
    def _approval_snapshot(approval: DeploymentApprovalModel) -> dict[str, object]:
        return {
            "id": str(approval.id),
            "runtime_instance_id": str(approval.runtime_instance_id),
            "requested_by": str(approval.requested_by),
            "reviewed_by": str(approval.reviewed_by) if approval.reviewed_by is not None else None,
            "decision": approval.decision,
            "note": approval.note,
            "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        }

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
    ) -> None:
        session.add(
            AuditLogModel(
                id=str(uuid4()),
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                before_state=before_state,
                after_state=after_state,
                created_at=datetime.now(timezone.utc),
            )
        )
