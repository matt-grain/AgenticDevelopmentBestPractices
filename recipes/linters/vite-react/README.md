# Vite + React (TypeScript)

Reference linters for Vite SPA / internal-tool React projects. Inferred from `rules/vite-react/architecture.md` + `rules/vite-react/tooling.md` + the global frontend rules in `~/.claude/CLAUDE.md`.

## Why these three

The vite-react ruleset has many guidelines but only some translate into AST-mechanical checks. These three give the highest leverage per line of linter code:

| File | Rule(s) enforced | Source rule |
|---|---|---|
| `check_no_direct_env_access.ts` | Only `src/lib/env.ts` may access `import.meta.env` directly. Centralizes Zod validation, catches missing `VITE_` prefix typos, gives types to the rest of the app. | `tooling.md` (`Validate with Zod at startup`) + global `lib/env.ts` rule |
| `check_useeffect_has_why.ts` | Every `useEffect(...)` has a leading `// WHY: ...` comment. Forces every survivor to carry a written justification — most legitimate uses can be replaced by `useMemo`, a TanStack Query hook, or nothing. | global `Every useEffect has a // WHY: comment` |
| `check_no_useeffect_for_fetching.ts` | useEffect callbacks must not contain `fetch(...)`, `axios.<method>(...)`, or `api.<method>(...)`. Use TanStack Query instead. | global `Never useEffect for fetching — use useApiQuery or TanStack Query` |

## Why TypeScript compiler API directly (no extra deps)

The Python recipes use stdlib `ast`. The TypeScript equivalent is the TS compiler API, available from the `typescript` package every TS project already has. No `ts-morph`, no `@typescript-eslint/typescript-estree`, no ESLint custom rule plugin — same shape as the Python recipes: standalone single-file scripts, exit 0/1, runnable directly.

Run via:

```bash
pnpm tsx tools/pre_commit_checks/check_no_direct_env_access.ts
```

## Inventory

| File | Lines | Source |
|---|---|---|
| `_base.ts` | ~80 | New (TS port of `_base.py`) |
| `check_no_direct_env_access.ts` | ~70 | New |
| `check_useeffect_has_why.ts` | ~80 | New |
| `check_no_useeffect_for_fetching.ts` | ~110 | New |

## Adapting

These linters are written generically — they don't reference any specific project. Drop them in as-is for most Vite+React projects. Edit:

- **`API_CLIENT_RECEIVER_PATTERN`** in `check_no_useeffect_for_fetching.ts` to match your project's API client variable names (defaults: `axios`, `api`, `apiClient`, `httpClient`, `http`, `client`)
- **`ALLOWLIST_SUFFIXES`** in `check_no_direct_env_access.ts` if `lib/env.ts` lives at a different path

## Pre-commit wiring

TypeScript hooks use `language: system` and run via `pnpm tsx`:

```yaml
- repo: local
  hooks:
    - id: check-no-direct-env-access
      name: Direct import.meta.env access (only src/lib/env.ts may)
      entry: pnpm tsx tools/pre_commit_checks/check_no_direct_env_access.ts
      language: system
      pass_filenames: false
      always_run: true
      types_or: [ts, tsx]
    - id: check-useeffect-has-why
      name: Every useEffect has a leading // WHY: comment
      entry: pnpm tsx tools/pre_commit_checks/check_useeffect_has_why.ts
      language: system
      pass_filenames: false
      always_run: true
      types_or: [ts, tsx]
    - id: check-no-useeffect-for-fetching
      name: No fetch / API calls inside useEffect
      entry: pnpm tsx tools/pre_commit_checks/check_no_useeffect_for_fetching.ts
      language: system
      pass_filenames: false
      always_run: true
      types_or: [ts, tsx]
```

Make sure `tsx` is installed: `pnpm add -D tsx`.

## Other rules — why they're not here yet

Inferred but skipped — either too fuzzy or too project-specific:

| Rule | Why not |
|---|---|
| Components with 3+ `useState` extract a custom hook | Mechanical but high false-positive rate (some components legitimately need three independent local states); add when patterns confirm value |
| `components/ui/` primitives are stateless | Same — useState in a primitive is sometimes legitimate (Combobox, DropdownMenu state) |
| Routes are thin (no business logic) | "Business logic" not mechanically definable |
| Server state via TanStack Query, client state via Zustand | Hard to detect intent — Zustand stores fetching is sometimes legitimate during migration |
| Permissions enforced server-side | Cross-system, can't lint client alone |

These could be added later if a project audit produces recurring violations matching the pattern (the `/plan-fix` → `/scaffold-linter` promotion path).
