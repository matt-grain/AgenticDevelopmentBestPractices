# Fix Pre-Merge Check — Self-Correcting Harness

You are a check-fix **harness**. Your job is to fix violations found by `/check` and **keep looping until clean or bailed out** — the human should not need to re-run `/check` manually.

This command implements a Generator/Evaluator separation pattern:
- **Evaluator**: The `/check` logic (tooling + architecture rules) — the objective oracle
- **Generator**: Subagents that fix violations — never self-evaluate
- **Harness**: You — orchestrating the loop, tracking progress, reverting on regression

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are the harness orchestrator. ALL code changes MUST be delegated to a subagent via the `Agent` tool with the correct `subagent_type`.

Your only allowed actions:
- **Read** files (to understand context, verify fixes)
- **Grep/Glob** (to scan for patterns, verify results)
- **Bash** (to run tooling gates — linters, formatters, tests, git operations)
- **Agent** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)

If you catch yourself about to use Edit/Write on a source file — STOP and dispatch a subagent instead.

## CRITICAL — Harness Loop Contract

```
MAX_ITERATIONS = 3
iteration = 0

while iteration < MAX_ITERATIONS:
    violations = run_evaluator()       # Step 1: /check logic
    if violations == 0: break          # Clean — done
    if iteration > 0 and violations >= previous_violations:
        revert_last_batch()            # Regression — undo
        break                          # Bail out, report what's left
    fix(violations)                    # Step 2-3: group + dispatch fixes
    iteration += 1
    previous_violations = violations

report(iteration, violations)          # Step 4: final report
```

The loop is unconditional within the max — do NOT pause to ask the human between iterations. The human sees the final report.

---

## Step 0 — Snapshot & Scope

1. **Create a restore point**: Run `git stash create` to capture current state. Store the hash — this is the rollback target if everything goes wrong.
2. **Determine the diff scope** (same as `/check` Step 0):
   - Detect base branch: `git rev-parse --verify main 2>/dev/null || git rev-parse --verify master`
   - Get changed files: `git diff --name-only --diff-filter=ACMR $(git merge-base HEAD <base>)..HEAD`
   - Filter to source files only
   - Detect project type from file extensions
3. **Detect subagent type** (same mapping as `/fix-check`):

   | Project Detection | subagent_type |
   |---|---|
   | `pyproject.toml` contains `fastapi` | `python-fastapi` |
   | `next.config.*` exists | `react-nextjs` |
   | `vite.config.*` exists | `vite-react` |
   | `pubspec.yaml` contains `flutter` | `flutter` |
   | Python + MCP patterns | `python-mcp-expert` |
   | Other | `general-purpose` |

4. Report: `"Harness started — {N} changed files, project type: {type}. Max 3 iterations."`

---

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

If `.shipboard.yml` exists in the repo root and `.mcp.json` registers `shipboard`:

1. Read `.shipboard.yml`; extract `component.name`.
2. Call:
   ```
   shipboard(action="report_lifecycle_stage",
             component=<component.name>,
             stage="verify_iterate",
             sub_state="iterate",
             source="fix-check",
             pr_number=<if known, else null>)
   ```
3. On failure (no MCP, server down, network error), append a one-line JSON entry to `.shipboard/pending_events.log` and continue. Reporting is best-effort — it MUST NOT block the actual command execution.

