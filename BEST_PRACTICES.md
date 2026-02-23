## Best practices for Claude Code

### Memory management

#### The Context Priority Hierarchy

| Source                    | Priority Level     | Implication                           |  
|---------------------------|--------------------|---------------------------------------|
| CLAUDE.md                 | High               | Treated as authoritative instructions |  
| Rules Directory           | High               | Same weight as CLAUDE.md              |   
| Skills                    | Medium (on-demand) | Loaded only when triggered            |   
| Conversation history      | Variable           | Decays over long sessions             |   
| File contents (Read tool) | Standard           | Normal context, no special weight     |  

#### CLAUDE.md

The over-specified CLAUDE.md. If your CLAUDE.md is too long, Claude ignores half of it because important rules get lost in the noise.
> Fix: Ruthlessly prune. If Claude already does something correctly without the instruction, delete it or convert it to a hook.

#### Rules

Rules are loaded automatically when Claude code reads a file and the path matching is true

```
---
paths: src/api/**/*.ts
---
 
# These instructions get high priority ONLY during API work
```


#### Trust but verify

The trust-then-verify gap. Claude produces a plausible-looking implementation that doesn’t handle edge cases.
> Fix: Always provide verification (tests, scripts, screenshots). If you can’t verify it, don’t ship it.

---

### End-to-End Development Workflow

The full release cycle from issues to deployment, with quality enforcement at every stage:

