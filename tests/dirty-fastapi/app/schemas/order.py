from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.enums.order_status import OrderStatus


class OrderCreate(BaseModel):
    customer_name: str
    total: float = 0.0

    @field_validator("customer_name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Customer name required")
        return v.strip()

    @field_validator("total")
    @classmethod
    def total_must_be_non_negative(cls, v: float) -> float:
        return max(v, 0.0)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    status: OrderStatus
    total: float


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderStatsOut(BaseModel):
    total: int
    by_status: dict[str, int]
