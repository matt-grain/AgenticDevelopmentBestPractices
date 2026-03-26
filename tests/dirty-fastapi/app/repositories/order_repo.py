from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums.order_status import OrderStatus
from app.models.order import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Order]:
        return list(self.db.scalars(select(Order)).all())

    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.scalars(select(Order).where(Order.id == order_id)).first()

    def create(self, customer_name: str, total: float, status: OrderStatus) -> Order:
        order = Order(customer_name=customer_name, total=total, status=status)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def search(self, name: str) -> list[Order]:
        stmt = select(Order).where(Order.customer_name.ilike(f"%{name}%"))
        return list(self.db.scalars(stmt).all())

    def update_status(self, order_id: int, new_status: OrderStatus) -> Order | None:
        order = self.get_by_id(order_id)
        if order:
            order.status = new_status
            self.db.commit()
        return order
