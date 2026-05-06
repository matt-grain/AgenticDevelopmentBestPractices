# Fix Architecture Review — Self-Correcting Harness

You are a review fix **harness**. Your job is to systematically fix ALL findings in `REVIEW.md` and **keep looping until clean or bailed out** — the human should not need to manually run `/validate-review`.

This command extends the original `/fix-review` with a Generator/Evaluator loop:
- **Evaluator**: The grep patterns from the manifest — objective, deterministic
- **Generator**: Subagents that fix violations — never self-evaluate
- **Harness**: You — orchestrating phases, tracking violations across iterations, reverting regressions

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are the harness orchestrator. ALL code changes MUST be delegated to a subagent via the `Agent` tool with the correct `subagent_type`.

Your only allowed actions:
- **Read** files (to understand context, build manifests, verify fixes)
- **Grep/Glob** (to scan for patterns, expand file lists, verify results)
- **Bash** (to run tooling gates — linters, tests, formatters, git operations)
- **Agent** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)
- **Write** (ONLY for `REVIEW.md`, `REVIEW_FIX_LOG.md` — never source code)

## CRITICAL — Harness Loop Contract

```
MAX_ITERATIONS = 2
iteration = 0

# Step 0-1: Pre-flight + build manifest (same as original)
manifest = build_manifest()

while iteration < MAX_ITERATIONS:
    execute_all_phases(manifest)           # Step 2: fix phase by phase
    remaining = run_evaluator(manifest)    # Step 3: re-check ALL grep patterns
    if remaining == 0: break               # Clean — done
    if iteration > 0 and remaining >= previous_remaining:
        revert_last_iteration()            # Regression — undo entire iteration
        break
    manifest = rebuild_from_remaining()    # Shrink manifest to only what's left
    iteration += 1
    previous_remaining = remaining

update_review_md()                         # Step 4: update artifacts
report()                                   # Step 5: final report
```

The loop is autonomous within MAX_ITERATIONS. Ask user confirmation only once before the first iteration (the manifest review in Step 1d). After that, loop without pausing.

---

## Step 0 — Pre-flight Checks

Same as original `/fix-review` Step 0:

1. Read `REVIEW.md`. If missing → tell user to run `/review-architecture` and stop.
2. Check date — warn if older than 7 days.
3. Check for `REVIEW_FIX_LOG.md` — warn if previous cycle exists.
4. Detect project type and select subagent(s).
5. Verify agent definition files exist.

### Step 0a — Create Restore Point

```bash
git stash create  # store hash as harness_restore_point
```

This is the nuclear rollback if everything goes wrong.

### Step 0b — Check for FIX_PLAN.md (single-phase or multi-phase)

If `FIX_PLAN.md` exists, use it as the execution plan and skip Step 1. Two formats are now possible:

**Single-phase plan** — `FIX_PLAN.md` contains all fix units inline (legacy / small audits). Run them all in one harness pass as before.

**Multi-phase plan** — `FIX_PLAN.md` is an overview pointing at `FIX_PLAN_PHASE_*.md` per-phase files. In this case:

1. Parse the optional phase argument: the user may invoke `/fix-review N` to run only phase N.
2. **If a phase number is supplied** → load only `FIX_PLAN_PHASE_{N}.md` as the manifest source. The harness loop runs against that single phase's fix units.
3. **If no phase number is supplied** AND multi-phase files exist → the right tool is `/implement-fix-phase` (one phase = one PR) rather than running all phases in one pass. Tell the user:
   ```
   FIX_PLAN.md is multi-phase ({P} phases). Recommended:
     - Run `/implement-fix-phase N` to ship phase N as a focused PR (formal mode).
     - Or run `/fix-review N` to run the harness loop on phase N only without branching.
   Pass `--all-phases` to run every phase in one pass (not recommended for large refactors).
   ```
   Wait for the user to pick a phase or pass `--all-phases`.
4. **If `--all-phases` is supplied** → run the full harness loop sequentially across every phase, treating the union of all `FIX_PLAN_PHASE_*.md` fix units as the manifest. This is the legacy "run everything" behavior; useful only for small multi-phase plans where the overhead of one PR per phase isn't worth it.

Single-phase plans behave exactly as before — no flags needed.

### Step 0c — Regression Pre-flight

Same as original: if `REVIEW_FIX_LOG.md` exists, re-run previously-fixed grep patterns to detect regressions. Add regressions as Phase 0 fix units.

---

## Step 1 — Build the Exhaustive Fix Manifest

Same as original `/fix-review` Step 1 (1a through 1d):

- Expand examples to complete file lists via Grep
- Group into fix units (max 8 files, one issue per unit)
- Build manifest table with `Violation Pattern (Grep)` and `Expected After Fix`
- Present manifest and get user confirmation

**One addition**: Every fix unit MUST have a verifiable grep pattern. If a finding can't be expressed as a grep (e.g., "missing ARCHITECTURE.md"), use a file-existence check instead (`test -f ARCHITECTURE.md`).

