---
paths: "**/*.py"
---

# KISS, DRY, YAGNI Principles

## KISS — Keep It Simple, Stupid
- Write the simplest code that solves the problem.
- Prefer flat over nested — avoid deep `if/else` chains; use early returns (guard clauses).
- Avoid premature abstraction — don't create a base class until you have 2+ concrete implementations.
- Avoid clever code — readability beats cleverness.
- Prefer standard library and well-known patterns over custom clever solutions.
- One function does one thing. If it needs "and" in its name, split it.

```python
# GOOD — guard clauses, flat
async def activate_user(self, user_id: int) -> UserOut:
    user = await self._repo.get(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    if user.status == UserStatus.ACTIVE:
        raise UserAlreadyActiveError(user_id)
    user.status = UserStatus.ACTIVE
    return await self._repo.save(user)

# BAD — nested
async def activate_user(self, user_id: int) -> UserOut:
    user = await self._repo.get(user_id)
    if user is not None:
        if user.status != UserStatus.ACTIVE:
            user.status = UserStatus.ACTIVE
            return await self._repo.save(user)
        else:
            raise UserAlreadyActiveError(user_id)
    else:
        raise UserNotFoundError(user_id)
```

## DRY — Don't Repeat Yourself
- Extract shared logic into well-named functions or base classes only when the duplication is proven (Rule of Three).
- Share Pydantic validators via reusable field types or custom types.
- Use mixins for cross-cutting ORM fields (e.g., `TimestampMixin` with `created_at`, `updated_at`).
- DRY applies to knowledge, not just code — two identical-looking code blocks with different reasons to change should stay separate.

## YAGNI — You Aren't Gonna Need It
- Don't add code for hypothetical future requirements.
- Don't create abstractions "just in case."
- Don't add configuration for things that currently have only one value.
- Delete dead code — don't comment it out.
