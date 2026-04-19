from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_engine, get_session_factory
from app.core.models import (
    AccountBalanceModel,
    BrokerAccountModel,
    PositionModel,
    UserModel,
)
from app.modules.auth.security import hash_password
from app.modules.risk.seed import seed_default_risk_data


def ensure_local_baseline() -> None:
    try:
        engine = get_engine()
        required_tables = {
            "users",
            "broker_accounts",
            "account_balances",
            "positions",
            "risk_rules",
            "risk_events",
            "risk_rule_versions",
        }
        existing_tables = set(inspect(engine).get_table_names())
        if not required_tables.issubset(existing_tables):
            return

        session_factory = get_session_factory()
        with session_factory() as session:
            existing_user = session.query(UserModel).filter(UserModel.email == "alex@quantflow.local").one_or_none()
            if existing_user is None:
                existing_user = UserModel(
                    id=uuid.uuid4(),
                    email="alex@quantflow.local",
                    full_name="Alex Johnson",
                    password_hash=hash_password("quantflow-demo"),
                    role="ADMIN",
                    status="ACTIVE",
                )
                session.add(existing_user)
                session.flush()

            trader_user = session.query(UserModel).filter(UserModel.email == "trader@quantflow.local").one_or_none()
            if trader_user is None:
                trader_user = UserModel(
                    id=uuid.uuid4(),
                    email="trader@quantflow.local",
                    full_name="Taylor Trader",
                    password_hash=hash_password("quantflow-demo"),
                    role="TRADER",
                    status="ACTIVE",
                )
                session.add(trader_user)
                session.flush()

            account = session.query(BrokerAccountModel).filter(BrokerAccountModel.user_id == existing_user.id).one_or_none()
            if account is None:
                account = BrokerAccountModel(
                    id=uuid.uuid4(),
                    user_id=existing_user.id,
                    broker_name="ALPACA",
                    broker_account_no="PA-10001",
                    external_account_id="paper-demo-001",
                    environment="paper",
                    status="ACTIVE",
                )
                session.add(account)
                session.flush()

            now = datetime.now(UTC)
            latest_balance = (
                session.query(AccountBalanceModel)
                .filter(AccountBalanceModel.broker_account_id == account.id)
                .order_by(AccountBalanceModel.snapshot_at.desc())
                .first()
            )
            if latest_balance is None:
                baseline_points = [
                    ("124010.00", "41850.00", "199640.00", "-210.00", now - timedelta(hours=4)),
                    ("124220.00", "41680.00", "200120.00", "120.00", now - timedelta(hours=3)),
                    ("124480.00", "41420.00", "201100.00", "480.00", now - timedelta(hours=2)),
                    ("124592.40", "41240.00", "201840.00", "1240.50", now),
                ]
                for equity, cash, buying_power, day_pnl, snapshot_at in baseline_points:
                    session.add(
                        AccountBalanceModel(
                            id=uuid.uuid4(),
                            broker_account_id=account.id,
                            equity=Decimal(equity),
                            cash=Decimal(cash),
                            buying_power=Decimal(buying_power),
                            day_pnl=Decimal(day_pnl),
                            snapshot_at=snapshot_at,
                        )
                    )

            existing_symbols = {position.symbol for position in session.query(PositionModel).filter(PositionModel.broker_account_id == account.id)}
            if "TSLA" not in existing_symbols:
                session.add(
                    PositionModel(
                        id=uuid.uuid4(),
                        broker_account_id=account.id,
                        symbol="TSLA",
                        quantity=Decimal("100"),
                        avg_price=Decimal("240.50"),
                        market_price=Decimal("245.50"),
                        market_value=Decimal("24550.00"),
                        unrealized_pnl=Decimal("500.00"),
                        snapshot_at=now,
                    )
                )
            if "NVDA" not in existing_symbols:
                session.add(
                    PositionModel(
                        id=uuid.uuid4(),
                        broker_account_id=account.id,
                        symbol="NVDA",
                        quantity=Decimal("50"),
                        avg_price=Decimal("480.00"),
                        market_price=Decimal("476.20"),
                        market_value=Decimal("23810.00"),
                        unrealized_pnl=Decimal("-190.00"),
                        snapshot_at=now,
                    )
                )

            seed_default_risk_data(session, owner=existing_user, account=account, now=now)

            session.commit()
    except SQLAlchemyError:
        return
