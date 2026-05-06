# Best Practices for Claude Code Agentic Workflows

This document describes a complete development workflow using Claude Code commands, rules, and agents for building software with architectural discipline.

---

## Quick Reference

### Two Workflows

| Workflow | Purpose | Commands |
|----------|---------|----------|
| **Development** | Build features from issues | `/init-component` → `/plan-release` → `/plan-validate` → `/implement-phase` → `/check` → `/fix-check` |
| **Release Gate** | Audit & fix before release | `/review-architecture` → `/plan-fix` → `/plan-fix-validate` → (per phase: `/implement-fix-phase N` → `/check` → PR → merge) → `/validate-review` → `/heal-review` |

### All Commands

| Command | Purpose | Input | Output |
|---------|---------|-------|--------|
| `/init-component` | Scaffold a new component (Discovery stage entry point) | Component name + optional `--pm`, `--ai-dev`, `--repo-owner`, `--repo-name` | `.shipboard.yml`, scaffolded `docs/`, `CLAUDE.md`, `ARCHITECTURE.md`, first git commit, MCP `register_component` event |
| `/scaffold-linter` | Mechanize an architectural rule as a deterministic pre-commit linter | Rule ID + recipe (e.g. `--recipe python-fastapi-layered/check_no_session_in_services.py`) | New `tools/pre_commit_checks/check_<rule>.{py\|ts}` + `.pre-commit-config.yaml` entry |
| `/plan-status` | Dashboard: where are we? | — | Inline report |
| `/plan-release` | Design features, split into phases | Issue refs or free-text | `IMPLEMENTATION_PLAN.md` + per-phase files |
| `/plan-validate` | Verify plan detail is Sonnet-ready | Plan files | Inline verdict |
| `/implement-phase N` | Execute a specific phase | Phase number | Code + `IMPLEMENTATION_STATUS.md` |
| `/check` | Pre-merge architectural gate (read-only) | — | Inline verdict |
| `/fix-check` | Fix violations found by `/check` | Conversation with `/check` output | Inline report |
| `/review-architecture` | Full codebase audit | — | `REVIEW.md` |
| `/plan-fix` | Plan fixes with HOW TO FIX. Splits into per-phase files when large. | `REVIEW.md` | `FIX_PLAN.md` (+ `FIX_PLAN_PHASE_N.md` if multi-phase) |
| `/plan-fix-validate` | Validate the fix plan is Sonnet-ready. Re-runs every violation grep to catch stale patterns. | `FIX_PLAN.md` (+ per-phase files) | Validation report (in conversation) |
| `/implement-fix-phase N` | Ship one themed phase as a focused PR (refactor analog of `/implement-phase`) | `FIX_PLAN_PHASE_N.md` | `FIX_STATUS.md`, branch `fix-phase-N-<theme>` |
| `/validate-review` | Independent verification | Review artifacts | `REVIEW_VALIDATION.md` |
| `/heal-review` | Fix remaining gaps | `REVIEW_VALIDATION.md` | Updated artifacts |

### Lifecycle reporting (Step 0.5)

Every harness command above (except `/plan-status`, which is read-only) reports a lifecycle event to ShipBoard at start, if `.shipboard.yml` is present in the repo root and `.mcp.json` registers a reachable `shipboard` server. This makes the dashboard's `/lifecycle` Kanban update live as the harness runs:

- `/plan-release`, `/plan-validate`, `/plan-fix`, `/plan-fix-validate`, `/review-architecture` → stage `intent` (sub-state varies)
- `/implement-phase N`, `/implement-fix-phase N`, `/scaffold-linter` → stage `generate`, sub-state `phase-N` / `fix-phase-N` / `scaffold-linter`
- `/check`, `/validate-review`, `/fix-check`, `/heal-review` → stage `verify_iterate` (sub-state `verify` / `verify-audit` / `iterate` / `heal`)

Reporting is **best-effort** — when MCP is unreachable the event is queued to `.shipboard/pending_events.log` and the command continues normally. Reporting NEVER blocks command execution.

If `.shipboard.yml` is missing (the user hasn't run `/init-component` yet, or this isn't a tracked component), Step 0.5 is silently skipped. Every command still works without ShipBoard.

