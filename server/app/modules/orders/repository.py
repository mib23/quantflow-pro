from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.ids import coerce_uuid, sqlite_guid, uuid_str
from app.modules.orders.schemas import ExecutionItem, OrderItem
from app.modules.orders.status import normalize_order_status
from app.modules.orders.tables import audit_logs, broker_accounts, executions, orders


class OrderRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def list_orders(self, page: int, page_size: int, user_id: str | None = None) -> tuple[list[OrderItem], int]:
        offset = (page - 1) * page_size
        dialect_name = self._dialect_name()
        base_query = select(orders)
        count_query = select(func.count()).select_from(orders)
        if user_id is not None:
            user_id_value = self._guid_storage_value(user_id, dialect_name=dialect_name)
            base_query = base_query.join(broker_accounts, broker_accounts.c.id == orders.c.broker_account_id).where(
                broker_accounts.c.user_id == user_id_value
            )
            count_query = (
                select(func.count())
                .select_from(orders.join(broker_accounts, broker_accounts.c.id == orders.c.broker_account_id))
                .where(broker_accounts.c.user_id == user_id_value)
            )
        with self._session_factory() as session:
            total = session.scalar(count_query) or 0
            rows = session.execute(
                base_query.order_by(orders.c.submitted_at.desc(), orders.c.client_order_id.desc()).limit(page_size).offset(offset)
            ).mappings().all()
        return [self._serialize_order(row) for row in rows], int(total)

    def list_executions(self, page: int, page_size: int, user_id: str | None = None) -> tuple[list[ExecutionItem], int]:
        offset = (page - 1) * page_size
        dialect_name = self._dialect_name()
        from_clause = executions.join(orders, executions.c.order_id == orders.c.id)
        if user_id is not None:
            user_id_value = self._guid_storage_value(user_id, dialect_name=dialect_name)
            from_clause = from_clause.join(broker_accounts, broker_accounts.c.id == orders.c.broker_account_id)
        with self._session_factory() as session:
            total_query = select(func.count()).select_from(from_clause)
            if user_id is not None:
                total_query = total_query.where(broker_accounts.c.user_id == user_id_value)
            total = session.scalar(total_query) or 0
            stmt = (
                select(
                    executions.c.id.label("id"),
                    executions.c.order_id.label("order_id"),
                    orders.c.client_order_id.label("client_order_id"),
                    orders.c.broker_order_id.label("broker_order_id"),
                    orders.c.symbol.label("symbol"),
                    orders.c.side.label("side"),
                    executions.c.broker_execution_id.label("broker_execution_id"),
                    executions.c.filled_quantity.label("filled_quantity"),
                    executions.c.filled_price.label("filled_price"),
                    executions.c.fee_amount.label("fee_amount"),
                    executions.c.executed_at.label("executed_at"),
                )
                .select_from(from_clause)
                .order_by(executions.c.executed_at.desc(), executions.c.id.desc())
                .limit(page_size)
                .offset(offset)
            )
            if user_id is not None:
                stmt = stmt.where(broker_accounts.c.user_id == user_id_value)
            rows = session.execute(stmt).mappings().all()
        return [self._serialize_execution(row) for row in rows], int(total)

    def get_order_by_client_order_id(self, client_order_id: str) -> OrderItem | None:
        with self._session_factory() as session:
            row = session.execute(select(orders).where(orders.c.client_order_id == client_order_id)).mappings().one_or_none()
        return self._serialize_order(row) if row else None

    def get_order_by_idempotency_key(self, idempotency_key: str) -> OrderItem | None:
        with self._session_factory() as session:
            row = session.execute(select(orders).where(orders.c.idempotency_key == idempotency_key)).mappings().one_or_none()
        return self._serialize_order(row) if row else None

    def get_order_by_broker_order_id(self, broker_order_id: str) -> OrderItem | None:
        with self._session_factory() as session:
            row = session.execute(select(orders).where(orders.c.broker_order_id == broker_order_id)).mappings().one_or_none()
        return self._serialize_order(row) if row else None

    def get_order_by_id(self, order_id: str) -> OrderItem | None:
        dialect_name = self._dialect_name()
        with self._session_factory() as session:
            row = session.execute(select(orders).where(orders.c.id == self._guid_storage_value(order_id, dialect_name=dialect_name))).mappings().one_or_none()
        return self._serialize_order(row) if row else None

    def get_broker_account(self, broker_account_id: str) -> RowMapping | None:
        dialect_name = self._dialect_name()
        with self._session_factory() as session:
            row = session.execute(
                select(broker_accounts).where(broker_accounts.c.id == self._guid_storage_value(broker_account_id, dialect_name=dialect_name))
            ).mappings().one_or_none()
        if row is None:
            return None
        return self._normalize_guid_row(row)

    def create_order(self, values: Mapping[str, object]) -> OrderItem:
        payload = dict(values)
        client_order_id = str(payload["client_order_id"])
        idempotency_key = str(payload["idempotency_key"])
        with self._session_factory() as session:
            dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"
            payload["id"] = self._guid_storage_value(payload["id"], dialect_name=dialect_name)
            payload["broker_account_id"] = self._guid_storage_value(payload["broker_account_id"], dialect_name=dialect_name)
            try:
                with session.begin():
                    session.execute(insert(orders).values(payload))
            except IntegrityError:
                session.rollback()
                existing = self.get_order_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return existing
                raise
        return self.get_order_by_client_order_id(client_order_id)

    def update_order_fields(
        self,
        client_order_id: str,
        *,
        status: str | None = None,
        broker_order_id: str | None = None,
    ) -> OrderItem:
        values: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}
        if status is not None:
            values["status"] = normalize_order_status(status)
        if broker_order_id is not None:
            values["broker_order_id"] = broker_order_id
        with self._session_factory() as session:
            with session.begin():
                session.execute(update(orders).where(orders.c.client_order_id == client_order_id).values(values))
        updated = self.get_order_by_client_order_id(client_order_id)
        if updated is None:
            raise ValueError(f"Order {client_order_id} disappeared after update.")
        return updated

    def create_execution(self, values: Mapping[str, object]) -> ExecutionItem:
        payload = dict(values)
        broker_execution_id = str(payload["broker_execution_id"])
        with self._session_factory() as session:
            dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"
            payload["id"] = self._guid_storage_value(payload["id"], dialect_name=dialect_name)
            payload["order_id"] = self._guid_storage_value(payload["order_id"], dialect_name=dialect_name)
            try:
                with session.begin():
                    session.execute(insert(executions).values(payload))
            except IntegrityError:
                session.rollback()
                existing = self.get_execution_by_broker_execution_id(broker_execution_id)
                if existing is not None:
                    return existing
                raise
        return self.get_execution_by_broker_execution_id(broker_execution_id)

    def get_execution_by_broker_execution_id(self, broker_execution_id: str) -> ExecutionItem | None:
        with self._session_factory() as session:
            stmt = (
                select(
                    executions.c.id.label("id"),
                    executions.c.order_id.label("order_id"),
                    orders.c.client_order_id.label("client_order_id"),
                    orders.c.broker_order_id.label("broker_order_id"),
                    orders.c.symbol.label("symbol"),
                    orders.c.side.label("side"),
                    executions.c.broker_execution_id.label("broker_execution_id"),
                    executions.c.filled_quantity.label("filled_quantity"),
                    executions.c.filled_price.label("filled_price"),
                    executions.c.fee_amount.label("fee_amount"),
                    executions.c.executed_at.label("executed_at"),
                )
                .select_from(executions.join(orders, executions.c.order_id == orders.c.id))
                .where(executions.c.broker_execution_id == broker_execution_id)
            )
            row = session.execute(stmt).mappings().one_or_none()
        return self._serialize_execution(row) if row else None

    def get_filled_quantity_total(self, order_id: str) -> Decimal:
        dialect_name = self._dialect_name()
        with self._session_factory() as session:
            total = session.scalar(
                select(func.coalesce(func.sum(executions.c.filled_quantity), 0)).where(
                    executions.c.order_id == self._guid_storage_value(order_id, dialect_name=dialect_name)
                )
            )
        return Decimal(str(total or 0))

    def create_audit_log(
        self,
        *,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        before_state: dict[str, object] | None = None,
        after_state: dict[str, object] | None = None,
    ) -> None:
        dialect_name = self._dialect_name()
        with self._session_factory() as session:
            with session.begin():
                session.execute(
                    insert(audit_logs).values(
                        {
                            "id": self._guid_storage_value(uuid4(), dialect_name=dialect_name),
                            "user_id": self._guid_storage_value(user_id, dialect_name=dialect_name),
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "action": action,
                            "before_state": before_state,
                            "after_state": after_state,
                            "created_at": datetime.now(timezone.utc),
                        }
                    )
                )

    @staticmethod
    def _serialize_order(row: RowMapping | None) -> OrderItem | None:
        if row is None:
            return None
        payload = dict(row)
        payload = OrderRepository._normalize_guid_row(payload)
        payload["status"] = normalize_order_status(str(payload["status"]))
        return OrderItem.model_validate(payload)

    @staticmethod
    def _serialize_execution(row: RowMapping | None) -> ExecutionItem | None:
        if row is None:
            return None
        payload = dict(row)
        payload = OrderRepository._normalize_guid_row(payload)
        return ExecutionItem.model_validate(payload)

    @staticmethod
    def _normalize_guid_row(row: Mapping[str, object]) -> dict[str, object]:
        payload = dict(row)
        for key in ("id", "user_id", "broker_account_id", "order_id"):
            value = payload.get(key)
            if value is None:
                continue
            try:
                payload[key] = uuid_str(value)
            except Exception:
                continue
        return payload

    def _guid_storage_value(self, value: object, *, dialect_name: str) -> str:
        guid = coerce_uuid(value)
        return sqlite_guid(guid) if dialect_name == "sqlite" else uuid_str(guid)

    def _dialect_name(self) -> str:
        with self._session_factory() as session:
            return session.bind.dialect.name if session.bind is not None else "sqlite"
