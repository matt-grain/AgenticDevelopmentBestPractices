# {PROJECT_NAME}

## Quick Reference

- **Stack:** {e.g., FastAPI + SQLAlchemy | Next.js 14 App Router | FastAPI backend + Next.js frontend}
- **Run dev:** {e.g., `cd backend && uv run uvicorn main:app --reload`}
- **Run tests:** {e.g., `uv run pytest` / `pnpm vitest run`}
- **Lint:** {e.g., `uv run ruff check . && uv run pyright .` / `pnpm tsc --noEmit && pnpm eslint .`}
- **Docs:** `ARCHITECTURE.md` (structure + patterns), `decisions.md` (ADRs)

## Hard Rules

These are non-negotiable. Violating any of these is a blocking issue.

1. **Read before writing.** Before modifying a file, read it and its neighbors in the same layer. Before adding a pattern, check if one exists. No exceptions.
2. **No file over 200 lines.** If a file approaches 200 lines, split it before adding more. This applies to extracted files too.
3. **No function over 30 lines.** Extract helpers or simplify.
4. **No `any`/`Any` without a comment justifying why.** Use `unknown` with narrowing or proper generics.
5. **No suppression without justification.** Every `# type: ignore`, `@ts-ignore`, `eslint-disable` needs a bracketed code + reason.
6. **Every public method has full type annotations.** Parameters AND return type. No implicit `Any`.
7. **Tests prove it works.** No feature is done without at least 1 happy-path + 1 error-path test per public method.
8. **Tooling must pass.** Run lint + type check + tests before considering any task complete. Fix errors, don't ignore them.

## Project-Specific Constraints

{Delete sections that don't apply. Add project-specific constraints.}

### Backend (Python/FastAPI)
- Services never import from `models/` — only repositories touch ORM.
- Services never manage transactions — no `commit()`, `flush()`, `rollback()`.
- Services accept dependencies via `__init__` — no module-level singletons.
- Every status/role/type is a StrEnum in `enums/` — no raw strings.
- Every stateful entity has an FSM in `state_machines/` — no ad-hoc transitions.
- Repository methods accept typed schemas or explicit params — never `data: dict`.

### Frontend (React/Next.js)
- Never `process.env` directly — import from `lib/env.ts`.
- Never `useState` for server data — use data-fetching hooks.
- Never `useEffect` for fetching — use `useApiQuery` or TanStack Query.
- Every `useEffect` has a `// WHY:` comment.
- Components with 3+ `useState` must extract a custom hook.
- Filter/sort/pagination state lives in URL params, not component state.
- Every route segment with data fetching has an `error.tsx`.

### Flutter
- Domain layer is pure Dart — no Flutter imports, no data layer imports.
- All domain models use `@freezed` — no mutable entity classes.
- All enums use enhanced Dart 3.0+ syntax — no raw strings.
- State via Riverpod or Bloc only — no `setState` for server data, no `ChangeNotifier`.

## Quality Workflow

Before merging a feature branch:
```
/check                    # Fast, read-only gate on your diff
```

Before a release:
```
/review-architecture      # Full audit → REVIEW.md
/plan-fix                 # Detailed fix plan → FIX_PLAN.md (review this!)
/fix-check               # Execute the plan
/validate-review          # Independent verification
/heal-review              # Fix remaining gaps (if any)
```

## Decisions Log

{Link to or summarize key decisions that affect how agents should write code.}

- {e.g., "Sync SQLAlchemy by design — not migrating to async (see decisions.md #3)"}
- {e.g., "UoW pattern for transactions — commit at router level (see decisions.md #5)"}
- {e.g., "No TanStack Query yet — using custom useApiQuery (see decisions.md #7)"}
