import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CHAR, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class GUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class BrokerAccountModel(Base):
    __tablename__ = "broker_accounts"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(50), nullable=False)
    broker_account_no: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    external_account_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class AccountBalanceModel(Base):
    __tablename__ = "account_balances"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    broker_account_id: Mapped[str] = mapped_column(GUID(), ForeignKey("broker_accounts.id"), nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    buying_power: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    day_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PositionModel(Base):
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    broker_account_id: Mapped[str] = mapped_column(GUID(), ForeignKey("broker_accounts.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    market_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    broker_account_id: Mapped[str] = mapped_column(GUID(), ForeignKey("broker_accounts.id"), nullable=False)
    runtime_instance_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("runtime_instances.id"), nullable=True)
    client_order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    time_in_force: Mapped[str] = mapped_column(String(10), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExecutionModel(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=False)
    broker_execution_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    filled_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"), server_default="0")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskRuleModel(Base):
    __tablename__ = "risk_rules"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Unnamed risk rule", server_default="Unnamed risk rule")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_accounts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    scope_symbols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class RiskEventModel(Base):
    __tablename__ = "risk_events"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    risk_rule_id: Mapped[str] = mapped_column(GUID(), ForeignKey("risk_rules.id"), nullable=False)
    broker_account_id: Mapped[str] = mapped_column(GUID(), ForeignKey("broker_accounts.id"), nullable=False)
    runtime_instance_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("runtime_instances.id"), nullable=True)
    order_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=True)
    client_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="BLOCKED", server_default="BLOCKED")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskRuleVersionModel(Base):
    __tablename__ = "risk_rule_versions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    risk_rule_id: Mapped[str] = mapped_column(GUID(), ForeignKey("risk_rules.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )


class StrategyModel(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT", server_default="DRAFT")
    default_parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    default_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class StrategyVersionModel(Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version_number", name="uq_strategy_versions_strategy_version"),)

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id: Mapped[str] = mapped_column(GUID(), ForeignKey("strategies.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    code_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    parameter_template: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )


class RuntimeInstanceModel(Base):
    __tablename__ = "runtime_instances"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id: Mapped[str] = mapped_column(GUID(), ForeignKey("strategies.id"), nullable=False)
    strategy_version_id: Mapped[str] = mapped_column(GUID(), ForeignKey("strategy_versions.id"), nullable=False)
    broker_account_id: Mapped[str] = mapped_column(GUID(), ForeignKey("broker_accounts.id"), nullable=False)
    submitted_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED", server_default="CREATED")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_REQUIRED", server_default="NOT_REQUIRED")
    parameters_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    deployment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120, server_default="120")
    restart_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    broker_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class DeploymentApprovalModel(Base):
    __tablename__ = "deployment_approvals"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    runtime_instance_id: Mapped[str] = mapped_column(GUID(), ForeignKey("runtime_instances.id"), nullable=False, unique=True)
    requested_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class RuntimeLogEntryModel(Base):
    __tablename__ = "runtime_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    runtime_instance_id: Mapped[str] = mapped_column(GUID(), ForeignKey("runtime_instances.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )


class RuntimeAlertModel(Base):
    __tablename__ = "runtime_alerts"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    runtime_instance_id: Mapped[str] = mapped_column(GUID(), ForeignKey("runtime_instances.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN", server_default="OPEN")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class BacktestJobModel(Base):
    __tablename__ = "backtest_jobs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id: Mapped[str] = mapped_column(GUID(), ForeignKey("strategies.id"), nullable=False)
    strategy_version_id: Mapped[str] = mapped_column(GUID(), ForeignKey("strategy_versions.id"), nullable=False)
    submitted_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", server_default="QUEUED")
    start_date: Mapped[date] = mapped_column(Date(), nullable=False)
    end_date: Mapped[date] = mapped_column(Date(), nullable=False)
    symbols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parameters_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    queue_name: Mapped[str] = mapped_column(String(100), nullable=False, default="default", server_default="default")
    execution_environment: Mapped[str] = mapped_column(String(50), nullable=False, default="test", server_default="test")
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class BacktestResultModel(Base):
    __tablename__ = "backtest_results"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    backtest_job_id: Mapped[str] = mapped_column(GUID(), ForeignKey("backtest_jobs.id"), nullable=False, unique=True)
    summary_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    equity_curve: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    trade_summary: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    report_format: Mapped[str] = mapped_column(String(20), nullable=False, default="json", server_default="json")
    report_body: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("now()")
    )


class BacktestLogModel(Base):
    __tablename__ = "backtest_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    backtest_job_id: Mapped[str] = mapped_column(GUID(), ForeignKey("backtest_jobs.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=text("now()")
    )
