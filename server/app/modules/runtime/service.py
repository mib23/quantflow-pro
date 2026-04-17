from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import status

from app.core.exceptions import ApiException
from app.core.realtime import realtime_hub
from app.modules.runtime.repository import RuntimeRepository
from app.modules.runtime.schemas import (
    RuntimeApprovalActionRequest,
    RuntimeEnvironment,
    RuntimeHeartbeatRequest,
    RuntimeInstanceCreateRequest,
    RuntimeInstanceDetail,
    RuntimeInstanceItem,
    RuntimeInstanceListResponse,
    RuntimeLogEntryItem,
    RuntimeLogListResponse,
)


@lru_cache
def get_runtime_repository() -> RuntimeRepository:
    return RuntimeRepository()


def get_runtime_service() -> "RuntimeService":
    return RuntimeService(get_runtime_repository())


class RuntimeService:
    def __init__(self, repository: RuntimeRepository):
        self._repository = repository

    def list_instances(self, *, user_id: str, page: int = 1, page_size: int = 20) -> RuntimeInstanceListResponse:
        include_admin = self._is_admin(user_id)
        items, total = self._repository.list_instances(user_id=user_id, include_admin=include_admin, page=page, page_size=page_size)
        refreshed = [self._refresh_health(item.id, requester_user_id=user_id, include_admin=include_admin) for item in items]
        compact = [RuntimeInstanceItem(**item.model_dump(exclude={"approval", "recent_logs", "recent_alerts", "recent_orders", "recent_risk_events"})) for item in refreshed]
        return RuntimeInstanceListResponse(items=compact, page=page, page_size=page_size, total=total)

    def create_instance(self, payload: RuntimeInstanceCreateRequest, *, requested_by: str) -> RuntimeInstanceDetail:
        user = self._require_user(requested_by)
        bundle = self._repository.get_strategy_version_bundle(payload.strategy_version_id)
        if bundle is None:
            raise ApiException("STRATEGY_VERSION_NOT_FOUND", "Strategy version not found.", status.HTTP_404_NOT_FOUND)
        version, strategy = bundle
        broker_account = self._repository.get_broker_account(payload.broker_account_id)
        if broker_account is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        is_admin = self._is_admin(requested_by, user_role=user.role)
        self._validate_environment_match(payload.environment, broker_account.environment)
        if payload.environment == "LIVE" and not is_admin:
            raise ApiException("RUNTIME_PERMISSION_DENIED", "Only admins can create live runtime instances.", status.HTTP_403_FORBIDDEN)

        parameters_snapshot = dict(payload.parameters_snapshot or version.parameter_template or {})
        approval_status = "PENDING" if payload.environment == "LIVE" else "NOT_REQUIRED"
        instance = self._repository.create_instance(
            strategy=strategy,
            version=version,
            broker_account=broker_account,
            submitted_by=requested_by,
            environment=payload.environment,
            approval_status=approval_status,
            parameters_snapshot=parameters_snapshot,
            deployment_notes=payload.deployment_notes,
        )
        self._append_runtime_log(instance.id, level="INFO", source="api", message="Runtime instance created.")
        if payload.environment == "LIVE":
            self._repository.create_approval(
                runtime_instance_id=instance.id,
                requested_by=requested_by,
                note=payload.deployment_notes,
            )
            self._append_runtime_log(instance.id, level="INFO", source="approval", message="Live deployment approval requested.")
        return self.get_instance_detail(instance.id, user_id=requested_by)

    def get_instance_detail(self, instance_id: str, *, user_id: str) -> RuntimeInstanceDetail:
        return self._refresh_health(
            instance_id,
            requester_user_id=user_id,
            include_admin=self._is_admin(user_id),
        )

    def start_instance(self, instance_id: str, *, user_id: str) -> RuntimeInstanceDetail:
        detail = self.get_instance_detail(instance_id, user_id=user_id)
        self._assert_instance_operator(detail, user_id=user_id)
        if detail.environment == "LIVE":
            self._assert_admin(user_id)
            self._assert_live_ready(detail)
        if detail.status == "RUNNING":
            return detail

        now = datetime.now(timezone.utc)
        self._repository.update_runtime(instance_id=instance_id, status="STARTING", error_summary=None)
        self._publish_status(instance_id, user_id=user_id)
        self._append_runtime_log(instance_id, level="INFO", source="worker", message="Runtime starting.")
        self._repository.update_runtime(
            instance_id=instance_id,
            status="RUNNING",
            started_at=now,
            stopped_at=None,
            last_heartbeat_at=now,
            error_summary=None,
        )
        self._append_runtime_log(instance_id, level="INFO", source="worker", message="Runtime is running.")
        self._publish_status(instance_id, user_id=user_id)
        return self.get_instance_detail(instance_id, user_id=user_id)

    def stop_instance(self, instance_id: str, *, user_id: str) -> RuntimeInstanceDetail:
        detail = self.get_instance_detail(instance_id, user_id=user_id)
        self._assert_instance_operator(detail, user_id=user_id)
        if detail.environment == "LIVE":
            self._assert_admin(user_id)
        if detail.status == "STOPPED":
            return detail

        now = datetime.now(timezone.utc)
        self._repository.update_runtime(instance_id=instance_id, status="STOPPING")
        self._append_runtime_log(instance_id, level="INFO", source="worker", message="Runtime stopping.")
        self._repository.update_runtime(instance_id=instance_id, status="STOPPED", stopped_at=now)
        self._append_runtime_log(instance_id, level="INFO", source="worker", message="Runtime stopped.")
        self._publish_status(instance_id, user_id=user_id)
        return self.get_instance_detail(instance_id, user_id=user_id)

    def restart_instance(self, instance_id: str, *, user_id: str) -> RuntimeInstanceDetail:
        detail = self.get_instance_detail(instance_id, user_id=user_id)
        self._assert_instance_operator(detail, user_id=user_id)
        if detail.environment == "LIVE":
            self._assert_admin(user_id)
            self._assert_live_ready(detail)

        self._append_runtime_log(instance_id, level="INFO", source="worker", message="Runtime restart requested.")
        self._repository.update_runtime(
            instance_id=instance_id,
            restart_count=detail.restart_count + 1,
        )
        if detail.status == "RUNNING":
            self.stop_instance(instance_id, user_id=user_id)
        return self.start_instance(instance_id, user_id=user_id)

    def approve_deployment(
        self,
        instance_id: str,
        payload: RuntimeApprovalActionRequest,
        *,
        user_id: str,
    ) -> RuntimeInstanceDetail:
        self._assert_admin(user_id)
        self._repository.set_approval_decision(
            runtime_instance_id=instance_id,
            reviewed_by=user_id,
            decision="APPROVED",
            note=payload.note,
        )
        self._append_runtime_log(instance_id, level="INFO", source="approval", message="Live deployment approved.")
        self._publish_status(instance_id, user_id=user_id)
        return self.get_instance_detail(instance_id, user_id=user_id)

    def reject_deployment(
        self,
        instance_id: str,
        payload: RuntimeApprovalActionRequest,
        *,
        user_id: str,
    ) -> RuntimeInstanceDetail:
        self._assert_admin(user_id)
        self._repository.set_approval_decision(
            runtime_instance_id=instance_id,
            reviewed_by=user_id,
            decision="REJECTED",
            note=payload.note,
        )
        self._append_runtime_log(instance_id, level="WARN", source="approval", message="Live deployment rejected.")
        self._publish_status(instance_id, user_id=user_id)
        return self.get_instance_detail(instance_id, user_id=user_id)

    def record_heartbeat(
        self,
        instance_id: str,
        payload: RuntimeHeartbeatRequest,
        *,
        user_id: str,
    ) -> RuntimeInstanceDetail:
        detail = self.get_instance_detail(instance_id, user_id=user_id)
        self._assert_instance_operator(detail, user_id=user_id)
        now = datetime.now(timezone.utc)
        next_status = "RUNNING" if detail.status == "DEGRADED" else detail.status
        self._repository.update_runtime(
            instance_id=instance_id,
            status=next_status,
            last_heartbeat_at=now,
            error_summary=None,
        )
        message = payload.summary or "Heartbeat received."
        self._append_runtime_log(instance_id, level="INFO", source="heartbeat", message=message)
        self._publish_status(instance_id, user_id=user_id)
        return self.get_instance_detail(instance_id, user_id=user_id)

    def list_logs(self, instance_id: str, *, user_id: str) -> RuntimeLogListResponse:
        self.get_instance_detail(instance_id, user_id=user_id)
        return self._repository.list_logs(instance_id)

    def sweep_stale_instances(self) -> int:
        updated = 0
        now = datetime.now(timezone.utc)
        for instance_id, last_heartbeat_at, heartbeat_timeout_seconds in self._repository.list_running_instance_health():
            if last_heartbeat_at is None:
                continue
            normalized_heartbeat_at = last_heartbeat_at
            if normalized_heartbeat_at.tzinfo is None or normalized_heartbeat_at.tzinfo.utcoffset(normalized_heartbeat_at) is None:
                normalized_heartbeat_at = normalized_heartbeat_at.replace(tzinfo=timezone.utc)
            deadline = normalized_heartbeat_at + timedelta(seconds=heartbeat_timeout_seconds)
            if deadline >= now:
                continue
            detail = self._refresh_health(instance_id, requester_user_id=None, include_admin=True)
            if detail.status == "DEGRADED":
                updated += 1
        return updated

    def _refresh_health(self, instance_id: str, *, requester_user_id: str | None, include_admin: bool) -> RuntimeInstanceDetail:
        detail = self._repository.get_instance_detail(
            instance_id,
            requester_user_id=requester_user_id,
            include_admin=include_admin,
        )
        if detail.status != "RUNNING" or detail.last_heartbeat_at is None:
            return detail
        last_heartbeat_at = detail.last_heartbeat_at
        if last_heartbeat_at.tzinfo is None or last_heartbeat_at.tzinfo.utcoffset(last_heartbeat_at) is None:
            last_heartbeat_at = last_heartbeat_at.replace(tzinfo=timezone.utc)
        deadline = last_heartbeat_at + timedelta(seconds=detail.heartbeat_timeout_seconds)
        if deadline >= datetime.now(timezone.utc):
            return detail
        degraded = self._repository.update_runtime(
            instance_id=instance_id,
            status="DEGRADED",
            error_summary="Heartbeat timeout exceeded.",
        )
        self._append_runtime_log(
            instance_id,
            level="WARN",
            source="monitor",
            message="Heartbeat overdue; runtime entered degraded state.",
        )
        self._repository.append_alert(
            runtime_instance_id=instance_id,
            severity="HIGH",
            alert_type="HEARTBEAT_TIMEOUT",
            message="Runtime heartbeat timed out.",
            recommendation="Inspect worker health and restart or take manual control.",
            payload={"last_heartbeat_at": detail.last_heartbeat_at.isoformat()},
        )
        self._publish_status(instance_id, detail_override=degraded)
        return self._repository.get_instance_detail(
            instance_id,
            requester_user_id=requester_user_id,
            include_admin=include_admin,
        )

    def _assert_live_ready(self, detail: RuntimeInstanceDetail) -> None:
        if detail.approval_status != "APPROVED":
            raise ApiException(
                "LIVE_APPROVAL_REQUIRED",
                "Live runtime instance must be approved before it can start.",
                status.HTTP_409_CONFLICT,
            )
        account = self._repository.get_broker_account(detail.broker_account_id)
        if account is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        if str(account.status).upper() != "ACTIVE":
            raise ApiException("BROKER_ACCOUNT_INACTIVE", "Broker account is not active.", status.HTTP_409_CONFLICT)
        if not self._repository.has_backtest_result(detail.strategy_version_id):
            raise ApiException(
                "LIVE_BACKTEST_REQUIRED",
                "Live runtime requires at least one completed backtest result for this strategy version.",
                status.HTTP_409_CONFLICT,
            )
        if not self._repository.has_enabled_risk_rules(owner_user_id=str(account.user_id), broker_account_id=detail.broker_account_id):
            raise ApiException(
                "LIVE_RISK_RULES_REQUIRED",
                "Live runtime requires at least one enabled risk rule for the target account.",
                status.HTTP_409_CONFLICT,
            )

    def _assert_instance_operator(self, detail: RuntimeInstanceDetail, *, user_id: str) -> None:
        if self._is_admin(user_id):
            return
        if detail.submitted_by != user_id:
            raise ApiException("RUNTIME_PERMISSION_DENIED", "You do not have access to this runtime instance.", status.HTTP_403_FORBIDDEN)

    def _assert_admin(self, user_id: str) -> None:
        if not self._is_admin(user_id):
            raise ApiException("RUNTIME_PERMISSION_DENIED", "Admin privileges are required.", status.HTTP_403_FORBIDDEN)

    def _require_user(self, user_id: str):
        user = self._repository.get_user(user_id)
        if user is None:
            raise ApiException("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        return user

    def _is_admin(self, user_id: str, user_role: str | None = None) -> bool:
        role = user_role
        if role is None:
            user = self._repository.get_user(user_id)
            role = user.role if user is not None else None
        return str(role).upper() == "ADMIN"

    @staticmethod
    def _validate_environment_match(expected: RuntimeEnvironment, account_environment: str) -> None:
        if expected != str(account_environment).upper():
            raise ApiException(
                "BROKER_ACCOUNT_ENVIRONMENT_MISMATCH",
                "Runtime environment must match the selected broker account environment.",
                status.HTTP_409_CONFLICT,
            )

    def _append_runtime_log(self, instance_id: str, *, level: str, source: str, message: str) -> RuntimeLogEntryItem:
        log = self._repository.append_log(
            runtime_instance_id=instance_id,
            level=level,
            source=source,
            message=message,
        )
        self._publish_log(log)
        return log

    def _publish_status(self, instance_id: str, *, user_id: str | None = None, detail_override=None) -> None:
        detail = detail_override or self._repository.get_instance_item(instance_id, include_admin=True)
        self._publish_event(
            f"runtime.status.{instance_id}",
            "runtime.status_changed",
            {
                "instance_id": detail.id,
                "status": detail.status,
                "approval_status": detail.approval_status,
                "environment": detail.environment,
                "last_heartbeat_at": detail.last_heartbeat_at.isoformat() if detail.last_heartbeat_at else None,
                "error_summary": detail.error_summary,
            },
        )

    def _publish_log(self, log: RuntimeLogEntryItem) -> None:
        self._publish_event(
            f"runtime.logs.{log.runtime_instance_id}",
            "runtime.log_created",
            log.model_dump(mode="json"),
        )

    @staticmethod
    def _publish_event(channel: str, event: str, payload: dict) -> None:
        try:
            import asyncio
            import inspect

            loop = asyncio.get_running_loop()
            publish_result = realtime_hub.publish(channel, event, payload)
            if inspect.isawaitable(publish_result):
                loop.create_task(publish_result)
        except RuntimeError:
            import asyncio
            import inspect

            publish_result = realtime_hub.publish(channel, event, payload)
            if inspect.isawaitable(publish_result):
                asyncio.run(publish_result)
