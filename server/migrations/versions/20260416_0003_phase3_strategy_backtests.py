"""phase3 strategy backtests

Revision ID: 20260416_0003
Revises: 20260415_0002
Create Date: 2026-04-16 16:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260416_0003"
down_revision = "20260415_0002"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "strategies"):
        op.create_table(
            "strategies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
            sa.Column("default_parameters", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("latest_version_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if not _has_table(inspector, "strategy_versions"):
        op.create_table(
            "strategy_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("code_snapshot", sa.Text(), nullable=False),
            sa.Column("parameters_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("version_note", sa.Text(), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if not _has_table(inspector, "backtest_jobs"):
        op.create_table(
            "backtest_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
            sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_versions.id"), nullable=False),
            sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
            sa.Column("queue_name", sa.String(length=64), nullable=False, server_default="backtests"),
            sa.Column("queue_job_id", sa.String(length=128), nullable=True),
            sa.Column("dataset_key", sa.String(length=128), nullable=False, server_default="demo-momentum"),
            sa.Column("symbols", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("parameters_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("benchmark", sa.String(length=32), nullable=True),
            sa.Column("time_range", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("failure_code", sa.String(length=64), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("retry_of_job_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if not _has_table(inspector, "backtest_results"):
        op.create_table(
            "backtest_results",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_jobs.id"), nullable=False, unique=True),
            sa.Column("metrics_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("equity_curve", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("trades", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("report", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("report_format", sa.String(length=16), nullable=False, server_default="json"),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if not _has_table(inspector, "backtest_logs"):
        op.create_table(
            "backtest_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_jobs.id"), nullable=False),
            sa.Column("level", sa.String(length=16), nullable=False, server_default="INFO"),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )


def downgrade() -> None:
    op.drop_table("backtest_logs")
    op.drop_table("backtest_results")
    op.drop_table("backtest_jobs")
    op.drop_table("strategy_versions")
    op.drop_table("strategies")
