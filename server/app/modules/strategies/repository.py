from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiException
from app.core.ids import coerce_uuid
from app.core.models import AuditLogModel, StrategyModel, StrategyVersionModel
from app.modules.strategies.schemas import StrategyCreateRequest, StrategyDetail, StrategySummary, StrategyVersionCreateRequest, StrategyVersionItem


class StrategyRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def list_strategies(self, *, user_id: str) -> tuple[list[StrategySummary], int]:
        with self._session_factory() as session:
            rows = session.execute(
                select(StrategyModel)
                .where(StrategyModel.owner_user_id == coerce_uuid(user_id))
                .order_by(StrategyModel.updated_at.desc(), StrategyModel.id.desc())
            ).scalars().all()
            versions = self._versions_by_strategy(session, [str(row.id) for row in rows])
        items = [self._serialize_summary(row, versions.get(str(row.id), [])) for row in rows]
        return items, len(items)

    def get_strategy(self, strategy_id: str, *, user_id: str) -> StrategyDetail | None:
        with self._session_factory() as session:
            row = session.execute(
                select(StrategyModel).where(
                    StrategyModel.id == coerce_uuid(strategy_id),
                    StrategyModel.owner_user_id == coerce_uuid(user_id),
                )
            ).scalars().first()
            versions = self._versions_by_strategy(session, [strategy_id]).get(strategy_id, [])
        if row is None:
            return None
        summary = self._serialize_summary(row, versions)
        return StrategyDetail(owner_user_id=str(row.owner_user_id), created_at=row.created_at, versions=versions, **summary.model_dump())

    def get_version(self, strategy_id: str, version_id: str, *, user_id: str) -> StrategyVersionItem | None:
        with self._session_factory() as session:
            row = session.execute(
                select(StrategyVersionModel)
                .join(StrategyModel, StrategyModel.id == StrategyVersionModel.strategy_id)
                .where(
                    StrategyVersionModel.id == coerce_uuid(version_id),
                    StrategyVersionModel.strategy_id == coerce_uuid(strategy_id),
                    StrategyModel.owner_user_id == coerce_uuid(user_id),
                )
            ).scalars().first()
        return self._serialize_version(row) if row is not None else None

    def create_strategy(self, payload: StrategyCreateRequest, *, user_id: str, trace_id: str | None = None) -> StrategyDetail:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                row = StrategyModel(
                    id=uuid4(),
                    owner_user_id=coerce_uuid(user_id),
                    name=payload.name.strip(),
                    description=payload.description,
                    status="ACTIVE",
                    default_parameters=payload.default_parameters,
                    latest_version_id=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                self._append_audit_log(
                    session,
                    user_id=user_id,
                    resource_type="STRATEGY",
                    resource_id=str(row.id),
                    action="STRATEGY_CREATED",
                    after_state={"name": row.name, "description": row.description, "status": row.status},
                    trace_id=trace_id,
                )
        detail = self.get_strategy(str(row.id), user_id=user_id)
        if detail is None:
            raise ValueError("Strategy could not be created.")
        return detail

    def create_version(
        self,
        strategy_id: str,
        payload: StrategyVersionCreateRequest,
        *,
        user_id: str,
        trace_id: str | None = None,
    ) -> StrategyVersionItem:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                strategy = session.execute(
                    select(StrategyModel).where(
                        StrategyModel.id == coerce_uuid(strategy_id),
                        StrategyModel.owner_user_id == coerce_uuid(user_id),
                    )
                ).scalars().first()
                if strategy is None:
                    raise ApiException("STRATEGY_NOT_FOUND", "Strategy not found.", status.HTTP_404_NOT_FOUND)

                current_number = session.execute(
                    select(func.max(StrategyVersionModel.version_number)).where(StrategyVersionModel.strategy_id == strategy.id)
                ).scalar_one()
                next_number = int(current_number or 0) + 1
                version = StrategyVersionModel(
                    id=uuid4(),
                    strategy_id=strategy.id,
                    version_number=next_number,
                    code_snapshot=payload.code,
                    parameters_snapshot=payload.parameters or strategy.default_parameters,
                    version_note=payload.version_note,
                    created_by=coerce_uuid(user_id),
                    created_at=now,
                )
                session.add(version)
                strategy.latest_version_id = str(version.id)
                strategy.updated_at = now
                self._append_audit_log(
                    session,
                    user_id=user_id,
                    resource_type="STRATEGY_VERSION",
                    resource_id=str(version.id),
                    action="STRATEGY_VERSION_CREATED",
                    after_state={"strategy_id": str(strategy.id), "version_number": next_number},
                    trace_id=trace_id,
                )
        created = self.get_version(strategy_id, str(version.id), user_id=user_id)
        if created is None:
            raise ValueError("Strategy version could not be created.")
        return created

    def clone_version(self, strategy_id: str, version_id: str, *, user_id: str, trace_id: str | None = None) -> StrategyVersionItem:
        source = self.get_version(strategy_id, version_id, user_id=user_id)
        if source is None:
            raise ApiException("STRATEGY_VERSION_NOT_FOUND", "Strategy version not found.", status.HTTP_404_NOT_FOUND)
        return self.create_version(
            strategy_id,
            StrategyVersionCreateRequest(
                code=source.code,
                parameters=source.parameters,
                version_note=f"Cloned from {source.version_tag}",
            ),
            user_id=user_id,
            trace_id=trace_id,
        )

    def _versions_by_strategy(self, session: Session, strategy_ids: list[str]) -> dict[str, list[StrategyVersionItem]]:
        if not strategy_ids:
            return {}
        rows = session.execute(
            select(StrategyVersionModel)
            .where(StrategyVersionModel.strategy_id.in_([coerce_uuid(strategy_id) for strategy_id in strategy_ids]))
            .order_by(StrategyVersionModel.version_number.desc(), StrategyVersionModel.created_at.desc())
        ).scalars().all()
        grouped: dict[str, list[StrategyVersionItem]] = {strategy_id: [] for strategy_id in strategy_ids}
        for row in rows:
            grouped.setdefault(str(row.strategy_id), []).append(self._serialize_version(row))
        return grouped

    @staticmethod
    def _serialize_version(row: StrategyVersionModel) -> StrategyVersionItem:
        return StrategyVersionItem(
            id=str(row.id),
            strategy_id=str(row.strategy_id),
            version_number=int(row.version_number),
            version_tag=f"v{int(row.version_number)}",
            code=row.code_snapshot,
            parameters=dict(row.parameters_snapshot or {}),
            version_note=row.version_note,
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    @staticmethod
    def _serialize_summary(row: StrategyModel, versions: list[StrategyVersionItem]) -> StrategySummary:
        latest = versions[0] if versions else None
        return StrategySummary(
            id=str(row.id),
            name=row.name,
            description=row.description,
            status=row.status,
            default_parameters=dict(row.default_parameters or {}),
            latest_version_id=str(row.latest_version_id) if row.latest_version_id else None,
            latest_version_tag=latest.version_tag if latest is not None else None,
            updated_at=row.updated_at,
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
                user_id=coerce_uuid(user_id),
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                before_state=before_state,
                after_state=after_state,
                trace_id=trace_id,
                created_at=datetime.now(UTC),
            )
        )
