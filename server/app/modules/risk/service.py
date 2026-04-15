from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastapi import status

from app.core.database import create_sync_engine
from app.core.exceptions import ApiException
from app.core.settings import get_settings
from app.modules.risk.repository import RiskRepository, get_risk_session_factory
from app.modules.risk.schemas import (
    PreTradeCheckRequest,
    RiskCheckResult,
    RiskEventListResponse,
    RiskRule,
    RiskRuleCreateRequest,
    RiskRuleListResponse,
    RiskRuleUpdateRequest,
    RiskSummaryResponse,
)


@dataclass(slots=True)
class RiskService:
    repository: RiskRepository | None = None

    @property
    def resolved_repository(self) -> RiskRepository:
        return self.repository or RiskRepository(get_risk_session_factory())

    def get_summary(self, user_id: str, broker_account_id: str | None = None) -> RiskSummaryResponse:
        return self.resolved_repository.get_summary(user_id=user_id, broker_account_id=broker_account_id)

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
        return self.resolved_repository.list_rules(
            user_id=user_id,
            broker_account_id=broker_account_id,
            enabled=enabled,
            rule_type=rule_type,
            page=page,
            page_size=page_size,
        )

    def create_rule(self, payload: RiskRuleCreateRequest, *, created_by: str, trace_id: str | None = None) -> RiskRule:
        return self.resolved_repository.create_rule(payload, created_by=created_by, trace_id=trace_id)

    def update_rule(
        self,
        rule_id: str,
        payload: RiskRuleUpdateRequest,
        *,
        changed_by: str,
        trace_id: str | None = None,
    ) -> RiskRule:
        return self.resolved_repository.update_rule(rule_id, payload, changed_by=changed_by, trace_id=trace_id)

    def activate_rule(self, rule_id: str, *, changed_by: str, trace_id: str | None = None) -> RiskRule:
        return self.resolved_repository.set_rule_enabled(rule_id, enabled=True, changed_by=changed_by, trace_id=trace_id)

    def deactivate_rule(self, rule_id: str, *, changed_by: str, trace_id: str | None = None) -> RiskRule:
        return self.resolved_repository.set_rule_enabled(rule_id, enabled=False, changed_by=changed_by, trace_id=trace_id)

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
        return self.resolved_repository.list_events(
            user_id=user_id,
            broker_account_id=broker_account_id,
            rule_id=rule_id,
            severity=severity,
            status_value=status_value,
            page=page,
            page_size=page_size,
        )

    def check_pre_trade(
        self,
        request: PreTradeCheckRequest,
        *,
        user_id: str | None = None,
        broker_account: dict[str, object] | None = None,
        persist: bool = True,
        trace_id: str | None = None,
    ) -> RiskCheckResult:
        return self.resolved_repository.evaluate_pre_trade(
            request,
            user_id=user_id,
            broker_account=broker_account,
            persist=persist,
            trace_id=trace_id,
        )

    @staticmethod
    def build_rejection_exception(result: RiskCheckResult) -> ApiException:
        return ApiException(
            "ORDER_RISK_REJECTED",
            result.reason or "Order rejected by risk rules.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={
                "reason": result.reason,
                "events": [event.model_dump(mode="json") for event in result.events],
                "rule_ids": result.rule_ids,
                "checked_at": result.checked_at.isoformat(),
            },
        )


@lru_cache
def get_risk_service() -> RiskService:
    return RiskService()
