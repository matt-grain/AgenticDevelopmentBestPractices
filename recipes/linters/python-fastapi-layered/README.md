# Python — FastAPI + Layered Architecture

Reference linters for projects using the layered pattern:

```
routers/        ← HTTP only. No SQLAlchemy. No business logic.
services/       ← Compose repositories. No Session. No transactions. No models import.
repositories/   ← Own ORM. Return Pydantic schemas / scalars, not bare ORM rows.
models/         ← SQLAlchemy 2.0 typed Mapped[T] = mapped_column(...).
enums/          ← StrEnum only. Single source of truth for closed sets.
workflows/      ← (optional) Compose services. Never reach past services.
main.py         ← Wires DI, registers exception handlers, exposes the app.
```

If your project doesn't have all these layers, take only the linters that match what you do have.

## Provenance

All files here are extracted verbatim from the **ShipBoard** project (`D:\OSS\AI-SDLC`), plus `check_datetime_patterns.py` from **museum-analysis** (`D:\OSS\museum-analysis`).

## Inventory

| File | Rule | Universal? |
|---|---|---|
| `_base.py` | Shared utilities (Violation, file iterator, runner) | ✅ |
| `check_file_length.py` | Files ≤ 200 lines, functions ≤ 30, classes ≤ 150 | ✅ Universal CLAUDE.md hard rule |
| `check_strenum_only.py` | All classes in `enums/` inherit from `StrEnum` | ✅ Universal CLAUDE.md hard rule |
| `check_no_httpexception_outside_handlers.py` | `HTTPException` only in `main.py` / `exception_handlers.py` / `routers/` | ✅ Layered FastAPI pattern |
| `check_no_sqlalchemy_in_routers.py` | Routers don't import `sqlalchemy` | ✅ Layered FastAPI pattern |
| `check_no_session_in_services.py` | Services don't take `Session`/`AsyncSession` parameters | ✅ Layered FastAPI pattern |
| `check_no_models_in_services.py` | Services don't import from `<package>.models` | ✅ Layered FastAPI pattern |
| `check_no_transaction_in_services.py` | Services don't call `.commit()` / `.flush()` / `.rollback()` | ✅ Layered FastAPI pattern |
| `check_no_repos_in_workflows.py` | Workflows compose services, not repositories | ✅ If you have a workflows layer |
| `check_models_use_mapped.py` | SQLAlchemy 2.0 typed `Mapped[T] = mapped_column(...)` | ✅ SQLAlchemy 2.0 best practice |
| `check_enum_discipline.py` | No raw string comparisons against known enum values | ⚠️ Template — supply your own `KNOWN_ENUM_VALUES` dict |
| `check_datetime_patterns.py` | No `datetime.utcnow()` / `datetime.now()` without tz / `.replace(tzinfo=None)` | ✅ Universal modern Python (3.12+) |

## Adapting

Every file references package name `shipboard` and layer path `src/shipboard/<layer>/`. Search-and-replace:

```bash
sed -i 's/shipboard/<your_package>/g' check_*.py
```

Then verify the `Path("src/<your_package>/<layer>")` references in each file's `main()` match your project's actual paths.

For `check_enum_discipline.py`, replace the `KNOWN_ENUM_VALUES` dict with your project's enum value → `EnumName.MEMBER` mapping.

## Pre-commit wiring

Drop a snippet like this into `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-no-session-in-services
      name: Services must not take Session parameters
      entry: python tools/pre_commit_checks/check_no_session_in_services.py
      language: python
      pass_filenames: false
      always_run: true
      types: [python]
    - id: check-no-models-in-services
      name: Services must not import models
      entry: python tools/pre_commit_checks/check_no_models_in_services.py
      language: python
      pass_filenames: false
      always_run: true
      types: [python]
    # ... one block per check ...
```

Most checks ignore `pass_filenames` and scan their layer directly — keeps the rule scoped to its target layer regardless of which file triggered the commit.