```
┌─────────────────────────────────────────────────────────────────────┐
│  PLAN                                                               │
│  /plan-release (from GH Issues / Jira tickets)                      │
│  → reads ARCHITECTURE.md, rules, agents                             │
│  → creates implementation plan with dependency order                 │
│  → dispatches agents per feature with full constraints               │
├─────────────────────────────────────────────────────────────────────┤
│  BUILD (per feature branch)                                         │
│  Agent implements → rules auto-load at write-time                   │
│  Agent runs tooling after implementation (pyright, ruff, tests)     │
│  Pre-commit hooks catch mechanical violations on commit             │
│  /check before merge → architectural gate on git diff               │
│  Merge to main                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  RELEASE GATE (all features merged)                                 │
│  /review-architecture → full codebase audit                         │
│  /plan-fix → detailed fix plan with HOW TO FIX per unit             │
│  (user reviews & edits FIX_PLAN.md)                                 │
│  /fix-review → executes plan, dispatches subagents                  │
│  /validate-review → independent verification                        │
│  /heal-review (if needed) → self-healing loop                       │
│  /validate-review (final) → ALL CLEAR                               │
├─────────────────────────────────────────────────────────────────────┤
│  DEPLOY                                                             │
│  Release to staging for testing                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### The Commands

**Development commands** (run repeatedly during development):

| Command | When | Speed | Purpose |
|---------|------|-------|---------|
| `/plan-release` | Start of release cycle | Minutes | Plan features from issues, dispatch agents with context |
| `/check` | Per feature branch, before merge | Minutes | Fast, read-only, diff-scoped architectural gate |

**Release gate commands** (run once per release milestone, in order):

| # | Command | Speed | Purpose |
|---|---------|-------|---------|
| 1 | `/review-architecture` | 10+ min | Full 5-agent codebase audit |
| 2 | `/plan-fix` | 5-10 min | Detailed fix plan with file lists + HOW TO FIX per unit |
| 3 | `/fix-review` | 10+ min | Executes FIX_PLAN.md, dispatches subagents |
| 4 | `/validate-review` | 10+ min | Independent verification (Grep + tooling + test matrix) |
| 5 | `/heal-review` | 10+ min | Self-healing loop with max 2 rework cycles |

#### Command Usage & Parameters

**`/plan-release`** — accepts issue references as arguments:
```
/plan-release GH#301, GH#404, GH#412        # GitHub issues by number
/plan-release #301 #404                       # Short form
/plan-release JIRA-205, GH#301               # Mixed sources
/plan-release "Add invoice export feature"    # Free-text description
```
Fetches issue details via `gh issue view`, reads `ARCHITECTURE.md` for project context, creates a phased implementation plan with dependency ordering, and dispatches the right subagent per feature with full constraints embedded in the prompt.

**`/plan-fix`** — produces a detailed fix plan before execution:
```
/plan-fix                                # Reads REVIEW.md, writes FIX_PLAN.md
```
Reads every finding from `REVIEW.md`, expands example files to complete lists via Grep/Glob, inspects 2-3 affected files per finding to understand the violation in context, finds reference examples of the correct pattern, and writes `FIX_PLAN.md` with concrete HOW TO FIX instructions for each fix unit. The user reviews and edits the plan before running `/fix-review`.

**Why use `/plan-fix`?** Subagents produce dramatically better results when given precise, pre-inspected instructions ("Replace `data: dict` with `data: ItemCreate` on line 67") versus vague directives ("fix the type annotations"). The planning step also catches issues early — wrong file lists, missing dependencies between fixes, unrealistic scope — before any code is changed.

**`/heal-review`** — accepts gap selectors to target specific gaps:
```
/heal-review Gap 2, Gap 5, Gap 7    # Fix specific gaps (quick wins first)
/heal-review 1                       # Fix a single large gap in a dedicated session
/heal-review 1-3                     # Fix a range of gaps
/heal-review                         # No args → shows gap table with effort estimates, lets you pick
```
When called without arguments, displays all gaps with effort estimates (Low/Medium/High) based on file count and change complexity. Recommends starting with Low effort gaps for quick wins. Warns before starting High effort gaps that affect 15+ files.

**Recommended `/heal-review` strategy** — work from small to large:
1. First pass: `/heal-review <low-effort gaps>` — mechanical fixes (enum replacements, missing return types, etc.)
2. Second pass: `/heal-review <medium gaps>` — module splits, missing test files
3. Third pass: `/heal-review <high-effort gap>` — one at a time for architectural changes (service→repo extraction, TanStack Query migration, etc.)
4. After each pass: `/validate-review` to update completion percentage

---

### Code Quality Enforcement — Multi-Layer Defense

Quality enforcement happens at 4 layers, from write-time to release-time. Each layer catches what the previous one missed.

#### The Layers

```
Layer 1 — Write-time:    Rules auto-load when agent reads files → guides code generation
Layer 2 — Commit-time:   Tooling (ruff, pyright, eslint, tsc) blocks mechanical violations
Layer 3 — Merge-time:    /check scans only changed files for architectural violations
Layer 4 — Release-time:  Full /review-architecture pipeline audits entire codebase
```

| Layer | What It Catches | Speed | Scope |
|-------|----------------|-------|-------|
| Rules (auto-load) | Guides the agent to follow patterns | Instant | Current file |
| Tooling (commit) | Type errors, lint, imports, security | Seconds | Changed files |
| `/check` (merge) | Architectural violations, missing tests, SoC breaches | Minutes | Git diff |
| `/review-architecture` (release) | Everything above + full codebase cross-reference | 10+ min | Entire project |

---

### Pre-Merge Gate: `/check`

A fast, focused architecture check on only the files changed in the current branch. Run before every merge.

- **Completely read-only and non-destructive** — never modifies files, never runs git checkout/reset/push
- Uses only read-only git commands: `git diff --name-only`, `git merge-base`, `git rev-parse`
- Scopes to `git diff` against base branch — only changed files
- Runs tooling in check mode (pyright/ruff check/eslint/tsc/dart analyze) + tests
- Reads changed files to analyze them against architectural rules
- Checks for "missing companions": new endpoint without test, new stateful entity without FSM, new module without ARCHITECTURE.md update
- Reports inline (no file output) with a verdict: READY TO MERGE / REVIEW BEFORE MERGING / DO NOT MERGE

**When to use**: After finishing a feature branch, before creating a PR or merging. Quick enough to run after every batch of changes. Safe to run at any time — it only reads, never writes.

---

### Architecture Review & Fix Pipeline

A 4-command pipeline to audit a codebase against your rules, fix all findings with zero gaps, and verify completeness. Run at release milestones or when onboarding an existing project.

#### The Commands

| Command | Output | Purpose |
|---------|--------|---------|
| `/review-architecture` | `REVIEW.md` | Full audit against all rules (5 parallel agents) |
| `/plan-fix` | `FIX_PLAN.md` | Detailed fix plan — file lists, HOW TO FIX, agent assignments, phases |
| `/fix-review` | `REVIEW_FIX_LOG.md` + updated `REVIEW.md` | Execute the fix plan, dispatch subagents, verify results |
| `/validate-review` | `REVIEW_VALIDATION.md` | Independent verification (Grep + tooling + test coverage matrix) |
| `/heal-review` | Updated `REVIEW.md` + `REVIEW_VALIDATION.md` | Self-healing loop for remaining gaps |

#### The Flow

```
/review-architecture → /plan-fix → (user reviews FIX_PLAN.md) → /fix-review → /validate-review
                                                                                     │
                                                                                ALL CLEAR? → done
                                                                                     │ no
                                                                                /heal-review
                                                                                     │
                                                                                /validate-review
                                                                                     │
                                                                                ALL CLEAR? → done
                                                                                     │ no
                                                                                manual intervention
