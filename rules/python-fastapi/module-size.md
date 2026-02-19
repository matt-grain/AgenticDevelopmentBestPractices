---
paths: "**/*.py"
---

# Small, Focused Modules

## File Size Limits
- A Python file SHOULD NOT exceed ~200 lines of code (excluding imports and docstrings).
- If a file grows beyond 200 lines, it is a signal to split it by responsibility.
- A single function SHOULD NOT exceed ~30 lines. If it does, extract helper functions.
- A single class SHOULD NOT exceed ~150 lines. If it does, it likely violates SRP — split it.

## Function Discipline
- One function does ONE thing. If the function name requires "and" or "then", split it.
- Maximum function arguments: 5. Beyond that, group into a Pydantic model or dataclass.
- Cyclomatic complexity per function: keep below 10 (enforced via `radon`).
- Nesting depth: maximum 3 levels. Use early returns, guard clauses, and extraction to flatten.

## Module Cohesion
- Every module (file) should have a single, clear reason to exist.
- If you can't describe what a module does in one sentence without "and", split it.
- Utility/helper modules must be specific (`utils/hashing.py`, `utils/date_helpers.py`) — never a catch-all `utils.py`.
- A `utils.py` or `helpers.py` file that grows beyond 50 lines must be split into topic-specific files.

## When Splitting, Preserve Discoverability
- After splitting, re-export public symbols from the package `__init__.py` if needed for ergonomic imports.
- Prefer flat package structures — avoid nesting deeper than 3 levels (`src/app/services/user_service.py` is fine, `src/app/core/services/domain/user/service.py` is not).
