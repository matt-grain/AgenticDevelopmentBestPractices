# Architecture Review — dirty-fastapi

**Date:** 2026-03-25
**Project type:** Python/FastAPI

## Executive Summary

| Category | Conformance | Critical | Warnings | Info |
|----------|------------|----------|----------|------|
| Architecture & SoC | Low | 8 | 10 | 2 |
| Typing & Style | Low | 3 | 8 | 1 |
| State & Enums | Low | 7 | 2 | 0 |
| Testing | Low | 10 | 4 | 0 |
| Documentation & Debt | Low | 7 | 8 | 1 |

### Top Critical Findings
1. SQL injection via f-string in `repositories/order_repo.py:29`
2. Hardcoded `SECRET_KEY` in `config.py:5`
3. Service layer receives `Session`, raises `HTTPException`, calls `db.commit()` — violates every service rule
4. No enums, no FSM — raw string statuses scattered across 6 files
5. Zero test coverage — no test files exist

## Detailed Findings

### 1. Architecture & Separation of Concerns

| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
| 🔴 | Service functions accept `db: Session` as parameter | `services/order_service.py` | Services must never import/receive Session | Rewrite as class with `__init__(self, repo: OrderRepository)` |
| 🔴 | Service imports and raises `HTTPException` | `services/order_service.py:2,23,51` | Services raise domain exceptions only | Create `exceptions.py` with domain exceptions |
| 🔴 | Service calls `db.commit()` directly (3 locations) | `services/order_service.py:58,71` | Services never manage transactions | Move to repository layer |
| 🔴 | Service mutates ORM model directly (`order.status = x`) | `services/order_service.py:57,69` | Delegate to repository methods | Call `repo.update_status()` |
| 🔴 | Repository uses f-string SQL injection | `repositories/order_repo.py:29` | Parameterized queries only | Use `select().where().ilike()` |
| 🔴 | Repository uses legacy `session.query()` | `repositories/order_repo.py:12,15` | SQLAlchemy 2.0 `select()` required | Replace with `select(Order)` |
| 🔴 | No `response_model` or `status_code` on any endpoint | `routers/orders.py:16,22,28,41,47` | Mandatory on all endpoints | Add to every `@router.*` decorator |
| 🔴 | Business logic in router (validation, price clamping) | `routers/orders.py:31-35` | Routers handle HTTP only | Move to service/schema layer |
| 🟡 | Raw `Depends(get_db)` instead of Annotated type alias | `routers/orders.py:17,23,29,42,48` | Use `Annotated[T, Depends()]` | Create `DbSession` alias |
| 🟡 | Service returns raw `list[dict]` instead of typed schema | `services/order_service.py:15` | Return Pydantic schemas | Return `list[OrderOut]` |
| 🟡 | Service functions are module-level, not a class | `services/order_service.py` | Must use class with `__init__` DI | Rewrite as `OrderService` class |
| 🟡 | Module-level `order_repo = None` singleton | `services/order_service.py:7` | No singletons; use Depends() | Remove |
| 🟡 | Single `OrderSchema` for all purposes | `schemas/order.py` | Separate Create/Update/Out | Split schemas |
| 🟡 | Repository `create()` has business logic (price clamping) | `repositories/order_repo.py:19-20` | Repos: data access only | Move to service |
| 🟡 | `config.py` uses `os.getenv` not `BaseSettings` | `config.py` | Must use pydantic-settings | Rewrite with `BaseSettings` |
| 🟡 | Hardcoded `SECRET_KEY` in source | `config.py:5` | Secrets in env vars only | Load from env |
| 🟡 | `allow_origins=["*"]` CORS wildcard | `main.py:11` | Explicit origins required | Load from settings |
| 🟡 | No `dependencies.py` for DI wiring | project | DI in dedicated file | Create file |
| 🟡 | List endpoint returns unbounded list | `routers/orders.py:16` | Must paginate | Add limit/offset |
| 🔵 | Legacy `Column()` style instead of `Mapped[]` | `models/order.py` | SA 2.0 style preferred | Migrate when convenient |

### 2. Typing & Style

| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
| 🔴 | 13 functions missing return type annotations | `services/`, `repositories/`, `utils.py`, `routers/` | Full annotations required | Add `-> ReturnType` everywhere |
| 🔴 | 5 functions missing parameter type annotations | `utils.py`, `services/`, `repositories/` | Full annotations required | Annotate all params |
| 🔴 | `from __future__ import annotations` missing in all files | all 8 source files | Required for modern syntax | Add to every module |
| 🟡 | `Any` used without justification | `utils.py:54` | Must justify or avoid | Use `object` instead |
| 🟡 | Bare `except:` catches everything | `utils.py:50` | Catch specific exceptions | `except (ValueError, IndexError):` |
| 🟡 | `print()` in production code | `services/order_service.py:34` | Use structured logging | Remove or use logger |
| 🟡 | Service raises `HTTPException` (typing violation) | `services/order_service.py` | Domain exceptions only | Create domain exceptions |
| 🟡 | Service calls `db.commit()` (typing violation) | `services/order_service.py` | Wrong layer | Move to repo |
| 🟡 | Inline import inside function body | `routers/orders.py:34` | Top-level imports only | Move to top |
| 🟡 | `Optional` import redundant with `__future__` annotations | `schemas/order.py:2` | Use `X \| None` syntax | Remove Optional |
| 🟡 | Legacy `class Config` in Pydantic schema | `schemas/order.py:12` | Use `ConfigDict` | Update to v2 style |
| 🔵 | `datetime.utcnow` deprecated in 3.12+ | `models/order.py:16` | Use `datetime.now(UTC)` | Update |

### 3. State Management & Enums

| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
| 🔴 | No `enums/` directory — no enums exist | project | Enums mandatory for fixed sets | Create `enums/order_status.py` |
| 🔴 | No `state_machines/` directory — no FSM exists | project | FSM mandatory for stateful entities | Create `state_machines/order_fsm.py` |
| 🔴 | `Order.status` is raw `String` column with default `"pending"` | `models/order.py:14` | Must use enum type | Use `OrderStatus` enum |
| 🔴 | `OrderSchema.status` typed as `str` | `schemas/order.py:9` | Must use enum type | Use `OrderStatus` |
| 🔴 | Inline transition map with raw string keys | `services/order_service.py:40-46` | FSM in `state_machines/` | Extract to FSM module |
| 🔴 | `create_order()` validates against hardcoded string list | `services/order_service.py:30-31` | Use enum | Validate via enum |
| 🔴 | `cancel_all_pending()` uses raw string `"pending"`, `"cancelled"` | `services/order_service.py:68-69` | Use enum values | Replace with enum |
| 🟡 | `parse_status()` maps strings to strings — should use enum | `utils.py:20-34` | Enum eliminates need for this | Delete once enum exists |
| 🟡 | `change_status` endpoint accepts raw `str` parameter | `routers/orders.py:42` | Use `OrderStatus` type | Type the param as enum |

### 4. Testing Quality

| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
| 🔴 | No test files exist anywhere | project | Tests required | Create `tests/` directory |
| 🔴 | No `conftest.py` or fixtures | project | Shared fixtures required | Create with DB/client fixtures |
| 🔴 | `get_orders()` untested | `services/order_service.py` | Happy + error path tests | Add tests |
| 🔴 | `get_order()` untested — 404 path not covered | `services/order_service.py` | Happy + error path tests | Add tests |
| 🔴 | `create_order()` untested | `services/order_service.py` | Happy + error path tests | Add tests |
| 🔴 | `update_order_status()` untested — FSM logic uncovered | `services/order_service.py` | All FSM transitions tested | Add tests |
| 🔴 | `cancel_all_pending()` untested | `services/order_service.py` | Happy + error path tests | Add tests |
| 🔴 | `get_order_stats()` untested | `services/order_service.py` | Happy + error path tests | Add tests |
| 🔴 | No router integration tests | `routers/orders.py` | Integration tests required | Add with httpx |
| 🔴 | No schema validation tests | `schemas/order.py` | Validator tests required | Add tests |
| 🟡 | No test factories exist | project | Use factories, not hardcoded data | Create `OrderFactory` |
| 🟡 | No pytest config in pyproject.toml | `pyproject.toml` | pytest-asyncio required | Add config |
| 🟡 | FSM has ~23 transition paths — none tested | `services/order_service.py` | All transitions tested | Map all paths |
| 🟡 | `utils.py` functions untested | `utils.py` | Happy + error path tests | Add tests |

### 5. Documentation & Cognitive Debt

| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
| 🔴 | No `ARCHITECTURE.md` | project root | Mandatory | Create with all sections |
| 🔴 | No `decisions.md` | project root | ADR log mandatory | Create |
| 🔴 | CORS wildcard `allow_origins=["*"]` | `main.py:11` | Security: explicit origins | Load from settings |
| 🔴 | Hardcoded `SECRET_KEY` | `config.py:5` | Security: no secrets in code | Load from env |
| 🔴 | f-string SQL injection | `repositories/order_repo.py:29` | Security: parameterized only | Use ORM |
| 🔴 | No lockfile committed | project | Dependency hygiene | Run `uv lock` |
| 🔴 | `random` for token generation | `utils.py:1,8-10` | Use `secrets` module | Replace |
| 🟡 | `TODO` without tracker ref | `services/order_service.py:62` | Must have `(#issue)` | Fix or remove |
| 🟡 | `FIXME` without tracker ref | `utils.py:37` | Must have `(#issue)` | Fix or remove |
| 🟡 | `print()` in production | `services/order_service.py:34` | Use logging | Remove |
| 🟡 | Bare `except:` | `utils.py:50` | Specific exceptions | Fix |
| 🟡 | `Any` without justification | `utils.py:54` | Must justify | Use `object` |
| 🟡 | Catch-all `utils.py` (59 lines, mixed concerns) | `utils.py` | Topic-specific modules | Split |
| 🟡 | Missing type annotations on multiple functions | multiple files | Full annotations required | Add |
| 🟡 | Single schema for all purposes | `schemas/order.py` | Separate per purpose | Split |
| 🔵 | `datetime.utcnow` deprecated | `models/order.py:16` | Use `datetime.now(UTC)` | Update |

## Migration Plan

### Phase 0 — Quick Wins (mechanical, low risk)
- [ ] Add `from __future__ import annotations` to all source files
- [ ] Add return type annotations to all functions
- [ ] Add parameter type annotations to all functions
- [ ] Replace bare `except:` with specific exceptions
- [ ] Replace `Any` with `object` in `utils.py:to_dict`
- [ ] Remove `print()` from `services/order_service.py`
- [ ] Remove `TODO` and `FIXME` without tracker refs (or add refs)
- [ ] Replace `random` with `secrets` in `utils.py`
- [ ] Replace `class Config` with `ConfigDict` in schemas
- [ ] Replace `Optional` with `X | None` syntax

### Phase 1 — Structural Improvements (medium effort)
- [ ] Create `enums/order_status.py` with `OrderStatus(StrEnum)`
- [ ] Create `exceptions.py` with domain exception hierarchy
- [ ] Rewrite `config.py` with `BaseSettings` (removes hardcoded secret)
- [ ] Split `OrderSchema` into `OrderCreate`, `OrderOut`, `OrderStatusUpdate`, `OrderStatsOut`
- [ ] Replace `allow_origins=["*"]` with explicit list from settings
- [ ] Replace all raw string status comparisons with enum values
- [ ] Replace `session.query()` with `select()` in repository
- [ ] Fix f-string SQL injection with parameterized ORM query
- [ ] Remove business logic from repository `create()`
- [ ] Add `response_model` and `status_code` to all endpoints
- [ ] Replace raw `Depends()` with `Annotated` type aliases
- [ ] Remove business logic from router `create_new_order`

### Phase 2 — Architectural Changes (higher effort)
- [ ] Rewrite service as `OrderService` class with `__init__` DI
- [ ] Remove `Session` from service — inject repository instead
- [ ] Remove `db.commit()` from service — keep in repository
- [ ] Remove direct ORM mutation from service — delegate to repo
- [ ] Create `state_machines/order_fsm.py` with transition map
- [ ] Wire DI chain: router → service → repository → session
- [ ] Replace `HTTPException` in service with domain exceptions
- [ ] Create `dependencies.py` with Annotated DI aliases
- [ ] Update model `status` column to use enum default

### Phase 3 — Ongoing Discipline
- [ ] Create `ARCHITECTURE.md`
- [ ] Create `decisions.md`
- [ ] Add pytest + test infrastructure to pyproject.toml
- [ ] Create test directory structure
- [ ] Add service unit tests (happy + error paths)
- [ ] Add FSM transition tests (all valid + invalid)
- [ ] Add router integration tests
- [ ] Generate `uv.lock` lockfile
