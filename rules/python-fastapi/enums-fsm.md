---
paths: "**/*.py"
---

# Enums and Finite State Machines

## Enums — Mandatory for Fixed Sets of Values
- ALWAYS use `enum.Enum` (or `StrEnum`, `IntEnum`) for any value from a fixed, known set.
- Never use raw strings or magic integers for statuses, roles, types, categories, modes, etc.
- Store enum values (not names) in the database.
- Use `StrEnum` for values that need JSON serialization without custom logic.
- Enums must be defined in the `enums/` directory.

```python
from enum import StrEnum, unique

@unique
class OrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
```

### When to Use Enums
- HTTP method types, user roles, permissions, feature flags.
- Any column that stores a value from a predefined list.
- Configuration options with discrete values.
- Event types, action types, notification channels.
- If you write `if status == "active"` with a string literal — it should be an enum.

## Finite State Machines — Mandatory for Stateful Entities

ANY entity with a status/state field that transitions between values MUST define a formal FSM.

### Rules
- Define allowed transitions explicitly — never allow arbitrary state changes.
- Validate transitions BEFORE applying — raise on illegal transitions.
- Optionally define side effects (callbacks) for transitions.
- FSMs live in `state_machines/` directory.
- The service layer calls the FSM to validate before mutating state.

```python
from __future__ import annotations
from typing import Final
from .enums.order_status import OrderStatus

# Transition map: current_state -> set of allowed next states
ORDER_TRANSITIONS: Final[dict[OrderStatus, frozenset[OrderStatus]]] = {
    OrderStatus.DRAFT: frozenset({OrderStatus.PENDING, OrderStatus.CANCELLED}),
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset({OrderStatus.REFUNDED}),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.REFUNDED: frozenset(),
}

class InvalidTransitionError(DomainError):
    def __init__(self, entity_id: int, current: OrderStatus, target: OrderStatus) -> None:
        super().__init__(
            f"Invalid transition for order {entity_id}: {current.value} -> {target.value}"
        )

def transition_order(order: Order, target: OrderStatus) -> None:
    allowed = ORDER_TRANSITIONS.get(order.status, frozenset())
    if target not in allowed:
        raise InvalidTransitionError(order.id, order.status, target)
    order.status = target
```

### When to Use FSMs
- Order lifecycle (draft → pending → confirmed → shipped → delivered).
- User account states (pending_verification → active → suspended → deleted).
- Payment states (initiated → processing → completed → failed → refunded).
- Task/ticket systems (open → in_progress → review → done → closed).
- Subscription states (trial → active → past_due → cancelled).
- Any entity where not all state changes are valid from every state.
