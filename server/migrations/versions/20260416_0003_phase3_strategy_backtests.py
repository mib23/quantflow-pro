"""phase3 strategy backtests

Revision ID: 20260416_0003
Revises: 20260415_0002
Create Date: 2026-04-16 15:55:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260416_0003"
down_revision = "20260415_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("default_parameters", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("default_version_id", sa.String(length=36), nullable=True),
        sa.Column("latest_version_id", sa.String(length=36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategies_created_by_updated_at", "strategies", ["created_by", "updated_at"])

    op.create_table(
        "strategy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("code_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("parameter_template", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("strategy_id", "version_number", name="uq_strategy_versions_strategy_version"),
    )
    op.create_index("ix_strategy_versions_strategy_created", "strategy_versions", ["strategy_id", "created_at"])

    op.create_table(
        "backtest_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_versions.id"), nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("symbols", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("benchmark_symbol", sa.String(length=32), nullable=True),
        sa.Column("parameters_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("queue_name", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("execution_environment", sa.String(length=50), nullable=False, server_default="test"),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backtest_jobs_submitted_status", "backtest_jobs", ["submitted_by", "status", "submitted_at"])
    op.create_index("ix_backtest_jobs_strategy_version", "backtest_jobs", ["strategy_version_id"])

    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backtest_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_jobs.id"), nullable=False, unique=True),
        sa.Column("summary_metrics", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("equity_curve", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("trade_summary", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("report_format", sa.String(length=20), nullable=False, server_default="json"),
        sa.Column("report_body", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "backtest_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backtest_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_jobs.id"), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backtest_logs_job_created", "backtest_logs", ["backtest_job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_backtest_logs_job_created", table_name="backtest_logs")
    op.drop_table("backtest_logs")
    op.drop_table("backtest_results")
    op.drop_index("ix_backtest_jobs_strategy_version", table_name="backtest_jobs")
    op.drop_index("ix_backtest_jobs_submitted_status", table_name="backtest_jobs")
    op.drop_table("backtest_jobs")
    op.drop_index("ix_strategy_versions_strategy_created", table_name="strategy_versions")
    op.drop_table("strategy_versions")
    op.drop_index("ix_strategies_created_by_updated_at", table_name="strategies")
    op.drop_table("strategies")