---

## Development Workflow

Build features from GitHub Issues or Jira tickets with phased implementation and verification.

### The Flow

```
/init-component QuotingAgent --pm "Matt" --ai-dev "Anima"   # Discovery scaffolding (NEW)
        │
        ▼
.shipboard.yml + docs/REQUIREMENTS.md + first commit + register_component MCP event
        │
        ├─ PM fills in docs/REQUIREMENTS.md
        │
        ▼
/plan-release GH#301, GH#404
        │
        ▼
IMPLEMENTATION_PLAN.md + per-phase files (detailed specs)
        │
        ├─ User reviews / edits plan
        │
        ▼
/plan-validate (verify specs are Sonnet-ready)
        │
        ├─ ✅ READY → proceed
        ├─ ⚠️ NEEDS REFINEMENT → fix plan → re-validate
        │
        ▼
        ├─ /implement-phase 1 (creates phase-1-* branch) → /check ──┬─→ gh pr create → CI → merge
        ├─ /implement-phase 2 (creates phase-2-* branch) → /check   │
        └─ /implement-phase 3 (creates phase-3-* branch) → /check   │
                                                                     │
                                                          violations found?
                                                                     │
                                                                     ▼
                                                  /fix-check → re-run /check → gh pr create → merge

        (Solo prototypes can stay on main; /check then proposes a direct
        commit instead of a PR. See USERGUIDE for the formal-vs-fast trade.)
```

### `/plan-release` — Design & Phase Splitting

Takes issue references, fetches details, creates a phased implementation plan:

```
/plan-release GH#301, GH#404           # GitHub issues
/plan-release JIRA-205, GH#301         # Mixed sources
/plan-release "Add invoice export"     # Free-text
```

What it does:
1. Fetches issue details via `gh issue view`
2. Reads `ARCHITECTURE.md` for project context
3. Analyzes scope (layers touched, files needed)
4. Splits into ordered phases with dependencies
5. Writes `IMPLEMENTATION_PLAN.md`

**Output**: For multi-phase plans, produces separate files:
- `IMPLEMENTATION_PLAN.md` — overview with phases, dependencies, timeline
- `IMPLEMENTATION_PLAN_PHASE_1.md` — detailed per-file specs for Phase 1
- `IMPLEMENTATION_PLAN_PHASE_2.md` — detailed per-file specs for Phase 2
- etc.

Each per-file spec includes: Purpose, Fields/Methods with types, Constraints, Reference file. This level of detail is critical — Sonnet subagents follow specs literally, so vague specs produce vague code.

Review and edit before implementing. Run `/plan-validate` after editing.

### `/plan-validate` — Verify Plan Quality

Independent 3rd-party validation that the plan is detailed enough for Sonnet subagents:

```
/plan-validate                         # Reads IMPLEMENTATION_PLAN*.md files
```

What it checks:
- **File spec completeness**: Does every file have Purpose, Fields/Methods, Constraints, Reference?
- **Architecture rules**: Do specs follow layer rules (no raw strings for status, no dicts for returns, etc.)?
- **Cross-file consistency**: Enum coverage, FSM coverage, test coverage, DI registration
- **Phase structure**: Per-phase files exist, self-contained, under 300 lines, no cross-phase leaks
- **Sonnet readability test**: "Would Sonnet produce correct code from this spec alone?"

**Verdict**: READY TO IMPLEMENT / NEEDS REFINEMENT / NOT READY

**When to run**: After `/plan-release` and after any manual edits to the plan files. Fast (2-5 minutes), read-only, no code changes.

### `/implement-phase N` — Execute a Phase

Implements a specific phase from the plan:

```
/implement-phase 1                     # Implement Phase 1
/implement-phase 2                     # After Phase 1 is done
```

What it does:
1. Reads `IMPLEMENTATION_PLAN.md`, parses target phase
2. Checks dependencies (earlier phases complete?)
3. Dispatches correct subagent per task (flutter, python-fastapi, etc.)
4. Runs tooling gate (type check, lint, tests)
5. Verifies against plan (all files created? tests exist?)
6. Updates `IMPLEMENTATION_PLAN.md` with completion status
7. Writes/updates `IMPLEMENTATION_STATUS.md` with:
   - What was done ✅
   - What's partial ⚠️
   - What's missing ❌
   - Next phase preview