If `.shipboard.yml` does not exist, skip this step silently (the user hasn't run `/init-component` yet — fine; the harness still works).

## Step 1 — Run Evaluator (the Oracle)

This step runs the `/check` logic internally. It is the **source of truth** — never skip it, never approximate it.

### 1a — Run Tooling

Run the project's tooling scoped to changed files:

**Python/FastAPI:**
```bash
uv run pyright <changed .py files> 2>&1 || true
uv run ruff check <changed .py files> 2>&1 || true
uv run lint-imports 2>&1 || true
uv run pytest 2>&1 || true
```

**Next.js / Vite React:**
```bash
pnpm tsc --noEmit 2>&1 || true
pnpm eslint <changed .ts/.tsx files> 2>&1 || true
pnpm vitest run 2>&1 || true
```

**Flutter:**
```bash
dart analyze --fatal-infos 2>&1 || true
dart format --set-exit-if-changed <changed .dart files> 2>&1 || true
flutter test 2>&1 || true
```

Capture all output. Parse errors into a structured list.

### 1b — Run Security Scan

Same as `/check` Step 1.5 — run SAST/SCA on changed files. Parse findings into the violation list.

### 1c — Run Architecture Check

Read each changed source file and apply the `/check` Step 2 architecture rules. This is the same rule set as `/check` — do NOT invent new rules or skip rules.

For each violation found, record: `{ severity, file, line, issue, rule, grep_pattern }`.

The `grep_pattern` field is critical — it's the objective test for whether the fix worked. For each violation, define a Grep command that would detect it. Examples:
- "Service imports Session" → `grep -n "Session" services/foo.py`
- "Missing return type" → `grep -n "def foo(" services/foo.py` (check if `->` follows)
- "Raw string comparison" → `grep -n '"active"' services/foo.py`

### 1d — Count & Classify

```
Evaluator results (iteration {N}):
- Tooling errors: {X}
- Security findings: {Y} (🔴 {a} / 🟡 {b})
- Architecture violations: {Z} (🔴 {c} / 🟡 {d})
- Total violations: {X + Y + Z}
```

Store the total count as `current_violations`.

### 1e — Loop Decision

```
if current_violations == 0:
    → Jump to Step 4 (report success)

if iteration > 0:
    if current_violations >= previous_violations:
        → Revert last batch (git checkout -- <files modified in last iteration>)
        → Jump to Step 4 (report with "regression detected, reverted")
    else:
        → Log: "Iteration {N}: {previous} → {current} violations (Δ-{diff}). Continuing."

if iteration >= MAX_ITERATIONS:
    → Jump to Step 4 (report remaining violations)
```

---

## Step 2 — Group Violations into Fix Units

### 2a — Phase 0: Tooling Auto-fixes

Extract violations that tooling can fix directly (no subagent):

| Violation Type | Fix Action |
|---|---|
| Linting errors (ruff, eslint, dart analyze) | `ruff check --fix` / `pnpm eslint --fix` / `dart fix --apply` |
| Formatting issues | `ruff format` / `pnpm prettier --write` / `dart format` |
| Import sorting | `ruff check --select I --fix` |

Run these immediately. They are free — no subagent cost, no risk.

### 2b — Prioritize Remaining Violations

Sort violations by fix priority:
1. **🔴 Critical security** — always first
2. **🔴 Critical architecture** — structural issues that may cause cascading violations
3. **🟡 Warnings** — only if iteration budget allows

On iteration 1: fix 🔴 Critical only (leave 🟡 for later iterations).
On iteration 2+: include 🟡 Warnings if 🔴 are resolved.

This prevents wasting iteration budget on warnings when critical issues dominate.

### 2c — Group into Fix Units

Same grouping logic as the original `/fix-check`:
- Same violation type across files → one unit
- Max 8 files per unit
- One issue type per unit
- Tag each unit with `subagent_type`

### 2d — Gather Context (MANDATORY)

Before building fix instructions, the harness MUST:
1. **Read the violating file** at the exact lines
2. **Search for existing enums/types** the fix should use
3. **Check adjacent code** for the correct pattern (find a file that does it right)
4. **Check behavioral context** for behavioral violations

This step prevents the most common failure: vague instructions → bad fixes → new violations → wasted iteration.

### 2e — Build Concrete HOW TO FIX Instructions

For each fix unit, write explicit before/after transformations. Same quality bar as original `/fix-check` Step 3b:

| BAD (wastes an iteration) | GOOD (fixes in one shot) |
|---|---|
| "Use enums instead of raw strings" | "Replace `"pending"` with `OrderStatus.PENDING` (import from `enums/order.py`)" |
| "Fix the type annotation" | "Add `-> OrderOut` return type to `get_order()` on line 45" |
| "Move logic out of router" | "Extract lines 23-48 into `OrderService.create_order()`, call it from router" |

---

## Step 3 — Execute Fixes (Generator Phase)

### 3a — Mark Iteration Start

```bash
# Tag the pre-fix state so we can revert this iteration if needed
git stash create  # store hash as iteration_restore_point
```

Record all files that will be modified in this iteration (the revert scope).

### 3b — Dispatch Subagents

For each fix unit, dispatch to the correct subagent. The prompt MUST include:

```
You are fixing specific architecture violations found by an automated pre-merge check.

PROJECT CONTEXT:
{Relevant sections from ARCHITECTURE.md}

FIX UNIT: {title}
VIOLATIONS TO FIX:
{For each violation: file, line, issue, rule}

FILES TO MODIFY (you MUST modify ALL):
{complete file list}

HOW TO FIX (step-by-step — follow exactly):
{Concrete instructions from Step 2e}

IMPORTANT:
- Do NOT skip files.
- Follow existing code style exactly.
- NEVER add wrapper code or abstractions — apply the direct fix.
- Do NOT introduce new violations:
  - No new raw strings for closed sets
  - No new `Any`/`any` without justification
  - No new untyped dicts
  - No new `# type: ignore` without justification
  - No silent no-ops
  - No placeholder text without tracker reference
```

### 3c — Verify Each Fix Unit (Don't Trust the Generator)

After each subagent completes:

1. **File count check**: Did it modify all listed files?
2. **Read modified files**: Verify the fix actually addresses the violation
3. **Regression Grep**: Run violation-specific grep patterns on modified files:
   - The ORIGINAL violation pattern (should now return 0 matches)
   - Common fix-introduced patterns (new `Any`, new raw strings, new `# type: ignore`)
4. **If subagent missed files or introduced violations**: re-dispatch ONCE for the specific failures

### 3d — Record Iteration Metadata

```
Iteration {N} complete:
- Fix units dispatched: {X}
- Files modified: {list}
- Subagent retries used: {Y}
```

Store `previous_violations = current_violations` and `iteration += 1`.

→ **Loop back to Step 1** (re-run the evaluator on the now-modified codebase)

---

## Step 4 — Final Report

After exiting the loop (clean, regression, or max iterations), produce the report.

### 4a — Determine Exit Reason

| Exit | Symbol | Meaning |
|---|---|---|
| Clean after iteration N | ✅ | All violations resolved |
| Max iterations reached | ⚠️ | Improved but not clean |
| Regression detected (reverted) | ❌ | Last fix batch made things worse — reverted |

### 4b — Output Report

```
## Fix Check Harness — Final Report

### Loop Summary
| Iteration | Violations | Δ | Fix Units | Files Modified |
|-----------|-----------|---|-----------|----------------|
| 0 (initial) | {N} | — | — | — |
| 1 | {N} | -{X} | {Y} | {Z} |
| 2 | {N} | -{X} | {Y} | {Z} |
| ... | ... | ... | ... | ... |

### Tooling Status
- pyright/tsc: ✅ Pass / ❌ {N} errors
- ruff/eslint: ✅ Pass / ❌ {N} errors
- tests: ✅ Pass / ❌ {N} failures

### Violation History
| Violation | File | Iteration 0 | Iteration 1 | Iteration 2 | Final |
|-----------|------|-------------|-------------|-------------|-------|
| Missing return type | services/foo.py | 🔴 | ✅ Fixed | — | ✅ |
| Raw string status | services/bar.py | 🔴 | 🔴 | ✅ Fixed | ✅ |
| Service imports Session | services/baz.py | 🔴 | 🔴 | 🔴 | ⚠️ Remaining |

### Verdict
✅ ALL CLEAR — {N} violations resolved in {M} iterations. Clean merge.
⚠️ IMPROVED — {X}/{N} violations resolved in {M} iterations. {Y} remaining (listed above).
❌ REGRESSION — Iteration {M} increased violations. Reverted to iteration {M-1} state. {Y} violations remain.
```

### 4c — If Not Clean, Provide Actionable Next Steps

For each remaining violation:
1. Why the harness couldn't fix it (too complex? cascading dependency? needs human judgment?)
2. Suggested manual approach
3. Specific file and line to look at

---

## Design Principles

1. **The evaluator is the oracle.** The `/check` rules + tooling output are objective truth. The fixer never judges its own work.

2. **Regression = revert.** If a fix iteration doesn't reduce violations, undo it. Inspired by Karpathy's autoresearch: keep improvements, discard regressions.

3. **No human in the loop (during execution).** The harness runs autonomously up to MAX_ITERATIONS. The human sees the final report. Inspired by Karpathy: "Do NOT pause to ask the human if you should continue."

4. **Context before dispatch.** Every subagent gets concrete instructions with exact enum names, import paths, and before/after. Vague prompts waste iterations.

5. **Separate generator from evaluator.** The subagent (generator) fixes code. The harness re-runs `/check` (evaluator) to verify. The generator never self-evaluates. Inspired by Anthropic's harness paper: "self-evaluation exhibits optimism bias."

6. **Iteration budget is scarce — spend wisely.** Fix 🔴 Critical first. Only spend iterations on 🟡 Warnings after critical issues are gone.

7. **One retry per subagent, not per loop.** Within an iteration, each subagent gets one retry for missed files. The LOOP handles macro-level retries. Don't nest retries.

8. **Minimize scaffolding over time.** Track which violation types consistently need 2+ iterations. Those are candidates for better HOW TO FIX templates or rule refinements — reduce the need for the loop rather than relying on it.

---

## Differences from Original `/fix-check`

| Aspect | Original | Harness |
|---|---|---|
| Evaluator | Parses `/check` output from conversation | Runs `/check` logic internally |
| Loop | 1 retry max, then report | Up to 3 iterations with revert |
| Human in loop | User manually re-runs `/check` | Automatic re-evaluation |
| Regression handling | Report new violations | Auto-revert + bail out |
| Violation tracking | Per-fix-unit | Per-violation across iterations |
| Priority | Fix all at once | 🔴 first, 🟡 later |
| Exit conditions | Fixed or partial | Clean, improved, or regression |