```

#### Review Cycle Lifecycle

Reviews are not one-shot — they repeat at each release milestone. The pipeline handles this automatically:

```
Release 1.0 features done
    │
    ├─ /review-architecture     → REVIEW.md (fresh)
    ├─ /plan-fix                → FIX_PLAN.md (user reviews & edits)
    ├─ /fix-review              → executes plan, REVIEW_FIX_LOG.md
    ├─ /validate-review         → REVIEW_VALIDATION.md → ALL CLEAR ✅
    │
    │  ... features developed, /check used on each branch ...
    │
Release 1.1 features done
    │
    ├─ /review-architecture     → archives old files to reviews/2025-06-15_*
    │                           → writes fresh REVIEW.md
    ├─ /plan-fix                → fresh plan
    ├─ /fix-review              → fresh cycle
    └─ ...
```

**Auto-archival**: When `/review-architecture` runs and finds existing review artifacts (`REVIEW.md`, `REVIEW_VALIDATION.md`, `REVIEW_FIX_LOG.md`), it moves them to a `reviews/` directory with date prefix before starting the new cycle. Clean slate, history preserved.

**Staleness detection**: `/fix-review` and `/validate-review` warn if the REVIEW.md is older than 7 days — the codebase may have changed since the review.

#### Why This Pipeline Exists

The naive approach — "review, then fix" — has a reliability gap: review findings list *example* files (`router_users.py`), but the agent only fixes those examples, not the 12 other routers with the same issue. Checkboxes get marked done without full verification.

This pipeline closes the gap with four layers of defense:

1. **`/plan-fix` — Thinking before doing**: Reads every finding, inspects the actual code, expands to complete file lists, and writes concrete HOW TO FIX instructions in `FIX_PLAN.md`. The user reviews and edits the plan before any code is touched. This separation of planning from execution is the single biggest improvement to fix quality — subagents work dramatically better when given precise, pre-approved instructions.

2. **`/fix-review` — Mechanical execution**: Reads `FIX_PLAN.md` and executes each fix unit by dispatching the right subagent with the pre-written instructions. Verifies post-fix with Grep re-check, tooling gate, and file count reconciliation. Because the plan is already detailed, the orchestrator's job is simpler and more reliable.

3. **`/validate-review` — Independent verification**: A separate pass that re-scans the entire codebase for each violation pattern, runs tooling in report-only mode, and builds a test coverage matrix. Catches anything `/fix-review` missed.

4. **`/heal-review` — Self-healing loop**: For any remaining gaps, creates paired tasks (implement + validate) with a different agent validating than the one that fixed. Max 2 rework cycles per gap to prevent infinite loops.

#### When to Use

| Scenario | What to Run |
|----------|-------------|
| **After finishing a feature branch** | `/check` |
| **New project bootstrap** | `/review-architecture` → `/plan-fix` → `/fix-review` → `/validate-review` |
| **Existing project onboarding** | Same as bootstrap |
| **Before a release** | `/review-architecture` → `/plan-fix` → full pipeline |
| **Quick drift check** | `/review-architecture` + `/validate-review` (skip fix) |

#### Key Design Decisions

- **Plan before fix** — `/plan-fix` separates "thinking" from "doing". The planner reads code, expands file lists, writes concrete instructions. The fixer (`/fix-review`) just executes the plan. This separation dramatically improves fix quality because: (a) the plan gets dedicated attention, (b) the user can review and edit before code changes, (c) subagents receive precise instructions, (d) the plan serves as audit documentation.
- **Orchestrator delegation rule** — `/fix-review`, `/heal-review`, and `/plan-release` are orchestrators that MUST NOT edit source code directly. All code changes are dispatched to specialized subagents via the `Task` tool. The orchestrator's role is limited to: reading files, scanning with Grep/Glob, running tooling via Bash, dispatching subagents, and writing review artifacts. This ensures the right agent (with the right rules loaded) does the implementation.
- **Validation is never done by the same agent that implemented the fix** — no self-grading.
- **Human checkpoints** between phases — `/fix-review` pauses between migration phases, `/heal-review` asks before starting.
- **Max 2 rework cycles** in `/heal-review` to prevent infinite loops — unresolved items are flagged for manual intervention.
- **All findings stay in REVIEW.md** — statuses are updated inline (`✅ Fixed`, `⚠️ Partial`) but original findings are never deleted, preserving audit history.
- **Subagent mapping is explicit** — each command references the agent definition files in `~/.claude/agents/` by name, with fallback to `general-purpose`.
- **Tooling is source of truth** — both `/fix-review` (tooling gate between phases) and `/validate-review` (tooling verification step) run actual tools (pyright, ruff, eslint, dart analyze, flutter test, pytest). Grep heuristics are a supplement, not a substitute. Tools override Grep.
- **Every rule needs a Grep pattern** — abstract rules without matching concrete Grep tasks in the audit agents get missed. When adding a new rule, always add the corresponding detection pattern to the review agents.