### Manifest Quality Gate

Before proceeding, verify the manifest:
- Every fix unit has a `Violation Pattern` that returns >0 matches right now
- Every fix unit has an `Expected After Fix` (usually "zero matches")
- The total violations count is recorded as `initial_violations`

```bash
# Run all grep patterns, count total matches
total_violations = sum(grep_match_count for each fix_unit)
```

This is the baseline for the harness loop.

---

## Step 2 — Execute Fixes Phase by Phase

Same as original `/fix-review` Step 2 (2a through 2d), with these harness additions:

### Per Fix Unit (unchanged from original):
- 2a: Create tracking tasks
- 2b: Dispatch to subagent with concrete HOW TO FIX
- 2c: Verify subagent output (file count, grep re-check, spot-check quality)
- 2d: Update task status

### Between Phases — Tooling Gate (unchanged)

Run linters, type checkers, tests. Fix issues before proceeding.

### Between Phases — Cross-Phase Interference Check (NEW)

After completing Phase N, before starting Phase N+1:

1. **Re-run ALL grep patterns from Phase 0 through Phase N** — not just the current phase.
2. **Compare against post-phase counts** from earlier phases:
   - If a Phase 0 fix was undone by Phase 1 → **flag as cross-phase regression**
   - Re-dispatch a targeted fix for ONLY the regressed items before continuing
3. **Record per-phase snapshot**:
   ```
   Phase 0 complete: 15 grep patterns checked, 0 remaining
   Phase 1 complete: 25 grep patterns checked, 2 remaining (down from 10)
   ```

This catches the most insidious failure: a later fix undoing an earlier one.

### Phase Checkpoint (slightly modified)

After the cross-phase check:
```
Phase {N} complete: {X}/{Y} fix units verified.
Cross-phase check: ✅ no regressions / ⚠️ {N} regressions re-fixed
Tooling gate: ✅ pass / ❌ {N} issues
Proceeding to Phase {N+1}.
```

**Do NOT ask user confirmation between phases within an iteration.** The harness runs autonomously. Only pause if a critical error makes it impossible to continue.

---

## Step 3 — Run Evaluator (the Oracle)

After ALL phases are complete, run a full evaluation sweep.

### 3a — Re-run ALL Grep Patterns

For every fix unit in the manifest, re-run the violation pattern:

```
| # | Fix Unit | Grep Pattern | Before | After | Status |
|---|----------|-------------|--------|-------|--------|
| 1 | Add return types | `def \w+\(.*\):\s*$` in services/ | 12 | 0 | ✅ |
| 2 | Replace raw strings | `"(pending\|active)"` in services/ | 8 | 0 | ✅ |
| 3 | Move DB from services | `Session` import in services/ | 3 | 1 | ⚠️ |
```

### 3b — Run Full Tooling Gate

```bash
# Python
uv run pyright . 2>&1 || true
uv run ruff check . 2>&1 || true
uv run pytest 2>&1 || true

# JS/TS
pnpm tsc --noEmit 2>&1 || true
pnpm eslint . 2>&1 || true
pnpm vitest run 2>&1 || true

# Flutter
dart analyze --fatal-infos 2>&1 || true
flutter test 2>&1 || true
```

### 3c — Scan for Fix-Introduced Violations

Run regression grep patterns on ALL files modified during this iteration:

