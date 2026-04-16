from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, ForeignKey, MetaData, Numeric, String, Table
from sqlalchemy.dialects.postgresql import UUID

guid_type = String(36).with_variant(UUID(as_uuid=False), "postgresql")

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", guid_type, primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("full_name", String(255), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(50), nullable=False),
    Column("status", String(50), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

broker_accounts = Table(
    "broker_accounts",
    metadata,
    Column("id", guid_type, primary_key=True),
    Column("user_id", guid_type, ForeignKey("users.id"), nullable=False),
    Column("broker_name", String(50), nullable=False),
    Column("broker_account_no", String(100), nullable=False, unique=True),
    Column("external_account_id", String(100), nullable=False, unique=True),
    Column("environment", String(20), nullable=False),
    Column("status", String(50), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

orders = Table(
    "orders",
    metadata,
    Column("id", guid_type, primary_key=True),
    Column("broker_account_id", guid_type, ForeignKey("broker_accounts.id"), nullable=False),
    Column("client_order_id", String(100), nullable=False, unique=True),
    Column("broker_order_id", String(100), nullable=True, unique=True),
    Column("symbol", String(32), nullable=False),
    Column("side", String(10), nullable=False),
    Column("order_type", String(20), nullable=False),
    Column("quantity", Numeric(18, 6), nullable=False),
    Column("limit_price", Numeric(18, 4), nullable=True),
    Column("status", String(32), nullable=False),
    Column("time_in_force", String(10), nullable=False),
    Column("idempotency_key", String(120), nullable=False, unique=True),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

executions = Table(
    "executions",
    metadata,
    Column("id", guid_type, primary_key=True),
    Column("order_id", guid_type, ForeignKey("orders.id"), nullable=False),
    Column("broker_execution_id", String(100), nullable=False, unique=True),
    Column("filled_quantity", Numeric(18, 6), nullable=False),
    Column("filled_price", Numeric(18, 4), nullable=False),
    Column("fee_amount", Numeric(18, 4), nullable=False),
    Column("executed_at", DateTime(timezone=True), nullable=False),
)

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", guid_type, primary_key=True),
    Column("user_id", guid_type, ForeignKey("users.id"), nullable=False),
    Column("resource_type", String(50), nullable=False),
    Column("resource_id", String(100), nullable=False),
    Column("action", String(50), nullable=False),
    Column("before_state", JSON, nullable=True),
    Column("after_state", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
