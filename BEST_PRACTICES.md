# Best Practices for Claude Code Agentic Workflows

This document describes a complete development workflow using Claude Code commands, rules, and agents for building software with architectural discipline.

---

## Quick Reference

### Two Workflows

| Workflow | Purpose | Commands |
|----------|---------|----------|
| **Development** | Build features from issues | `/plan-release` → `/implement-phase` → `/check` → `/fix-check` |
| **Release Gate** | Audit & fix before release | `/review-architecture` → `/plan-fix` → `/fix-review` → `/validate-review` → `/heal-review` |

### All Commands

| Command | Purpose | Input | Output |
|---------|---------|-------|--------|
| `/plan-status` | Dashboard: where are we? | — | Inline report |
| `/plan-release` | Design features, split into phases | Issue refs or free-text | `IMPLEMENTATION_PLAN.md` |
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
IMPLEMENTATION_PLAN.md (phases, tasks, dependencies)
        │
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

**Output**: `IMPLEMENTATION_PLAN.md` with phases, tasks per phase, file lists, and agent assignments. Review and edit before implementing.

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

### `/fix-check` — Fix Violations from `/check`

Structured fix command for violations found by `/check`. Replaces ad-hoc "fix them" requests with a disciplined pipeline:

```
# Run /check first, then when violations are found:
/fix-check                             # Fixes 🔴 Critical violations
                                       # Asks before fixing 🟡 Warnings
```

What it does:
1. **Parses** the `/check` violation table from the conversation
2. **Groups** violations into fix units (max 8 files each, one issue type per unit)
3. **Routes** to correct subagent by file type (.dart→flutter, .py→python-fastapi, .tsx→react-nextjs)
4. **Phase 0**: Runs tooling auto-fixes directly (ruff --fix, eslint --fix, dart fix)
5. **Phase 1+**: Dispatches subagents with violations, project context, and self-verification checklist
6. **Re-checks** all touched files after fixes — classifies results as Resolved / Remaining / New
7. **Retries once** if new violations were introduced (max 1 retry, no infinite loops)
8. **Reports** final state with verdict: ALL CLEAR / PARTIAL / REGRESSIONS

**Why use `/fix-check` instead of "fix them"?**
- Every subagent gets the per-stack self-verification checklist (prevents introducing new violations)
- Correct agent for correct stack (`.dart` fixes never go to a Python agent)
- Built-in re-check loop catches regressions
- Retry cap (1) prevents infinite fix loops

**Typical flow:**
```
/check                    → "❌ DO NOT MERGE — 5 critical violations"
/fix-check                → fixes violations, re-checks, reports
/check                    → "✅ READY TO MERGE"
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

### `/fix-review` — Execute the Plan

Reads `FIX_PLAN.md` and executes each fix unit:

```
/fix-review                            # Uses FIX_PLAN.md if present
```

What it does:
1. Reads `FIX_PLAN.md` (or builds manifest on-the-fly if missing)
2. For each fix unit, dispatches correct subagent with HOW TO FIX
3. Verifies each unit (Grep re-check, file count)
4. Runs tooling gate between phases
5. Plan completion check per phase (catches cross-unit interference)
6. Updates `REVIEW.md` with fix statuses

**Output**: `REVIEW_FIX_LOG.md` + updated `REVIEW.md`

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

Targeted fixes for gaps found by validation:

```
/heal-review                           # Shows gaps, lets you pick
/heal-review 4, 6, 7                   # Fix specific gaps
/heal-review 1-3                       # Fix a range
```

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
| **Re-checks after fix?** | N/A | Yes (1 retry max) | N/A | Yes (per phase) |

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

### Plan Before Do

Both workflows separate planning from execution:
- **Development**: `/plan-release` plans → `/implement-phase` executes
- **Release gate**: `/plan-fix` plans → `/fix-review` executes

This separation improves quality because:
1. Planning gets dedicated attention
2. User reviews before code changes
3. Subagents receive precise instructions
4. Plans serve as audit documentation

### Orchestrator Delegation Rule

Commands like `/fix-review`, `/fix-check`, `/heal-review`, `/implement-phase` are **orchestrators** that MUST NOT edit source code directly. All code changes are dispatched to specialized subagents via the `Agent` tool.

Orchestrator actions:
- Read files, Grep/Glob for patterns
- Run tooling via Bash
- Dispatch subagents via Agent
- Write review artifacts (REVIEW.md, FIX_PLAN.md, etc.)

### Trust But Verify

- Validation is never done by the same agent that implemented
- Tooling is source of truth (tools override Grep heuristics)
- Plan completion checks catch subagent misses
- Max 1-2 rework cycles to prevent infinite loops

### Human Checkpoints

- `/plan-fix` → user reviews `FIX_PLAN.md` before `/fix-review`
- `/plan-release` → user reviews `IMPLEMENTATION_PLAN.md` before `/implement-phase`
- `/fix-check` → user confirms fix plan before execution
- Phase checkpoints pause for confirmation
- Gaps flagged for manual intervention after max retries

---

## When to Use What

| Scenario | Commands |
|----------|----------|
| Starting a new feature | `/plan-release` → `/implement-phase N` → `/check` |
| Before merging a feature branch | `/check` |
| `/check` found violations | `/fix-check` → `/check` again |
| New project bootstrap | `/review-architecture` → `/plan-fix` → `/fix-review` → `/validate-review` |
| Onboarding existing project | Same as bootstrap |
| Before a release | Full release gate workflow |
| Quick drift check | `/review-architecture` only |
