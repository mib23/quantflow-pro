"""repair strategy and backtest schema drift

Revision ID: 20260419_0005
Revises: 20260417_0004
Create Date: 2026-04-19 23:50:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260419_0005"
down_revision = "20260417_0004"
branch_labels = None
depends_on = None


def _table_names(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table_name: str) -> dict[str, dict[str, object]]:
    return {column["name"]: column for column in sa.inspect(bind).get_columns(table_name)}


def _rename_column_if_present(
    bind,
    table_name: str,
    *,
    old_name: str,
    new_name: str,
    existing_type,
    existing_nullable: bool = True,
) -> None:
    cols = _columns(bind, table_name)
    if old_name in cols and new_name not in cols:
        op.alter_column(
            table_name,
            old_name,
            new_column_name=new_name,
            existing_type=existing_type,
            existing_nullable=existing_nullable,
        )


def upgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    if "strategies" in tables:
        _rename_column_if_present(
            bind,
            "strategies",
            old_name="created_by",
            new_name="owner_user_id",
            existing_type=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
        )
        cols = _columns(bind, "strategies")
        if "latest_version_id" in cols and isinstance(cols["latest_version_id"]["type"], sa.String):
            op.execute(
                """
                ALTER TABLE strategies
                ALTER COLUMN latest_version_id TYPE uuid
                USING NULLIF(latest_version_id::text, '')::uuid
                """
            )

    if "strategy_versions" in tables:
        cols = _columns(bind, "strategy_versions")
        if "code_snapshot" in cols and isinstance(cols["code_snapshot"]["type"], sa.JSON):
            op.execute(
                """
                ALTER TABLE strategy_versions
                ALTER COLUMN code_snapshot TYPE text
                USING CASE
                    WHEN code_snapshot IS NULL THEN NULL
                    WHEN jsonb_typeof(code_snapshot::jsonb) = 'string'
                        THEN trim(both '"' from code_snapshot::text)
                    ELSE code_snapshot::text
                END
                """
            )
        _rename_column_if_present(
            bind,
            "strategy_versions",
            old_name="parameter_template",
            new_name="parameters_snapshot",
            existing_type=sa.JSON(),
            existing_nullable=False,
        )
        _rename_column_if_present(
            bind,
            "strategy_versions",
            old_name="change_reason",
            new_name="version_note",
            existing_type=sa.Text(),
            existing_nullable=True,
        )
        cols = _columns(bind, "strategy_versions")
        if "parameters_snapshot" not in cols:
            op.add_column(
                "strategy_versions",
                sa.Column("parameters_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            )
        if "version_note" not in cols:
            op.add_column("strategy_versions", sa.Column("version_note", sa.Text(), nullable=True))

    if "backtest_jobs" in tables:
        _rename_column_if_present(
            bind,
            "backtest_jobs",
            old_name="benchmark_symbol",
            new_name="benchmark",
            existing_type=sa.String(length=32),
            existing_nullable=True,
        )
        _rename_column_if_present(
            bind,
            "backtest_jobs",
            old_name="failure_message",
            new_name="failure_reason",
            existing_type=sa.Text(),
            existing_nullable=True,
        )
        cols = _columns(bind, "backtest_jobs")
        if "queue_job_id" not in cols:
            op.add_column("backtest_jobs", sa.Column("queue_job_id", sa.String(length=128), nullable=True))
        if "dataset_key" not in cols:
            op.add_column(
                "backtest_jobs",
                sa.Column(
                    "dataset_key",
                    sa.String(length=128),
                    nullable=False,
                    server_default="demo-momentum",
                ),
            )
        if "time_range" not in cols:
            op.add_column(
                "backtest_jobs",
                sa.Column("time_range", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            )
            if "start_date" in cols or "end_date" in cols:
                op.execute(
                    """
                    UPDATE backtest_jobs
                    SET time_range = json_build_object(
                        'start', CASE WHEN start_date IS NULL THEN NULL ELSE start_date::text END,
                        'end', CASE WHEN end_date IS NULL THEN NULL ELSE end_date::text END
                    )
                    WHERE start_date IS NOT NULL OR end_date IS NOT NULL
                    """
                )
        if "cancellation_requested" not in cols:
            op.add_column(
                "backtest_jobs",
                sa.Column(
                    "cancellation_requested",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                ),
            )
            if "canceled_at" in cols:
                op.execute(
                    """
                    UPDATE backtest_jobs
                    SET cancellation_requested = true
                    WHERE canceled_at IS NOT NULL OR upper(status) = 'CANCELED'
                    """
                )
        if "retry_of_job_id" not in cols:
            op.add_column("backtest_jobs", sa.Column("retry_of_job_id", postgresql.UUID(as_uuid=True), nullable=True))
        if "created_at" not in cols:
            op.add_column(
                "backtest_jobs",
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            )
            if "submitted_at" in cols:
                op.execute("UPDATE backtest_jobs SET created_at = submitted_at WHERE submitted_at IS NOT NULL")
        cols = _columns(bind, "backtest_jobs")
        if "benchmark" not in cols:
            op.add_column("backtest_jobs", sa.Column("benchmark", sa.String(length=32), nullable=True))
        if "failure_reason" not in cols:
            op.add_column("backtest_jobs", sa.Column("failure_reason", sa.Text(), nullable=True))

    if "backtest_results" in tables:
        _rename_column_if_present(
            bind,
            "backtest_results",
            old_name="backtest_job_id",
            new_name="job_id",
            existing_type=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
        )
        _rename_column_if_present(
            bind,
            "backtest_results",
            old_name="summary_metrics",
            new_name="metrics_summary",
            existing_type=sa.JSON(),
            existing_nullable=False,
        )
        _rename_column_if_present(
            bind,
            "backtest_results",
            old_name="report_body",
            new_name="report",
            existing_type=sa.JSON(),
            existing_nullable=False,
        )
        cols = _columns(bind, "backtest_results")
        if "trades" not in cols:
            op.add_column("backtest_results", sa.Column("trades", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
            if "trade_summary" in cols:
                op.execute(
                    """
                    UPDATE backtest_results
                    SET trades = CASE
                        WHEN trade_summary IS NULL THEN '[]'::json
                        WHEN jsonb_typeof(trade_summary::jsonb) = 'array' THEN trade_summary
                        ELSE '[]'::json
                    END
                    """
                )
        if "generated_at" not in cols:
            op.add_column(
                "backtest_results",
                sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            )
            source_column = "updated_at" if "updated_at" in cols else "created_at" if "created_at" in cols else None
            if source_column is not None:
                op.execute(f"UPDATE backtest_results SET generated_at = {source_column} WHERE {source_column} IS NOT NULL")

    if "backtest_logs" in tables:
        _rename_column_if_present(
            bind,
            "backtest_logs",
            old_name="backtest_job_id",
            new_name="job_id",
            existing_type=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
        )
        cols = _columns(bind, "backtest_logs")
        if "code" not in cols:
            op.add_column(
                "backtest_logs",
                sa.Column("code", sa.String(length=64), nullable=False, server_default="LEGACY_LOG"),
            )
        if "details" not in cols:
            op.add_column("backtest_logs", sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
            if "trace_id" in cols:
                op.execute(
                    """
                    UPDATE backtest_logs
                    SET details = json_build_object('trace_id', trace_id)
                    WHERE trace_id IS NOT NULL AND trace_id <> ''
                    """
                )


def downgrade() -> None:
    raise NotImplementedError("This repair migration is not reversible.")
