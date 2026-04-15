"""phase2 dashboard risk

Revision ID: 20260415_0002
Revises: 20260414_0001
Create Date: 2026-04-15 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260415_0002"
down_revision = "20260414_0001"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "risk_rules" in tables:
        if not _has_column(inspector, "risk_rules", "name"):
            op.add_column("risk_rules", sa.Column("name", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "risk_rules", "description"):
            op.add_column("risk_rules", sa.Column("description", sa.Text(), nullable=True))
        if not _has_column(inspector, "risk_rules", "scope_accounts"):
            op.add_column("risk_rules", sa.Column("scope_accounts", sa.JSON(), nullable=True))
        if not _has_column(inspector, "risk_rules", "scope_symbols"):
            op.add_column("risk_rules", sa.Column("scope_symbols", sa.JSON(), nullable=True))

    if "risk_events" in tables:
        if not _has_column(inspector, "risk_events", "broker_account_id"):
            op.add_column("risk_events", sa.Column("broker_account_id", postgresql.UUID(as_uuid=True), nullable=True))
        if not _has_column(inspector, "risk_events", "client_order_id"):
            op.add_column("risk_events", sa.Column("client_order_id", sa.String(length=100), nullable=True))
        if not _has_column(inspector, "risk_events", "reason"):
            op.add_column("risk_events", sa.Column("reason", sa.Text(), nullable=True))
        if not _has_column(inspector, "risk_events", "status"):
            op.add_column("risk_events", sa.Column("status", sa.String(length=20), nullable=True))
        if not _has_column(inspector, "risk_events", "dedupe_key"):
            op.add_column("risk_events", sa.Column("dedupe_key", sa.String(length=255), nullable=True))
        if not _has_index(inspector, "risk_events", "ix_risk_events_dedupe_key"):
            op.create_index("ix_risk_events_dedupe_key", "risk_events", ["dedupe_key"], unique=True)
        if not _has_index(inspector, "risk_events", "ix_risk_events_account_occurred"):
            op.create_index("ix_risk_events_account_occurred", "risk_events", ["broker_account_id", "occurred_at"])

    if "audit_logs" in tables and not _has_column(inspector, "audit_logs", "trace_id"):
        op.add_column("audit_logs", sa.Column("trace_id", sa.String(length=100), nullable=True))

    if "risk_rule_versions" not in tables:
        op.create_table(
            "risk_rule_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("risk_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_rules.id"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("change_reason", sa.Text(), nullable=True),
            sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    inspector = sa.inspect(bind)
    if "risk_rule_versions" in inspector.get_table_names() and not _has_index(inspector, "risk_rule_versions", "ix_risk_rule_versions_rule_version"):
        op.create_index("ix_risk_rule_versions_rule_version", "risk_rule_versions", ["risk_rule_id", "version"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_risk_rule_versions_rule_version", table_name="risk_rule_versions")
    op.drop_table("risk_rule_versions")

    op.drop_column("audit_logs", "trace_id")

    op.drop_index("ix_risk_events_account_occurred", table_name="risk_events")
    op.drop_index("ix_risk_events_dedupe_key", table_name="risk_events")
    op.drop_column("risk_events", "dedupe_key")
    op.drop_column("risk_events", "status")
    op.drop_column("risk_events", "reason")
    op.drop_column("risk_events", "client_order_id")
    op.drop_column("risk_events", "broker_account_id")

    op.drop_column("risk_rules", "scope_symbols")
    op.drop_column("risk_rules", "scope_accounts")
    op.drop_column("risk_rules", "description")
    op.drop_column("risk_rules", "name")
