"""phase4 runtime sim live

Revision ID: 20260417_0004
Revises: 20260416_0003
Create Date: 2026-04-17 12:15:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260417_0004"
down_revision = "20260416_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_versions.id"), nullable=False),
        sa.Column("broker_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("broker_accounts.id"), nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CREATED"),
        sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("parameters_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("deployment_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_timeout_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broker_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_runtime_instances_account_status", "runtime_instances", ["broker_account_id", "status", "created_at"])
    op.create_index("ix_runtime_instances_submitter_created", "runtime_instances", ["submitted_by", "created_at"])

    op.create_table(
        "deployment_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtime_instances.id"), nullable=False, unique=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "runtime_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtime_instances.id"), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_runtime_logs_instance_created", "runtime_logs", ["runtime_instance_id", "created_at"])

    op.create_table(
        "runtime_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtime_instances.id"), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_runtime_alerts_instance_created", "runtime_alerts", ["runtime_instance_id", "created_at"])

    op.add_column("orders", sa.Column("runtime_instance_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_runtime_instance_id",
        "orders",
        "runtime_instances",
        ["runtime_instance_id"],
        ["id"],
    )
    op.create_index("ix_orders_runtime_instance_id", "orders", ["runtime_instance_id"])

    op.add_column("risk_events", sa.Column("runtime_instance_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_risk_events_runtime_instance_id",
        "risk_events",
        "runtime_instances",
        ["runtime_instance_id"],
        ["id"],
    )
    op.create_index("ix_risk_events_runtime_instance_id", "risk_events", ["runtime_instance_id"])


def downgrade() -> None:
    op.drop_index("ix_risk_events_runtime_instance_id", table_name="risk_events")
    op.drop_constraint("fk_risk_events_runtime_instance_id", "risk_events", type_="foreignkey")
    op.drop_column("risk_events", "runtime_instance_id")

    op.drop_index("ix_orders_runtime_instance_id", table_name="orders")
    op.drop_constraint("fk_orders_runtime_instance_id", "orders", type_="foreignkey")
    op.drop_column("orders", "runtime_instance_id")

    op.drop_index("ix_runtime_alerts_instance_created", table_name="runtime_alerts")
    op.drop_table("runtime_alerts")
    op.drop_index("ix_runtime_logs_instance_created", table_name="runtime_logs")
    op.drop_table("runtime_logs")
    op.drop_table("deployment_approvals")
    op.drop_index("ix_runtime_instances_submitter_created", table_name="runtime_instances")
    op.drop_index("ix_runtime_instances_account_status", table_name="runtime_instances")
    op.drop_table("runtime_instances")