### `/check` — Pre-Merge Gate

Fast, read-only architectural check on changed files. Run before every merge:

```
/check                                 # Scans git diff against base branch
```

What it checks:
- Tooling (pyright, ruff, eslint, tsc, dart analyze)
- Tests pass
- Architectural violations in changed files
- Missing companions (new endpoint without test, new entity without FSM)
- Plan alignment (if `IMPLEMENTATION_PLAN.md` exists)

**Verdict**: READY TO MERGE / REVIEW BEFORE MERGING / DO NOT MERGE

**Safe to run anytime** — completely read-only, never modifies files.

### `/fix-check` — Self-Correcting Fix Harness

A self-correcting harness that fixes violations from `/check` and **loops until clean or bailed out**. Implements a Generator/Evaluator separation pattern inspired by [Anthropic's harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps) and [Karpathy's autoresearch](https://github.com/karpathy/autoresearch).

```
/fix-check                             # Runs autonomously — no manual re-runs needed
```

What it does:
1. **Runs the evaluator** — executes `/check` logic internally (tooling + architecture rules)
2. **Groups** violations into fix units (🔴 Critical first, 🟡 Warnings in later iterations)
3. **Routes** to correct subagent by file type (.dart→flutter, .py→python-fastapi, .tsx→react-nextjs)
4. **Phase 0**: Runs tooling auto-fixes directly (ruff --fix, eslint --fix, dart fix)
5. **Phase 1+**: Dispatches subagents with concrete HOW TO FIX instructions
6. **Re-evaluates** — re-runs the full `/check` logic on modified files (evaluator ≠ generator)
7. **Loops** — if violations remain and count decreased, rebuilds manifest and fixes again
8. **Reverts on regression** — if a fix iteration doesn't improve, `git checkout` the modified files
9. **Reports** after max 3 iterations with per-violation history across iterations

**Key design principles:**
- **Evaluator is the oracle**: `/check` rules + tooling output are objective truth. The fixer never judges its own work.
- **Regression = revert**: If an iteration doesn't reduce violations, undo it (Karpathy pattern).
- **No human in the loop during execution**: The harness runs autonomously up to MAX_ITERATIONS. The human sees the final report.
- **Iteration budget is scarce**: Fix 🔴 Critical first. Only spend iterations on 🟡 Warnings after critical issues resolve.

**Typical flow:**
```
/check                    → "❌ DO NOT MERGE — 5 critical violations"
/fix-check                → evaluates → fixes → re-evaluates → loops → clean in 2 iterations
                          → "✅ ALL CLEAR — 5 violations resolved in 2 iterations"
```

---

## Release Gate Workflow

Audit the entire codebase against architectural rules, fix all violations, verify completeness. Run at release milestones.

### The Flow

```
/review-architecture
        │
        ▼
    REVIEW.md (findings, migration plan)
        │
        ▼
    /plan-fix
        │
        ├─ Small audit (<30 fix units, 1–2 themes)
        │   → FIX_PLAN.md (single-phase, run /fix-check once)
        │
        └─ Large audit (≥30 fix units OR ≥3 themes)
            → FIX_PLAN.md (overview)
            + FIX_PLAN_PHASE_1.md (e.g. Security findings)
            + FIX_PLAN_PHASE_2.md (e.g. Layer-boundary violations)
            + FIX_PLAN_PHASE_N.md (...)
                │
                ├─ User reviews & edits
                │
                ▼
            For each phase (in dependency order):
                /implement-fix-phase N (creates fix-phase-N-<theme> branch)
                        │
                        ▼
                    /check
                        │
                        ▼
                    gh pr create → CI → reviewer → merge
                        │
                        ▼
                    /implement-fix-phase N+1 ...
                │
                ▼
        /validate-review
                │
                ├─ ALL CLEAR? → done
                │
                ▼ (if gaps)
        /heal-review → /validate-review → done or manual intervention
```

The fix loop now mirrors the feature loop: one themed phase = one focused PR, just like one feature phase = one focused PR. Reviewers see the same shape whether they're shipping new features or paying down architectural debt.

### `/review-architecture` — Full Audit

5 parallel agents scan the entire codebase against your rules:

```
/review-architecture                   # Takes 10+ minutes
```

**Output**: `REVIEW.md` with:
- Executive summary with conformance scores
- Detailed findings (🔴 Critical, 🟡 Warning, 🔵 Note)
- Migration plan with phased checklist

### `/plan-fix` — Plan Before Fixing

Reads findings, expands to complete file lists, writes concrete fix instructions:

```
/plan-fix                              # Reads REVIEW.md, writes FIX_PLAN.md
```

What it does:
1. For each finding, expands examples to full file list (via Grep/Glob)
2. Inspects 2-3 affected files to understand the violation
3. Finds reference examples of the correct pattern
4. Writes concrete HOW TO FIX instructions per fix unit
5. Groups fix units by **theme** (Security findings → Layer-boundary violations → Typing discipline → File-size violations → FSM/enum discipline → Test gaps → Dead code → CI gates), ordered by **severity** (🔴 → 🟡 → 🔵)
6. Enforces batch size (max 8 files per unit)
7. **Splits into per-phase files** (`FIX_PLAN_PHASE_N.md`) when ≥30 fix units OR ≥3 themes — each phase ships as one focused PR, mirroring how `/plan-release` splits feature work into per-phase plan files

**Output**:
- Small audits → single `FIX_PLAN.md` with all fix units inline (run with `/fix-check`)
- Large audits → `FIX_PLAN.md` overview + `FIX_PLAN_PHASE_N.md` per phase (run each with `/implement-fix-phase N`)

Review and edit before executing.

**Why plan first?** Subagents produce dramatically better results when given precise instructions ("Replace `data: dict` with `data: ItemCreate` on line 67") versus vague directives ("fix the types"). Planning also catches scope issues before code changes.

### `/validate-review` — Independent Verification

A separate verification pass that doesn't trust the fixer:

```
/validate-review                       # Independent check
```

What it does:
1. Re-scans entire codebase for each violation pattern
2. Runs tooling in report-only mode (no --fix)
3. Builds test coverage matrix
4. Checks for deferred items from `FIX_PLAN.md` (excluded from %)

**Output**: `REVIEW_VALIDATION.md` with completion percentage and remaining gaps.

**Verdict**: ALL CLEAR / GAPS FOUND / SIGNIFICANT GAPS

### `/heal-review` — Fix Remaining Gaps

Targeted fixes for gaps found by validation, with cross-gap interference detection:

```
/heal-review                           # Shows gaps, lets you pick
/heal-review 4, 6, 7                   # Fix specific gaps
/heal-review 1-3                       # Fix a range
```

After healing each gap, `/heal-review` re-runs grep patterns from ALL previously-healed gaps. If healing Gap 3 undoes Gap 1's fix, it detects the regression and re-fixes immediately (max 1 retry per cross-gap conflict).

**Strategy** — work small to large:
1. `/heal-review <low-effort gaps>` — mechanical fixes
2. `/heal-review <medium gaps>` — module splits, missing tests
3. `/heal-review <high-effort gap>` — one at a time for big changes
4. `/validate-review` after each pass

---

## Mechanical Linters & the Recipes Catalog

Both planning commands now identify candidate mechanical linters and surface them in their plans. `/scaffold-linter` converts those candidates into deterministic pre-commit hooks.

### Why mechanical linters

The [Anthropic harness paper's](https://www.anthropic.com/engineering/harness-design-long-running-apps) main insight: the evaluator should be objective. `/check` today has two evaluators — universal tooling (pyright/ruff/eslint/tsc + SAST/SCA — mechanical, fast, reliable) and architecture rules (LLM judgment — slower, sometimes wrong). Custom linters convert the architecture half into mechanical too. Result: `/fix-check` loops run faster, verdicts are objective, and `ARCHITECTURE.md` rules become *executable* rather than aspirational.

### `/scaffold-linter` — Mechanize a Rule

```
/scaffold-linter no-session-in-services --recipe python-fastapi-layered/check_no_session_in_services.py
/scaffold-linter useeffect-has-why --recipe vite-react/check_useeffect_has_why.ts
```

What it does:
1. Detects project type, picks recipe directory (`recipes/linters/<type>/`)
2. Reads the named recipe as exemplar
3. Adapts to project specifics (package name, layer paths, value sets)
4. Writes `tools/pre_commit_checks/check_<rule>.{py|ts}`
5. Appends hook entry to `.pre-commit-config.yaml`
6. Runs `pre-commit run check-<rule>` to verify it executes

If the verifier exits clean → the rule is now enforced on every commit AND inside `/check`. If it exits with violations → those are real existing issues to fix (commonly with `/fix-check`).

### Three natural invocation paths

| Trigger | What surfaces it |
|---|---|
| **From `/plan-release`** | The new `## Mechanical Rules to Enforce` section in `IMPLEMENTATION_PLAN.md` lists candidate linters with one-line scaffold commands per rule. Run them at the appropriate phase (some rules apply from day one; enum discipline waits for `enums/` to exist). |
| **From `/plan-fix`** | The new `## Recurring Patterns Worth Promoting to Linters` section in `FIX_PLAN.md` flags grep patterns that hit ≥ 2 files. Scaffold each candidate **after** the corresponding fix phase completes — that way the linter ships clean. |
| **Directly** | Any time you notice a recurring issue and want to mechanize the rule on the spot. |

### The recipes catalog (`recipes/linters/`)

Reference exemplars — read by Claude when scaffolding, adapted to project specifics, never copied verbatim.

| Directory | Linters | Source projects |
|---|---|---|
| `python-fastapi-layered/` | 12 — file/function size, StrEnum discipline, no Session/models/transactions in services, no SQLAlchemy in routers, HTTPException placement, SQLAlchemy 2.0 typed Mapped, datetime patterns | AI-SDLC, museum-analysis |
| `python-clean-arch/` | 6 — pure domain layer, no UI exceptions in core, DI discipline, async-only HTTP | pharma-derive, museum-analysis |
| `vite-react/` | 3 — `import.meta.env` only via `lib/env.ts`, every `useEffect` has `// WHY:` comment, no fetch in `useEffect` | Inferred from `rules/vite-react/*.md` + global frontend rules |

The catalog grows by upstream contribution: when a project ships a mature project-specific linter, generalize it back into the recipe directory so the next project can scaffold it directly.

### Architecture rules walk a path

```
vibes in Claude's head  →  documented in ARCHITECTURE.md  →  executable as tools/pre_commit_checks/check_*.{py|ts}
```

Each `/plan-fix → /scaffold-linter` cycle pushes one more rule from "LLM judges during /check" → "deterministic mechanical evaluator." The harness gets faster and more reliable over time.

---

## `/check` vs `/fix-check` vs `/review-architecture`

| | `/check` | `/fix-check` | `/review-architecture` |
|---|---|---|---|
| **Scope** | Changed files (git diff) | Violations from `/check`, or fix units from `FIX_PLAN.md` | Entire codebase |
| **Speed** | Minutes | Minutes | 10+ minutes |
| **Modifies code?** | No (read-only) | Yes | No (read-only) |
| **Output** | Inline verdict | Inline report (or `REVIEW_FIX_LOG.md` when run after `/plan-fix`) | `REVIEW.md` |
| **When to use** | Before every merge | After `/check` finds violations, or after `/plan-fix` | At release milestones |
| **Self-correcting loop?** | N/A | Yes (max 3 iterations, auto-revert) | N/A |
| **Evaluator** | N/A | Runs `/check` logic internally, or grep patterns from `FIX_PLAN.md` | N/A |

---

## Memory Management

### The Context Priority Hierarchy

| Source | Priority | Notes |
|--------|----------|-------|
| CLAUDE.md | High | Authoritative project instructions |
| Rules Directory | High | Auto-loaded when paths match |
| Skills (commands) | Medium | Loaded on-demand when triggered |
| Conversation history | Variable | Decays over long sessions |
| File contents (Read) | Standard | Normal context |

### CLAUDE.md Best Practices

Keep it short. If CLAUDE.md is too long, important rules get lost in noise.
- Ruthlessly prune instructions Claude already follows correctly
- Move detailed patterns to rules files with path matching
- Convert enforcement to hooks where possible

### Rules Auto-Loading

Rules load automatically when Claude reads files matching the path pattern:

```markdown
---
paths: src/api/**/*.ts
---

# These instructions get high priority ONLY during API work
```

---

## Multi-Layer Quality Enforcement

```
Layer 1 — Write-time:    Rules auto-load → guides code generation
Layer 2a — Commit-time:  Universal tooling (pyright/ruff/eslint/tsc + SAST/SCA)
Layer 2b — Commit-time:  Project-specific mechanical linters (pre-commit hooks
                         scaffolded by /scaffold-linter from recipes catalog —
                         architecture rules become executable AST checks)
Layer 3 — Merge-time:    /check → /fix-check → re-run /check
Layer 4 — Release-time:  Full /review-architecture pipeline
```

| Layer | What It Catches | Speed | Scope |
|-------|----------------|-------|-------|
| Rules | Pattern violations during generation | Instant | Current file |
| Tooling (universal) | Type errors, lint, security CVEs | Seconds | Changed files |
| Mechanical linters (project) | Architecture rules ("services don't import models", "useEffect has WHY:", "StrEnum only") | Seconds | Changed files / target layer |
| `/check` + `/fix-check` | Remaining architectural rules (LLM judgment) | Minutes | Git diff |
| `/review-architecture` | Everything + cross-reference | 10+ min | Entire project |

---

## Key Design Principles

### Plan → Validate → Do

Both workflows separate planning, validation, and execution:
- **Development**: `/plan-release` plans → `/plan-validate` verifies → `/implement-phase` executes
- **Release gate**: `/plan-fix` plans → `/fix-check` executes

This separation improves quality because:
1. Planning gets dedicated attention with per-file specs
2. Validation catches vague specs before any code is written
3. User reviews between each step
4. Subagents receive precise, Sonnet-calibrated instructions
5. Per-phase files keep subagent context clean (no cross-phase noise)

### Orchestrator Delegation Rule

Commands like `/fix-check`, `/heal-review`, `/implement-phase` are **orchestrators** that MUST NOT edit source code directly. All code changes are dispatched to specialized subagents via the `Agent` tool.

Orchestrator actions:
- Read files, Grep/Glob for patterns
- Run tooling via Bash
- Dispatch subagents via Agent
- Write review artifacts (REVIEW.md, FIX_PLAN.md, etc.)

### Trust But Verify (Generator/Evaluator Separation)

Inspired by [Anthropic's harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps): "Models tend to confidently praise the work—even when quality is obviously mediocre." Separating the generator from the evaluator is essential.

- **Generator**: Subagents that fix code — never self-evaluate
- **Evaluator**: `/check` rules + tooling + grep patterns — the objective oracle
- **Harness**: Orchestrator that loops generator → evaluator until clean or budget exhausted
- Validation is never done by the same agent that implemented
- Tooling is source of truth (tools override Grep heuristics)
- Regression = revert (Karpathy pattern: keep improvements, discard regressions)
- Max 2-3 iterations to prevent infinite loops

### Human Checkpoints

- `/plan-fix` → user reviews `FIX_PLAN.md` before `/fix-check`
- `/plan-release` → user reviews plan files → `/plan-validate` verifies before `/implement-phase`
- `/fix-check` → user confirms fix plan before execution
- Phase checkpoints pause for confirmation
- Gaps flagged for manual intervention after max retries

---

## When to Use What

| Scenario | Commands |
|----------|----------|
| Starting a new feature | `/plan-release` → `/plan-validate` → `/implement-phase N` → `/check` |
| Before merging a feature branch | `/check` |
| `/check` found violations | `/fix-check` → `/check` again |
| New project bootstrap | `/review-architecture` → `/plan-fix` → `/fix-check` → `/validate-review` |
| Onboarding existing project | Same as bootstrap |
| Before a release | Full release gate workflow |
| Quick drift check | `/review-architecture` only |
