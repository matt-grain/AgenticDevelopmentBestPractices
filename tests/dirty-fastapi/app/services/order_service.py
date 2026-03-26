from __future__ import annotations

from typing import TYPE_CHECKING

from app.enums.order_status import OrderStatus
from app.exceptions import InvalidTransitionError, OrderNotFoundError

if TYPE_CHECKING:
    from app.models.order import Order
    from app.repositories.order_repo import OrderRepository
    from app.schemas.order import OrderCreate

_VALID_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    def get_orders(self) -> list[Order]:
        return self._repo.get_all()

    def get_order(self, order_id: int) -> Order:
        order = self._repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    def create_order(self, payload: OrderCreate) -> Order:
        return self._repo.create(
            customer_name=payload.customer_name,
            total=payload.total,
            status=OrderStatus.PENDING,
        )

    def update_order_status(self, order_id: int, new_status: OrderStatus) -> Order:
        order = self._repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)

        current = OrderStatus(order.status)
        allowed = _VALID_TRANSITIONS.get(current, frozenset())
        if new_status not in allowed:
            raise InvalidTransitionError(current, new_status)

        result = self._repo.update_status(order_id, new_status)
        if result is None:
            raise OrderNotFoundError(order_id)
        return result

    def cancel_all_pending(self) -> list[int]:
        orders = self._repo.get_all()
        cancelled: list[int] = []
        for order in orders:
            if order.status == OrderStatus.PENDING:
                self._repo.update_status(order.id, OrderStatus.CANCELLED)
                cancelled.append(order.id)
        return cancelled

    def get_order_stats(self) -> dict[str, int | dict[str, int]]:
        orders = self._repo.get_all()
        by_status: dict[str, int] = {}
        for order in orders:
            by_status[order.status] = by_status.get(order.status, 0) + 1
        return {"total": len(orders), "by_status": by_status}
