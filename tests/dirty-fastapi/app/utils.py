from __future__ import annotations

import secrets
from datetime import datetime

from app.enums.order_status import OrderStatus

_STATUS_ALIASES: dict[str, OrderStatus] = {
    "pending": OrderStatus.PENDING,
    "new": OrderStatus.PENDING,
    "created": OrderStatus.PENDING,
    "confirmed": OrderStatus.CONFIRMED,
    "accepted": OrderStatus.CONFIRMED,
    "shipped": OrderStatus.SHIPPED,
    "sent": OrderStatus.SHIPPED,
    "dispatched": OrderStatus.SHIPPED,
    "delivered": OrderStatus.DELIVERED,
    "completed": OrderStatus.DELIVERED,
    "done": OrderStatus.DELIVERED,
    "cancelled": OrderStatus.CANCELLED,
    "canceled": OrderStatus.CANCELLED,
    "void": OrderStatus.CANCELLED,
}


def generate_token(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def format_date(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_status(status: str) -> OrderStatus:
    return _STATUS_ALIASES.get(status.lower().strip(), OrderStatus.PENDING)


def calculate_totals(orders: list[dict[str, float]]) -> dict[str, float]:
    total = sum(o.get("total", 0) for o in orders)
    count = len(orders)
    avg = total / count if count > 0 else 0
    return {"total": total, "count": count, "average": avg}


def validate_email(email: str) -> bool:
    try:
        parts = email.split("@")
        return len(parts) == 2 and "." in parts[1]
    except (ValueError, IndexError):
        return False


def to_dict(obj: object) -> dict[str, object]:
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {}
