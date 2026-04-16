from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_sync_engine
from app.core.ids import coerce_uuid
from app.core.models import AccountBalanceModel, BrokerAccountModel, OrderModel, PositionModel, RiskEventModel, RiskRuleModel
from app.core.settings import get_settings


@lru_cache
def get_dashboard_session_factory() -> Callable[[], Session]:
    engine = create_sync_engine(get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class DashboardRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def resolve_account(self, user_id: str, broker_account_id: str | None = None) -> dict[str, object] | None:
        with self._session_factory() as session:
            stmt = select(BrokerAccountModel)
            if broker_account_id is not None:
                stmt = stmt.where(BrokerAccountModel.id == coerce_uuid(broker_account_id), BrokerAccountModel.user_id == coerce_uuid(user_id))
            else:
                stmt = stmt.where(BrokerAccountModel.user_id == coerce_uuid(user_id)).order_by(BrokerAccountModel.created_at.desc(), BrokerAccountModel.id.asc())
            account = session.execute(stmt).scalars().first()
            if account is None:
                return None

            balance = session.execute(
                select(AccountBalanceModel)
                .where(AccountBalanceModel.broker_account_id == account.id)
                .order_by(AccountBalanceModel.snapshot_at.desc(), AccountBalanceModel.id.desc())
            ).scalars().first()
        return {
            "account": account,
            "balance": balance,
        }

    def list_positions(self, broker_account_id: str) -> list[dict[str, object]]:
        with self._session_factory() as session:
            ranked = (
                select(
                    PositionModel.id.label("id"),
                    PositionModel.broker_account_id.label("broker_account_id"),
                    PositionModel.symbol.label("symbol"),
                    PositionModel.quantity.label("quantity"),
                    PositionModel.avg_price.label("avg_price"),
                    PositionModel.market_price.label("market_price"),
                    PositionModel.market_value.label("market_value"),
                    PositionModel.unrealized_pnl.label("unrealized_pnl"),
                    PositionModel.snapshot_at.label("snapshot_at"),
                    func.row_number()
                    .over(
                        partition_by=(PositionModel.broker_account_id, PositionModel.symbol),
                        order_by=(PositionModel.snapshot_at.desc(), PositionModel.id.desc()),
                    )
                    .label("row_number"),
                )
                .where(PositionModel.broker_account_id == coerce_uuid(broker_account_id))
                .subquery()
            )
            rows = session.execute(select(ranked).where(ranked.c.row_number == 1).order_by(ranked.c.symbol.asc())).mappings().all()
        return [dict(row) for row in rows]

    def get_equity_curve(self, broker_account_id: str, *, days: int = 7, limit: int = 200) -> list[AccountBalanceModel]:
        window_start = datetime.now(UTC) - timedelta(days=days)
        with self._session_factory() as session:
            rows = session.execute(
                select(AccountBalanceModel)
                .where(AccountBalanceModel.broker_account_id == coerce_uuid(broker_account_id), AccountBalanceModel.snapshot_at >= window_start)
                .order_by(AccountBalanceModel.snapshot_at.asc(), AccountBalanceModel.id.asc())
                .limit(limit)
            ).scalars().all()
        return rows

    def count_open_orders(self, broker_account_id: str) -> int:
        open_statuses = {"PENDING_SUBMIT", "SUBMITTED", "OPEN", "PARTIALLY_FILLED", "CANCEL_REQUESTED"}
        with self._session_factory() as session:
            count = session.execute(
                select(func.count()).select_from(OrderModel).where(OrderModel.broker_account_id == coerce_uuid(broker_account_id), OrderModel.status.in_(open_statuses))
            ).scalar_one()
        return int(count or 0)

    def list_recent_orders(self, broker_account_id: str, *, limit: int = 10) -> list[OrderModel]:
        with self._session_factory() as session:
            rows = session.execute(
                select(OrderModel)
                .where(OrderModel.broker_account_id == coerce_uuid(broker_account_id))
                .order_by(OrderModel.submitted_at.desc(), OrderModel.updated_at.desc(), OrderModel.client_order_id.desc())
                .limit(limit)
            ).scalars().all()
        return rows

    def list_recent_risk_events(self, broker_account_id: str, *, limit: int = 10) -> list[tuple[RiskEventModel, str, str]]:
        with self._session_factory() as session:
            rows = session.execute(
                select(RiskEventModel, RiskRuleModel.name, RiskRuleModel.rule_type)
                .join(RiskRuleModel, RiskRuleModel.id == RiskEventModel.risk_rule_id)
                .where(RiskEventModel.broker_account_id == coerce_uuid(broker_account_id))
                .order_by(RiskEventModel.occurred_at.desc(), RiskEventModel.id.desc())
                .limit(limit)
            ).all()
        return rows
