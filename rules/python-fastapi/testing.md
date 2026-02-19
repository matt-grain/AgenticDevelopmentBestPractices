---
paths: "**/*.py"
---

# Tests as Executable Documentation

## Test Naming — Tests Are Specs
- Test names MUST read as behavior specifications in plain English.
- Use the pattern: `test_<action>_<scenario>_<expected_outcome>` or `test_<scenario>_<expected_behavior>`.
- A non-developer should be able to read test names and understand the business rules.

```python
# GOOD — these are readable specifications
def test_create_order_with_valid_items_returns_pending_status(): ...
def test_cancel_order_already_shipped_raises_invalid_transition(): ...
def test_user_login_with_expired_password_requires_reset(): ...
def test_apply_discount_exceeding_total_caps_at_zero(): ...

# BAD — meaningless names
def test_order_1(): ...
def test_create(): ...
def test_error_case(): ...
def test_it_works(): ...
```

## Test Structure — Arrange/Act/Assert
- Every test follows the AAA pattern with clear visual separation.
- Each section should be identifiable at a glance.

```python
async def test_checkout_with_insufficient_stock_raises_error(
    order_service: OrderService,
    product_factory: ProductFactory,
) -> None:
    # Arrange
    product = await product_factory.create(stock=0)
    request = CheckoutRequest(product_id=product.id, quantity=5)

    # Act & Assert
    with pytest.raises(InsufficientStockError):
        await order_service.checkout(request)
```

## What to Test and Where
- **Service layer** (unit tests): Business rules, validation logic, state transitions, edge cases. This is where most tests live.
- **Router layer** (integration tests): HTTP status codes, request/response serialization, auth, error response format. Use `httpx.AsyncClient`.
- **Repository layer**: Only test complex queries. Simple CRUD doesn't need dedicated tests if covered by integration tests.
- **FSMs**: Test every valid transition AND every invalid transition explicitly.
- **Schemas**: Test validation rules, especially custom validators and edge cases.

## Test Coverage Expectations
- Every public service method must have at least one happy-path test and one error-path test.
- Every FSM transition must be tested (both valid and invalid).
- Every custom Pydantic validator must be tested.
- Every error handler / exception mapping must be tested.

## Test Organization
- Mirror the `src/` structure: `tests/services/test_user_service.py`, `tests/routers/test_users.py`.
- Use `conftest.py` at each test directory level for shared fixtures.
- Use factories for test data creation — never hardcode dicts or raw values inline.

## Fixtures as Documentation
- Fixtures should have descriptive names that explain the scenario they set up.
- Prefer explicit fixture composition over deeply nested fixture chains.

```python
@pytest.fixture
async def active_user_with_expired_subscription(
    user_factory: UserFactory,
    subscription_factory: SubscriptionFactory,
) -> User:
    user = await user_factory.create(status=UserStatus.ACTIVE)
    await subscription_factory.create(user_id=user.id, expires_at=past_date())
    return user
```

## Tests You Must NOT Skip
- Boundary conditions (empty list, zero quantity, max length, None values).
- Unauthorized access attempts on protected endpoints.
- Invalid state transitions (the FSM rule ensures these exist).
- Concurrent modification scenarios for critical resources.
