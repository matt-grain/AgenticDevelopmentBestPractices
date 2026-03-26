from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

from app.enums.order_status import OrderStatus

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_name = Column(String, nullable=False)
    status = Column(String, default=OrderStatus.PENDING)
    total = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