**Python:**
```
Grep: `\bdict\[str,` in services/ → new untyped dict signatures
Grep: `-> Any\b` → new Any returns
Grep: `"[a-z_]+".*:.*lambda` → raw string keys in dispatch dicts
Grep: `# TODO` → verify each has real tracker ref
Grep: `print(` → print in production code
Grep: `except:` → bare except
```

**Dart:**
```
Grep: `Color\(0x` → hardcoded colors
Grep: `String\?` on domain entity status fields → should be enum
Grep: `break;` after setting success state → silent no-op
```

**All:**
```
wc -l → files over 200 lines / 300 for tests
```

### 3d — Count & Classify

```
current_violations = grep_remaining + tooling_errors + new_violations
```

### 3e — Loop Decision

```
if current_violations == 0:
    → Jump to Step 4 (report success)

if iteration > 0 and current_violations >= previous_violations:
    → Revert this iteration:
      git checkout -- <all files modified in this iteration>
    → Jump to Step 4 (report with "regression detected, reverted")

if iteration >= MAX_ITERATIONS:
    → Jump to Step 4 (report remaining violations)

# Otherwise: loop
previous_violations = current_violations
iteration += 1
→ Rebuild manifest from remaining violations only (shrink scope)
→ Go to Step 2
```

### Manifest Rebuild for Iteration 2

When looping, don't re-run the full manifest. Build a **reduced manifest**:

1. Keep only fix units where the grep pattern still returns matches
2. Add any NEW violations detected in Step 3c as new fix units
3. Re-gather context for these fix units (read the modified files, not the originals)
4. Build fresh HOW TO FIX instructions based on the CURRENT state of the code

This is critical — the code has changed since iteration 1. Stale instructions from the original manifest will produce bad fixes.

---

## Step 4 — Update Artifacts

### 4a — Update REVIEW.md

Same as original Step 3: update finding statuses, migration plan checkboxes, add fix summary header, recalculate conformance.

### 4b — Generate REVIEW_FIX_LOG.md

Extended format with iteration tracking:

```markdown
# Fix Log — {project_name}

**Date:** {today's date}
**Based on:** REVIEW.md dated {review date}
**Harness iterations:** {N}

## Loop Summary
| Iteration | Violations | Δ | Fix Units | Files Modified |
|-----------|-----------|---|-----------|----------------|
| 0 (initial) | {N} | — | — | — |
| 1 | {N} | -{X} | {Y} | {Z} |
| 2 | {N} | -{X} | {Y} | {Z} |

## Per-Phase Results

### Phase 0 — Micro-fixes
| Fix Unit | Files | Grep Before | Grep After | Status |
|----------|-------|-------------|------------|--------|
| ... | ... | ... | ... | ✅/⚠️ |

### Phase 1 — Structural
| Fix Unit | Files | Grep Before | Grep After | Status |
|----------|-------|-------------|------------|--------|
| ... | ... | ... | ... | ✅/⚠️ |

## Cross-Phase Regressions (if any)
| Phase | Fix Unit | Regressed By | Re-fixed? |
|-------|----------|-------------|-----------|
| ... | ... | ... | ✅/❌ |

## Fix-Introduced Violations (if any)
| File | New Violation | Detected In | Fixed In | Status |
|------|--------------|-------------|----------|--------|
| ... | ... | Iter 1 eval | Iter 2 | ✅/⚠️ |

## Remaining Issues (if any)
{List with file names, grep patterns, and why the harness couldn't fix them}

## Verdict
✅ ALL CLEAR — {N} findings resolved in {M} iterations.
⚠️ IMPROVED — {X}/{N} resolved in {M} iterations. {Y} remaining.
❌ REGRESSION — Iteration {M} reverted. {Y} remain from iteration {M-1}.
```

---

## Step 5 — Report to User

Summarize:
1. Loop summary table (iterations, violation counts, deltas)
2. Total fix units processed and completion rate
3. Files modified count
4. Cross-phase regressions encountered and whether they were resolved
5. Fix-introduced violations encountered and whether they were resolved
6. Any remaining issues with file names and why they couldn't be fixed
7. Verdict

---

## Design Principles

1. **The grep patterns are the oracle.** Every fix unit has a deterministic, verifiable grep pattern. The evaluator runs ALL patterns after ALL phases — not just per-unit spot checks.

2. **Regression = revert.** If iteration 2 doesn't reduce total violations below iteration 1, undo all of iteration 2. Keep the better state.

3. **Cross-phase interference detection.** After each phase, re-run ALL prior phases' grep patterns. A fix that undoes a previous fix is caught immediately — not discovered in `/validate-review`.

4. **Manifest shrinks per iteration.** Iteration 2 only processes remaining violations. Context is re-gathered from the CURRENT file state, not stale originals.

5. **Autonomous within budget.** MAX_ITERATIONS = 2 (heavier than /fix-check's 3). User confirms once at the manifest review. After that, the harness runs without pausing.

6. **One retry per subagent, loop for macro.** Within a phase, each subagent gets one retry for missed files. The ITERATION handles macro-level correction. Don't nest retries.

7. **Phase checkpoints are lightweight.** No user confirmation between phases within an iteration — just cross-phase grep check + tooling gate.

---

## Differences from Original `/fix-review`

| Aspect | Original | Harness |
|---|---|---|
| Post-fix verification | "Run `/validate-review`" | Automatic evaluator loop |
| Loop | 1 retry per fix unit, then report | Up to 2 full iterations with revert |
| Cross-phase regression | Plan completion check (per phase only) | Re-run ALL prior grep patterns after each phase |
| Fix-introduced violations | Spot-check + regression grep | Full sweep of regression patterns |
| Human in loop | Confirm between phases | Confirm once at manifest, then autonomous |
| Violation tracking | Per-fix-unit | Per-violation across iterations |
| Manifest rebuild | N/A (single pass) | Shrinks to remaining violations for iteration 2 |
| Revert | N/A | Auto-revert if iteration doesn't improve |
| Artifact output | REVIEW_FIX_LOG.md (per-unit) | Extended with iteration tracking + cross-phase data |

---

## When NOT to Use the Harness

Use the original `/fix-review` (without harness) when:
- The review has 50+ fix units — the evaluator sweep becomes expensive
- You want manual control between phases (e.g., reviewing Phase 1 output before Phase 2)
- The project has fragile tests that may flake during the tooling gate loop

The harness is most valuable when:
- Reviews have 10-30 fix units
- Cross-file fixes are common (architecture, DI, enum introduction)
- Previous fix cycles have shown fix-introduced regressions
