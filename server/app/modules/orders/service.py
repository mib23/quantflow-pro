from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from uuid import uuid4

from fastapi import status
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_sync_engine
from app.core.exceptions import ApiException
from app.core.realtime import realtime_hub
from app.core.settings import get_settings
from app.modules.orders.broker import BrokerGateway, BrokerOrderUpdate, NullBrokerGateway
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    ExecutionItem,
    ExecutionListData,
    OrderItem,
    OrderListData,
    PlaceOrderRequest,
    PlaceOrderResponse,
    RiskCheckResult,
)
from app.modules.orders.status import is_final_order_status, normalize_order_status


@lru_cache
def get_order_session_factory() -> Callable[[], Session]:
    settings = get_settings()
    engine = create_sync_engine(settings.database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_order_repository() -> OrderRepository:
    return OrderRepository(get_order_session_factory())


def get_broker_gateway() -> BrokerGateway:
    return NullBrokerGateway()


def get_order_service() -> "OrderService":
    return OrderService(get_order_repository(), get_broker_gateway())


class OrderService:
    def __init__(self, repository: OrderRepository, broker_gateway: BrokerGateway | None = None):
        self._repository = repository
        self._broker_gateway = broker_gateway or NullBrokerGateway()

    def list_orders(self, page: int = 1, page_size: int = 20, user_id: str | None = None) -> OrderListData:
        items, total = self._repository.list_orders(page=page, page_size=page_size, user_id=user_id)
        return OrderListData(items=items, page=page, page_size=page_size, total=total)

    def list_executions(self, page: int = 1, page_size: int = 20, user_id: str | None = None) -> ExecutionListData:
        items, total = self._repository.list_executions(page=page, page_size=page_size, user_id=user_id)
        return ExecutionListData(items=items, page=page, page_size=page_size, total=total)

    def place_order(self, payload: PlaceOrderRequest, user_id: str | None = None) -> PlaceOrderResponse:
        broker_account = self._require_active_broker_account(payload.broker_account_id)
        if user_id is not None and str(broker_account["user_id"]) != user_id:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        existing = self._repository.get_order_by_idempotency_key(payload.idempotency_key)
        if existing is not None:
            self._assert_idempotent_order(existing, payload)
            return PlaceOrderResponse(**existing.model_dump(), risk_check=RiskCheckResult())

        created = self._repository.create_order(
            {
                "id": str(uuid4()),
                "broker_account_id": payload.broker_account_id,
                "client_order_id": self._generate_client_order_id(payload.idempotency_key),
                "broker_order_id": None,
                "symbol": payload.symbol,
                "side": payload.side,
                "order_type": payload.order_type,
                "quantity": payload.quantity,
                "limit_price": payload.limit_price,
                "status": "PENDING_SUBMIT",
                "time_in_force": payload.time_in_force,
                "idempotency_key": payload.idempotency_key,
                "submitted_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        self._repository.create_audit_log(
            user_id=str(broker_account["user_id"]),
            resource_type="ORDER",
            resource_id=created.client_order_id,
            action="ORDER_CREATED",
            after_state=created.model_dump(mode="json"),
        )

        risk_check = RiskCheckResult()
        try:
            broker_update = self._broker_gateway.submit_order(created.model_dump(mode="json"))
        except Exception as exc:  # pragma: no cover - safety path
            failed = self._repository.update_order_fields(created.client_order_id, status="FAILED")
            self._repository.create_audit_log(
                user_id=str(broker_account["user_id"]),
                resource_type="ORDER",
                resource_id=created.client_order_id,
                action="ORDER_SUBMIT_FAILED",
                before_state=created.model_dump(mode="json"),
                after_state=failed.model_dump(mode="json"),
            )
            raise ApiException("ORDER_BROKER_SUBMISSION_FAILED", str(exc), status.HTTP_502_BAD_GATEWAY) from exc

        if broker_update is not None:
            created = self._sync_broker_update(created.client_order_id, broker_update, default_status="SUBMITTED")
            self._publish_order_event(created.broker_account_id, created)

        return PlaceOrderResponse(**created.model_dump(), risk_check=risk_check)

    def cancel_order(self, client_order_id: str, user_id: str | None = None) -> OrderItem:
        order = self._require_order(client_order_id)
        if is_final_order_status(order.status) or order.status == "CANCEL_REQUESTED":
            return order

        broker_account = self._require_active_broker_account(order.broker_account_id)
        if user_id is not None and str(broker_account["user_id"]) != user_id:
            raise ApiException("ORDER_NOT_FOUND", "Order not found.", status.HTTP_404_NOT_FOUND)
        requested = self._repository.update_order_fields(client_order_id, status="CANCEL_REQUESTED")
        self._repository.create_audit_log(
            user_id=str(broker_account["user_id"]),
            resource_type="ORDER",
            resource_id=requested.client_order_id,
            action="ORDER_CANCEL_REQUESTED",
            before_state=order.model_dump(mode="json"),
            after_state=requested.model_dump(mode="json"),
        )

        if requested.broker_order_id is None:
            self._publish_order_event(requested.broker_account_id, requested)
            return requested

        try:
            broker_update = self._broker_gateway.cancel_order(requested.broker_order_id)
        except Exception as exc:  # pragma: no cover - safety path
            failed = self._repository.update_order_fields(client_order_id, status="FAILED")
            self._repository.create_audit_log(
                user_id=str(broker_account["user_id"]),
                resource_type="ORDER",
                resource_id=requested.client_order_id,
                action="ORDER_CANCEL_FAILED",
                before_state=requested.model_dump(mode="json"),
                after_state=failed.model_dump(mode="json"),
            )
            raise ApiException("ORDER_BROKER_CANCEL_FAILED", str(exc), status.HTTP_502_BAD_GATEWAY) from exc

        if broker_update is None:
            self._publish_order_event(requested.broker_account_id, requested)
            return requested
        updated = self._sync_broker_update(requested.client_order_id, broker_update)
        self._publish_order_event(updated.broker_account_id, updated)
        return updated

    def sync_broker_order(
        self,
        *,
        client_order_id: str | None = None,
        broker_order_id: str | None = None,
        status_value: str | None = None,
    ) -> OrderItem:
        order = self._resolve_order(client_order_id=client_order_id, broker_order_id=broker_order_id)
        broker_update = BrokerOrderUpdate(broker_order_id=broker_order_id or order.broker_order_id, status=status_value)
        return self._sync_broker_update(order.client_order_id, broker_update)

    def record_execution(
        self,
        *,
        client_order_id: str | None = None,
        broker_order_id: str | None = None,
        broker_execution_id: str,
        filled_quantity: Decimal,
        filled_price: Decimal,
        fee_amount: Decimal = Decimal("0"),
        executed_at: datetime | None = None,
    ) -> ExecutionItem:
        order = self._resolve_order(client_order_id=client_order_id, broker_order_id=broker_order_id)
        execution = self._repository.create_execution(
            {
                "id": str(uuid4()),
                "order_id": order.id,
                "broker_execution_id": broker_execution_id,
                "filled_quantity": filled_quantity,
                "filled_price": filled_price,
                "fee_amount": fee_amount,
                "executed_at": executed_at or datetime.now(timezone.utc),
            }
        )
        filled_total = self._repository.get_filled_quantity_total(order.id)
        next_status = "FILLED" if filled_total >= Decimal(str(order.quantity)) else "PARTIALLY_FILLED"
        updated = self._repository.update_order_fields(order.client_order_id, status=next_status)
        self._repository.create_audit_log(
            user_id=str(self._require_active_broker_account(order.broker_account_id)["user_id"]),
            resource_type="ORDER",
            resource_id=order.client_order_id,
            action="ORDER_EXECUTION_RECORDED",
            before_state=order.model_dump(mode="json"),
            after_state=updated.model_dump(mode="json"),
        )
        self._publish_order_event(updated.broker_account_id, updated, filled_quantity=float(filled_total))
        return execution

    def _sync_broker_update(
        self,
        client_order_id: str,
        broker_update: BrokerOrderUpdate,
        *,
        default_status: str | None = None,
    ) -> OrderItem:
        status_value = broker_update.status
        if status_value is None:
            status_value = default_status
        else:
            status_value = normalize_order_status(status_value)
        updated = self._repository.update_order_fields(
            client_order_id,
            status=status_value,
            broker_order_id=broker_update.broker_order_id,
        )
        broker_account = self._require_active_broker_account(updated.broker_account_id)
        self._repository.create_audit_log(
            user_id=str(broker_account["user_id"]),
            resource_type="ORDER",
            resource_id=updated.client_order_id,
            action="ORDER_STATUS_SYNCED",
            after_state=updated.model_dump(mode="json"),
        )
        return updated

    def _publish_order_event(self, broker_account_id: str, order: OrderItem, *, filled_quantity: float = 0.0) -> None:
        try:
            import asyncio

            loop = asyncio.get_running_loop()
            loop.create_task(
                realtime_hub.publish(
                    f"orders.status.{broker_account_id}",
                    "order.status_changed",
                    {
                        "client_order_id": order.client_order_id,
                        "status": order.status,
                        "filled_quantity": filled_quantity,
                        "remaining_quantity": max(float(order.quantity) - filled_quantity, 0),
                        "updated_at": order.updated_at.isoformat(),
                    },
                )
            )
        except RuntimeError:
            return

    def _resolve_order(self, *, client_order_id: str | None, broker_order_id: str | None) -> OrderItem:
        order = None
        if client_order_id is not None:
            order = self._repository.get_order_by_client_order_id(client_order_id)
        elif broker_order_id is not None:
            order = self._repository.get_order_by_broker_order_id(broker_order_id)
        if order is None:
            raise ApiException("ORDER_NOT_FOUND", "Order not found.", status.HTTP_404_NOT_FOUND)
        return order

    def _require_order(self, client_order_id: str) -> OrderItem:
        order = self._repository.get_order_by_client_order_id(client_order_id)
        if order is None:
            raise ApiException("ORDER_NOT_FOUND", "Order not found.", status.HTTP_404_NOT_FOUND)
        return order

    def _require_active_broker_account(self, broker_account_id: str) -> dict[str, object]:
        broker_account = self._repository.get_broker_account(broker_account_id)
        if broker_account is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        if str(broker_account["status"]).upper() != "ACTIVE":
            raise ApiException("BROKER_ACCOUNT_INACTIVE", "Broker account is not active.", status.HTTP_409_CONFLICT)
        return dict(broker_account)

    @staticmethod
    def _assert_idempotent_order(order: OrderItem, payload: PlaceOrderRequest) -> None:
        if (
            order.broker_account_id != payload.broker_account_id
            or order.symbol != payload.symbol
            or order.side != payload.side
            or order.order_type != payload.order_type
            or Decimal(str(order.quantity)) != payload.quantity
            or (Decimal(str(order.limit_price)) if order.limit_price is not None else None) != payload.limit_price
            or order.time_in_force != payload.time_in_force
        ):
            raise ApiException(
                "ORDER_IDEMPOTENCY_CONFLICT",
                "The idempotency key already belongs to a different order payload.",
                status.HTTP_409_CONFLICT,
            )

    @staticmethod
    def _generate_client_order_id(idempotency_key: str) -> str:
        return f"ord_{uuid4().hex[:12]}_{idempotency_key[-6:]}"
