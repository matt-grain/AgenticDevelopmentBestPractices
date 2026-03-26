# Best Practices for Claude Code Agentic Workflows

This document describes a complete development workflow using Claude Code commands, rules, and agents for building software with architectural discipline.

---

## Quick Reference

### Two Workflows

| Workflow | Purpose | Commands |
|----------|---------|----------|
| **Development** | Build features from issues | `/plan-release` → `/plan-validate` → `/implement-phase` → `/check` → `/fix-check` |
| **Release Gate** | Audit & fix before release | `/review-architecture` → `/plan-fix` → `/fix-review` → `/validate-review` → `/heal-review` |

### All Commands

| Command | Purpose | Input | Output |
|---------|---------|-------|--------|
| `/plan-status` | Dashboard: where are we? | — | Inline report |
| `/plan-release` | Design features, split into phases | Issue refs or free-text | `IMPLEMENTATION_PLAN.md` + per-phase files |
| `/plan-validate` | Verify plan detail is Sonnet-ready | Plan files | Inline verdict |
| `/implement-phase N` | Execute a specific phase | Phase number | Code + `IMPLEMENTATION_STATUS.md` |
| `/check` | Pre-merge architectural gate (read-only) | — | Inline verdict |
| `/fix-check` | Fix violations found by `/check` | Conversation with `/check` output | Inline report |
| `/review-architecture` | Full codebase audit | — | `REVIEW.md` |
| `/plan-fix` | Plan fixes with HOW TO FIX | `REVIEW.md` | `FIX_PLAN.md` |
| `/fix-review` | Execute fix plan | `FIX_PLAN.md` or `REVIEW.md` | `REVIEW_FIX_LOG.md` |
| `/validate-review` | Independent verification | Review artifacts | `REVIEW_VALIDATION.md` |
| `/heal-review` | Fix remaining gaps | `REVIEW_VALIDATION.md` | Updated artifacts |

---

## Development Workflow

Build features from GitHub Issues or Jira tickets with phased implementation and verification.

### The Flow

```
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
        ├─ /implement-phase 1 → /check ──┬─→ commit
        ├─ /implement-phase 2 → /check   │
        └─ /implement-phase 3 → /check   │
                                          │
                                 violations found?
                                          │
                                          ▼
                                    /fix-check → re-run /check → commit
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
        ▼
    FIX_PLAN.md (file lists, HOW TO FIX per unit)
        │
        ├─ User reviews & edits
        │
        ▼
    /fix-review
        │
        ▼
    /validate-review
        │
        ├─ ALL CLEAR? → done
        │
        ▼ (if gaps)
    /heal-review → /validate-review → done or manual intervention
```

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
5. Groups into phases (Phase 0: micro-fixes, Phase 1-2: structural/architectural)
6. Enforces batch size (max 8 files per unit)

**Output**: `FIX_PLAN.md` — review and edit before running `/fix-review`.

**Why plan first?** Subagents produce dramatically better results when given precise instructions ("Replace `data: dict` with `data: ItemCreate` on line 67") versus vague directives ("fix the types"). Planning also catches scope issues before code changes.

### `/fix-review` — Self-Correcting Fix Harness

Reads `FIX_PLAN.md` and executes each fix unit with a self-correcting evaluator loop. Same harness pattern as `/fix-check`, adapted for full-codebase scope.

```
/fix-review                            # Uses FIX_PLAN.md if present
```

What it does:
1. Reads `FIX_PLAN.md` (or builds manifest on-the-fly if missing)
2. For each fix unit, dispatches correct subagent with HOW TO FIX
3. Verifies each unit (Grep re-check, file count)
4. Runs tooling gate between phases
5. **Cross-phase interference check** — re-runs ALL prior phases' grep patterns after each phase
6. **Full evaluator sweep** after all phases — re-runs every grep pattern from the manifest
7. **Loops** — if violations remain and count decreased, rebuilds manifest for remaining only (max 2 iterations)
8. **Reverts on regression** — if iteration 2 doesn't improve over iteration 1, undo it
9. Updates `REVIEW.md` with fix statuses

**Output**: `REVIEW_FIX_LOG.md` (with iteration tracking) + updated `REVIEW.md`

**Key difference from `/fix-check`**: The evaluator uses the manifest's grep patterns as the oracle (deterministic, fast) rather than re-running 5 review agents. MAX_ITERATIONS = 2 (heavier scope).

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

## `/check` vs `/fix-check` vs `/review-architecture` vs `/fix-review`

| | `/check` | `/fix-check` | `/review-architecture` | `/fix-review` |
|---|---|---|---|---|
| **Scope** | Changed files (git diff) | Violations from `/check` | Entire codebase | Findings from `REVIEW.md` |
| **Speed** | Minutes | Minutes | 10+ minutes | 30+ minutes |
| **Modifies code?** | No (read-only) | Yes | No (read-only) | Yes |
| **Output** | Inline verdict | Inline report | `REVIEW.md` | `REVIEW_FIX_LOG.md` |
| **When to use** | Before every merge | After `/check` finds violations | At release milestones | After `/plan-fix` |
| **Self-correcting loop?** | N/A | Yes (max 3 iterations, auto-revert) | N/A | Yes (max 2 iterations, auto-revert) |
| **Evaluator** | N/A | Runs `/check` logic internally | N/A | Grep patterns from manifest |

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
Layer 2 — Commit-time:   Tooling blocks mechanical violations
Layer 3 — Merge-time:    /check → /fix-check → re-run /check
Layer 4 — Release-time:  Full /review-architecture pipeline
```

| Layer | What It Catches | Speed | Scope |
|-------|----------------|-------|-------|
| Rules | Pattern violations during generation | Instant | Current file |
| Tooling | Type errors, lint, security | Seconds | Changed files |
| `/check` + `/fix-check` | Architectural violations | Minutes | Git diff |
| `/review-architecture` | Everything + cross-reference | 10+ min | Entire project |

---

## Key Design Principles

### Plan → Validate → Do

Both workflows separate planning, validation, and execution:
- **Development**: `/plan-release` plans → `/plan-validate` verifies → `/implement-phase` executes
- **Release gate**: `/plan-fix` plans → `/fix-review` executes

This separation improves quality because:
1. Planning gets dedicated attention with per-file specs
2. Validation catches vague specs before any code is written
3. User reviews between each step
4. Subagents receive precise, Sonnet-calibrated instructions
5. Per-phase files keep subagent context clean (no cross-phase noise)

### Orchestrator Delegation Rule

Commands like `/fix-review`, `/fix-check`, `/heal-review`, `/implement-phase` are **orchestrators** that MUST NOT edit source code directly. All code changes are dispatched to specialized subagents via the `Agent` tool.

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

- `/plan-fix` → user reviews `FIX_PLAN.md` before `/fix-review`
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
| New project bootstrap | `/review-architecture` → `/plan-fix` → `/fix-review` → `/validate-review` |
| Onboarding existing project | Same as bootstrap |
| Before a release | Full release gate workflow |
| Quick drift check | `/review-architecture` only |
