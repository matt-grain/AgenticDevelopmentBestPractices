# Intentional Violations — Scorecard

This file documents every intentional violation in the test project.
Use it to score `/check` detection rate and `/fix-check` fix rate.

## Violations (20 total)

| # | Category | File | Violation | Severity |
|---|----------|------|-----------|----------|
| 1 | Security | `app/main.py` | `allow_origins=["*"]` CORS wildcard | Critical |
| 2 | Security | `app/config.py` | Hardcoded `SECRET_KEY` | Critical |
| 3 | Security | `app/repositories/order_repo.py` | f-string SQL injection in `search()` | Critical |
| 4 | Security | `app/utils.py` | `random` module for token generation (should use `secrets`) | Warning |
| 5 | Architecture | `app/config.py` | Uses `os.getenv` instead of pydantic-settings `BaseSettings` | Warning |
| 6 | Architecture | `app/routers/orders.py` | No `response_model` or `status_code` on any endpoint | Critical |
| 7 | Architecture | `app/routers/orders.py` | Raw `Depends(get_db)` instead of `Annotated` type alias | Warning |
| 8 | Architecture | `app/routers/orders.py` | Business logic in `create_new_order` (validation, price clamping) | Critical |
| 9 | Architecture | `app/services/order_service.py` | Imports and receives `Session` directly | Critical |
| 10 | Architecture | `app/services/order_service.py` | Raises `HTTPException` (should be domain exception) | Critical |
| 11 | Architecture | `app/services/order_service.py` | Returns raw `dict` instead of typed schema | Critical |
| 12 | Architecture | `app/services/order_service.py` | Directly mutates ORM model + calls `db.commit()` | Critical |
| 13 | Architecture | `app/repositories/order_repo.py` | Uses `session.query()` instead of `select()` | Warning |
| 14 | Architecture | `app/repositories/order_repo.py` | Business logic in `create()` (price clamping) | Warning |
| 15 | State/Enum | `app/services/order_service.py` | Raw string status comparisons, no enum, no FSM | Critical |
| 16 | Typing | `app/services/order_service.py` | Missing return type annotations on all functions | Warning |
| 17 | Typing | `app/repositories/order_repo.py` | Missing type annotations on methods | Warning |
| 18 | Typing | `app/utils.py` | `Any` without justification, missing annotations | Warning |
| 19 | Schema | `app/schemas/order.py` | Single schema for all purposes (no Create/Update/Out) | Warning |
| 20 | Cognitive | `app/utils.py` | Catch-all utils file | Warning |
| 21 | Cognitive | `app/services/order_service.py` | `TODO` without tracker reference | Warning |
| 22 | Cognitive | `app/utils.py` | `FIXME` without tracker reference | Warning |
| 23 | Cognitive | `app/services/order_service.py` | `print()` in production code | Warning |
| 24 | Cognitive | `app/utils.py` | Bare `except:` in `validate_email` | Warning |
| 25 | Documentation | (project root) | No `ARCHITECTURE.md` | Warning |
| 26 | Documentation | (project root) | No `decisions.md` | Info |
| 27 | Testing | (project root) | No test files at all | Warning |

## Scoring

After running `/check`:
- **Detection rate** = violations detected / 27

After running `/fix-check` harness:
- **Fix rate** = violations fixed / violations detected
- **Iterations needed** = how many loops before clean (or bail)
- **Regressions** = new violations introduced by fixes
