# Linter Recipes — Reference Catalog

A curated catalog of mechanical linters (AST-based pre-commit checks) extracted from real projects following this harness's architectural discipline.

## What this is

These files are **reference examples, not drop-in templates.** When `/plan-release` or `/plan-fix` decides a project rule deserves mechanical enforcement, Claude reads this catalog for inspiration — AST patterns, naming conventions, error-message style — and writes a *new* linter using the project's specific concepts (package name, layer names, enum values).

Think of it like reading a similar project's tests for inspiration, not copying boilerplate.

## Why mechanical linters

The Anthropic harness paper's main insight: the evaluator should be objective. Today `/check` has two evaluators — tooling (mechanical, fast, reliable) and architecture (LLM judgment, slower, sometimes wrong). Mechanical linters convert architecture rules into deterministic checks. Result:

- `/fix-check` loops run faster (no LLM eval per iteration)
- Verdicts are objective — no "the model thinks this is OK" disagreements
- `ARCHITECTURE.md` rules become *executable*: each rule has a linter, each linter has a rule entry — they keep each other honest
- Onboarding wins: a new contributor runs `pre-commit run --all-files` and learns the project's discipline mechanically

## Catalog structure

```
recipes/linters/
  python-fastapi-layered/    # FastAPI + repository/service/router layered architecture
  python-clean-arch/         # Pure domain layer + Clean Architecture (multi-stack core, UI plug-ins)
  vite-react/                # Vite SPA + React + TanStack Query (TypeScript)
```

Each directory ships a `_base.{py|ts}` (Violation type + file iterator + runner) and one file per check. All checks return shell-exit-style `0` (clean) or `1` (violations) so they wire into `pre-commit` directly.

The TypeScript recipes use the TypeScript compiler API directly (no `ts-morph`, no ESLint custom-rule plugin) — same single-file shape as the Python ones, runnable via `pnpm tsx`.

## How to use during the harness flow

**During `/plan-release`** — when the plan introduces a new architectural rule:
1. Plan output includes a `## Mechanical Rules to Enforce` section listing candidate linters.
2. Human reviews during `/plan-validate`.
3. Confirmed rules get a `/scaffold-linter` step at the appropriate phase (some rules are linted from day one; enum discipline waits for the enum file to exist).

**During `/plan-fix`** — when a fix unit's Grep pattern recurs (≥2 findings or ≥2 files):
1. Plan output flags the pattern under `## Recurring Patterns Worth Promoting to Linters`.
2. Human confirms → `/scaffold-linter` runs alongside the fix, both files committed together.

The principle: **violations vote which rules deserve mechanical enforcement.**

## How to wire into pre-commit

After scaffolding `tools/pre_commit_checks/check_<rule>.{py|ts}`, append to `.pre-commit-config.yaml`:

**Python:**
```yaml
- repo: local
  hooks:
    - id: check-<rule>
      name: <one-line rule description>
      entry: python tools/pre_commit_checks/check_<rule>.py
      language: python
      pass_filenames: false
      always_run: true
      types: [python]
```

**TypeScript** (uses `language: system` because `tsx` isn't a pre-commit-managed env):
```yaml
- repo: local
  hooks:
    - id: check-<rule>
      name: <one-line rule description>
      entry: pnpm tsx tools/pre_commit_checks/check_<rule>.ts
      language: system
      pass_filenames: false
      always_run: true
      types_or: [ts, tsx]
```

Then `/check` runs `pre-commit run --from-ref <merge-base> --to-ref HEAD` — the same gate developers get on every `git commit`.

## Adapting catalog files

Every file references the source project's package name (`shipboard`, `pharma_derive`, etc.) and layer paths (`src/<package>/services`, `src/domain`, etc.). When using as inspiration:

1. Replace package names with your project's package
2. Adjust layer paths to match your project structure
3. For files like `check_enum_discipline.py`, supply your own `KNOWN_ENUM_VALUES` dict (the existing one is ShipBoard-specific by design — that's the whole point of the rule)
4. Adjust `FORBIDDEN_*` frozensets to match your stack

## Source projects

- **AI-SDLC / ShipBoard** (`D:\OSS\AI-SDLC`): mature FastAPI + SQLAlchemy 2.0 + StrEnum + repository/service/workflow/router layered architecture
- **museum-analysis** (`D:\OSS\museum-analysis`): async-first FastAPI with audit-grade datetime discipline
- **pharma-derive** (`D:\OSS\pharma-derive`): Clean Architecture with pure domain layer + Streamlit/FastAPI UI plug-ins
- **vite-react/** linters: inferred from `rules/vite-react/*.md` + global frontend rules — no real-project provenance yet (the patterns are textbook Vite+React+TanStack Query discipline). They'll grow real provenance as projects use them.

These are the curators' real projects — patterns survived contact with reality.
