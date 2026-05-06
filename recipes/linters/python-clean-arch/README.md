# Python — Clean Architecture (pure domain core)

Reference linters for projects using Clean Architecture: a framework-agnostic domain core, with infrastructure and UI as plug-ins around it.

```
domain/         ← Pure business logic. Stdlib + pydantic + numerics only. No framework.
agents/         ← Domain-driven coordinators. No UI imports.
verification/   ← Validation layer. No UI imports.
audit/          ← Audit trail. No UI imports.
engine/         ← Orchestration. No UI imports. Repos via DI only.
persistence/    ← Repos live here. Can import SQLAlchemy / etc.
ui/             ← Streamlit / FastAPI / etc. The only place UI frameworks live.
```

The whole point: you can **rip out the UI layer** and the domain still runs.

## Provenance

Files extracted from **pharma-derive** (`D:\OSS\pharma-derive`), with `check_no_sync_http.py` from **museum-analysis** (`D:\OSS\museum-analysis`).

## Inventory

| File | Rule | Universal? |
|---|---|---|
| `_base.py` | Shared utilities | ✅ |
| `check_domain_purity.py` | Domain layer imports only stdlib + permitted scientific libs (pydantic / pandas / numpy / networkx) | ✅ Universal Clean Arch — adjust the allowlist |
| `check_domain_no_ui_exceptions.py` | Domain / agents / verification / audit don't raise `HTTPException` or import Streamlit | ✅ Universal |
| `check_repo_direct_instantiation.py` | Repositories injected via constructor DI, never instantiated in domain/engine/etc. | ✅ Universal DI discipline |
| `check_no_sync_http.py` | No `requests` / `urllib` / `urllib3` / `http.client` in `src/` — async only | ✅ For async-first projects |

## Adapting

The pharma-derive originals use these layer names: `domain`, `agents`, `verification`, `audit`, `engine`, `persistence`. If your Clean Architecture uses different names (e.g. `core` / `application` / `infrastructure` / `interface`), edit each file's:

- `FORBIDDEN_LAYERS` tuple (where the rule applies)
- `Path("src/...")` references in `main()` (where to scan)
- Allowlist names in error messages

`check_domain_purity.py`'s `FORBIDDEN_MODULES` set is the most opinionated piece — it bans `pydantic_ai`, `statemachine`, `loguru`, `sqlalchemy`, `streamlit`, `fastapi`, `httpx`. Adjust to match your stack: keep what you actually want banned, drop what you legitimately use in domain.

## Pre-commit wiring

```yaml
- repo: local
  hooks:
    - id: check-domain-purity
      name: Domain layer — no framework imports
      entry: python tools/pre_commit_checks/check_domain_purity.py
      language: python
      pass_filenames: false
      always_run: true
      types: [python]
    - id: check-domain-no-ui-exceptions
      name: Domain / agents / verification / audit — no UI exceptions
      entry: python tools/pre_commit_checks/check_domain_no_ui_exceptions.py
      language: python
      pass_filenames: false
      always_run: true
      types: [python]
    # ... one block per check ...
```

## Related: layered FastAPI

If your project is layered FastAPI rather than Clean Architecture (no pure domain, ORM models live in a `models/` layer), use `python-fastapi-layered/` instead. They overlap in spirit but the layer names and rules differ.
