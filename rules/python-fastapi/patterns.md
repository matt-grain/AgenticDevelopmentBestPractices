---
paths: "**/*.py"
---

# Design Patterns & Best Practices

## Repository Pattern
- Abstract data access behind a repository interface.
- Repository methods: `get`, `get_by_*`, `list`, `create`, `update`, `delete`.
- Accept and return domain models, not raw dicts.
- Keep query logic inside repositories — services never build SQL.

## Unit of Work Pattern
- Group related database operations into a single transaction.
- Use async context managers for transaction management.
- Commit at the workflow/service boundary, not inside repositories.

## DTO / Schema Pattern
- Never expose ORM models directly through the API.
- Transform at the service boundary: ORM model → Pydantic schema.
- Use separate schemas for creation, update, partial update, and response.

## Strategy Pattern
- When behavior varies by type/configuration, use strategy injection.
- Define a Protocol, implement concrete strategies, inject via `Depends()`.

## Factory Pattern
- Use factory functions/classes for complex object creation.
- Especially for creating test fixtures and seeding data.

## Value Objects
- Use frozen Pydantic models or `@dataclass(frozen=True)` for immutable value objects.
- Value objects: money, address, date range, coordinates, email, etc.
- Compare by value, not identity.

## Result Pattern for Error Handling
- For operations that can fail in expected ways, consider returning a result type instead of raising exceptions everywhere.

## Pagination
- Always paginate list endpoints — never return unbounded collections.
- Use cursor-based pagination for large datasets, offset-based for small ones.
- Return total count, page info, and items.

## Idempotency
- POST/PUT endpoints for critical operations should support idempotency keys.
- Design state transitions to be idempotent where possible.

## Logging
- Use structured logging (`structlog` or stdlib with JSON formatter).
- Log at service/workflow boundaries, not inside repositories.
- Include correlation IDs for request tracing.
- Never log sensitive data (passwords, tokens, PII).
- Use appropriate log levels: DEBUG for dev detail, INFO for business events, WARNING for recoverable issues, ERROR for failures.

## Configuration
- Use `pydantic-settings` `BaseSettings` with environment variable loading.
- Validate all configuration at startup — fail fast on missing/invalid config.
- Use separate settings classes per concern (DatabaseSettings, AuthSettings, etc.).
- Never hardcode secrets, URLs, or environment-specific values.

## Async Best Practices
- Use `async def` for all I/O-bound operations (DB, HTTP, file).
- Never use `time.sleep()` — use `asyncio.sleep()`.
- Use `asyncio.gather()` for concurrent independent operations.
- Use `asyncio.TaskGroup` (3.11+) for structured concurrency.
- Never call sync blocking functions in async context without `run_in_executor`.

## Security
- Hash passwords with `bcrypt` or `argon2` — never store plaintext.
- Use parameterized queries — never f-string SQL.
- Validate and sanitize all user input at the schema layer.
- Use short-lived JWTs for authentication.
- Apply rate limiting on public endpoints.
- Use CORS middleware with explicit allowed origins — never `allow_origins=["*"]` in production.
- Secrets in environment variables, never in code or config files.

## Database
- Use Alembic for migrations — never modify schema manually.
- Always use async SQLAlchemy (`AsyncSession`, `create_async_engine`).
- Add database indexes for columns used in WHERE, ORDER BY, and JOIN.
- Use `select()` (SQLAlchemy 2.0 style) — never legacy `Query` API.
