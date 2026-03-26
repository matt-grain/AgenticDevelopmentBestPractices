from __future__ import annotations


class DomainError(Exception):
    pass


class OrderNotFoundError(DomainError):
    def __init__(self, order_id: int) -> None:
        self.order_id = order_id
        super().__init__(f"Order {order_id} not found")


class InvalidTransitionError(DomainError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current} to {target}")
