---
paths: "**/*.py"
---

# Python Typing & Pythonic Style

## Type Annotations — Mandatory
- ALL functions must have full type annotations for parameters and return types.
- ALL class attributes must be annotated.
- ALL module-level variables must be annotated when the type is not obvious.
- Use `from __future__ import annotations` for modern syntax (PEP 604 unions: `X | None`).
- Never use `Any` without an explanatory comment justifying why.
- Use `TypeAlias` for complex type expressions.
- Use `TypeVar` and `Generic` for generic classes/functions.
- Use `ParamSpec` for decorator typing.
- Use `Annotated[T, ...]` for metadata-rich types.
- Use `Final` for constants.
- Use `ClassVar` for class-level attributes.
- Use `Self` (Python 3.11+) for methods returning the instance type.
- Use `Never` for functions that always raise.
- Use `TypeGuard` for type narrowing functions.
- Use `overload` to express multiple signatures.

```python
from __future__ import annotations
from typing import Final, TypeAlias

MAX_RETRIES: Final[int] = 3
UserId: TypeAlias = int

async def get_user(user_id: UserId) -> UserOut | None: ...
```

## Pythonic Style

### Naming
- `snake_case` for functions, methods, variables, modules.
- `PascalCase` for classes and type aliases.
- `UPPER_SNAKE_CASE` for constants.
- Prefix private attributes/methods with `_` (single underscore).
- Never use `__` double underscore name mangling unless absolutely necessary.
- Boolean variables/parameters: use `is_`, `has_`, `can_`, `should_` prefixes.

### String Formatting
- Always use f-strings for interpolation (not `.format()` or `%`).
- Use f-strings in log messages only with lazy evaluation or use `logger.debug("msg %s", var)`.

### Collections & Comprehensions
- Prefer list/dict/set comprehensions over `map()`/`filter()` with lambdas.
- Use generator expressions for large sequences to save memory.
- Use `dict.get(key, default)` instead of `if key in dict: dict[key]`.
- Use `collections.defaultdict`, `Counter`, `deque` when appropriate.

### Context Managers
- Use `async with` for resource management (DB sessions, HTTP clients, file handles).
- Create custom context managers with `@asynccontextmanager` when managing lifecycle.

### Dataclasses & Pydantic
- Use `dataclasses.dataclass` for internal data containers without validation.
- Use Pydantic `BaseModel` for anything crossing a boundary (API, config, external data).
- Use `pydantic.Field(...)` for validation constraints.
- Use `model_validator` and `field_validator` for complex rules.
- Prefer `model_config = ConfigDict(frozen=True)` for immutable value objects.

### Iteration
- Use `enumerate()` instead of manual counter variables.
- Use `zip()` with `strict=True` for parallel iteration.
- Use `itertools` for complex iteration patterns.
- Never modify a collection while iterating over it.

### Comparison & Identity
- Use `is None` / `is not None` (never `== None`).
- Use `isinstance()` for type checks (never `type(x) == T`).
- Use truthiness checks for empty collections: `if not items:` instead of `if len(items) == 0:`.

### Imports
- Use absolute imports.
- Group imports: stdlib → third-party → local, separated by blank lines.
- Never use wildcard imports (`from module import *`).
- Import types in `TYPE_CHECKING` blocks to avoid circular imports.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models.user import User
```

### Error Handling
- Catch specific exceptions — never bare `except:` or `except Exception:` without re-raising.
- Use `raise ... from err` to preserve exception chains.
- Create domain-specific exception hierarchies.

```python
class DomainError(Exception): ...
class UserNotFoundError(DomainError):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")
```
