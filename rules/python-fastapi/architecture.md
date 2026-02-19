---
paths: "**/*.py"
---

# FastAPI Architecture — Layered Separation of Concerns

## Project Structure

Always follow this canonical layout:

```
src/<project_name>/
├── main.py                  # App factory, lifespan, middleware registration
├── config.py                # Settings via pydantic-settings (BaseSettings)
├── dependencies.py          # Shared FastAPI Depends() factories
├── exceptions.py            # Custom exception classes + global handlers
├── routers/                 # Thin HTTP layer — one file per domain
│   ├── __init__.py
│   ├── users.py
│   └── orders.py
├── schemas/                 # Pydantic models (request/response DTOs)
│   ├── __init__.py
│   ├── users.py
│   └── orders.py
├── services/                # Business logic — domain rules live HERE
│   ├── __init__.py
│   ├── user_service.py
│   └── order_service.py
├── workflows/               # Multi-service orchestration & sagas
│   ├── __init__.py
│   └── checkout_workflow.py
├── repositories/            # Data access layer — DB queries only
│   ├── __init__.py
│   ├── user_repository.py
│   └── order_repository.py
├── models/                  # SQLAlchemy / ORM models
│   ├── __init__.py
│   └── user.py
├── enums/                   # All Enum definitions
│   ├── __init__.py
│   └── order_status.py
├── state_machines/          # FSM definitions for stateful entities
│   ├── __init__.py
│   └── order_fsm.py
└── utils/                   # Pure helper functions (no business logic)
    └── hashing.py
```

## Layer Responsibilities & Rules

### Routers (HTTP Layer)
- Handle HTTP concerns ONLY: parse request, call service, return response.
- Never contain business logic, DB queries, or direct model imports.
- Always declare explicit `response_model` on endpoints.
- Always declare explicit `status_code` on endpoints.
- Use dependency injection (`Depends()`) for services and auth.
- Group endpoints with `APIRouter(prefix=..., tags=[...])`.
- Use `Annotated[T, Depends(...)]` type aliases for clean signatures.

```python
# GOOD
@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserServiceDep,
) -> UserOut:
    return await service.create(payload)

# BAD — business logic leaking into router
@router.post("/users")
async def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(409, "exists")
    user = User(**payload.dict())
    db.add(user)
    ...
```

### Services (Business Logic Layer)
- Contain ALL business rules, validations, and domain decisions.
- Receive and return Pydantic schemas or domain primitives — never ORM models to callers.
- Call repositories for data access — never import `Session` or execute queries directly.
- Raise domain-specific exceptions (not `HTTPException`).
- A service should depend on repositories, not on other services. Use workflows for multi-service orchestration.

### Workflows (Orchestration Layer)
- Coordinate multiple services for complex business processes.
- Handle transaction boundaries and compensating actions (sagas).
- Implement retry logic and idempotency for distributed operations.
- A workflow may depend on multiple services but never on repositories directly.

```python
class CheckoutWorkflow:
    def __init__(
        self,
        order_service: OrderService,
        payment_service: PaymentService,
        notification_service: NotificationService,
    ) -> None:
        self._order_service = order_service
        self._payment_service = payment_service
        self._notification_service = notification_service

    async def execute(self, checkout: CheckoutRequest) -> OrderOut:
        order = await self._order_service.create(checkout.order)
        try:
            await self._payment_service.charge(order.id, checkout.payment)
        except PaymentFailedError:
            await self._order_service.cancel(order.id)
            raise
        await self._notification_service.send_confirmation(order)
        return order
```

### Repositories (Data Access Layer)
- Encapsulate ALL database queries — the only layer that imports ORM models and `Session`.
- Return ORM model instances to services (services convert to schemas).
- Never contain business logic or validation.
- One repository per aggregate root / domain entity.
- Use the repository pattern to enable unit testing with fakes/mocks.

### Schemas (Pydantic DTOs)
- Separate schemas per purpose: `Create`, `Update`, `Out`, `InDB`, `Patch`.
- Use `model_config = ConfigDict(from_attributes=True)` for ORM integration.
- Never reuse a single schema for both input and output.
- Validate at the boundary — use `Field(...)` constraints, custom validators.

### Models (ORM Layer)
- Define database structure only — no methods with business logic.
- Use `Mapped[]` and `mapped_column()` (SQLAlchemy 2.0 style).

## Dependency Injection

- Register all dependencies as `Depends()` callables.
- Create `Annotated` type aliases for common dependencies.
- Chain dependencies: router → service → repository → session.

```python
# dependencies.py
from typing import Annotated
from fastapi import Depends

async def get_db() -> AsyncGenerator[AsyncSession, None]: ...
async def get_user_repo(db: DBDep) -> UserRepository: ...
async def get_user_service(repo: UserRepoDep) -> UserService: ...

DBDep = Annotated[AsyncSession, Depends(get_db)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
```
