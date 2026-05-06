# Validate Fix Plan

You are an independent fix-plan **validator**. Your job is to read `FIX_PLAN.md` (and per-phase files when present) and verify it is detailed enough for subagents (especially Sonnet) to execute correctly — without skipped files, vague instructions, or stale grep patterns.

**You are NOT the planner.** You are a 3rd-party reviewer. Do not assume the plan is correct — verify every claim against the codebase, the original `REVIEW.md`, and the rules.

## Why This Command Exists

Sonnet subagents follow fix instructions literally. When a fix unit says "fix the type annotations in service files", Sonnet picks one or two files and stops. When a fix unit says "Open each file in the list. For every `def` method that lacks `-> ReturnType`, add the return type. For `__init__` methods: add `-> None`. For methods returning a single model: add `-> ModelName`", Sonnet processes every file mechanically. The quality of the fix is bounded by the quality of the plan.

Fix plans have one extra failure mode that feature plans don't: **stale grep patterns**. If `REVIEW.md` was generated last week and the codebase has moved, some violations may already be fixed. A fix unit whose grep pattern returns zero matches right now wastes a subagent dispatch. Validation catches this BEFORE you burn context on phantom fixes.

## Step 0 — Load Plan and Context

1. **Find the plan files.** Check for:
   - `FIX_PLAN.md` (single-phase) — OR
   - `FIX_PLAN.md` (overview) + `FIX_PLAN_PHASE_*.md` (per-phase plan files, e.g., `FIX_PLAN_PHASE_1.md`)
   - If neither exists, tell the user: "No fix plan found. Run `/review-architecture` then `/plan-fix` first." and stop.
   - If only a monolithic `FIX_PLAN.md` exists with ≥30 fix units OR ≥3 themes, flag this in the report: "⚠️ Fix plan should be split into per-phase files to keep PRs reviewable. See Phase Structure section."
2. **Read all plan files.**
3. **Read `REVIEW.md`** — it is the source-of-truth for what fixes are needed. Compare the fix plan's coverage against REVIEW.md's findings: every actionable finding (🔴 Critical and 🟡 Warning) should map to a fix unit unless it's in the Deferred Items list.
4. **Read `ARCHITECTURE.md`** — understand project structure and what "correct" looks like.
5. **Read `CLAUDE.md`** (if exists) — project-specific rules.
6. **Detect project type** (pyproject.toml with fastapi, pubspec.yaml with flutter, next.config.*, vite.config.*).
7. **Quick codebase scan**: Glob for files referenced as "Reference example" in the plan. Read 1-2 to verify they actually demonstrate the target pattern.

## Step 1 — Validate Fix Unit Completeness

For EACH fix unit in the plan, check it against the **Fix Unit Spec Checklist**:

### Required Fields (every fix unit)

| Field | Required? | What to check |
|---|---|---|
| **Title** | REQUIRED | Action-oriented, not just the violation name. ("Replace raw string statuses with ComponentStatus enum" not "Status fields") |
| **Theme** | REQUIRED | Maps to one of the standard themes (Security / Layer-boundary / Typing / File-size / FSM-enum / Tests / Dead code / CI gates) or a documented project-specific theme |
| **Severity** | REQUIRED | 🔴/🟡/🔵 — must match the source REVIEW.md finding's severity |
| **Agent** | REQUIRED | Specific subagent_type, not "general-purpose" unless the file types genuinely don't have a specialist |
| **Files** | REQUIRED | **Complete list, one per line.** No "e.g.", "such as", "and similar". |
| **Violation pattern (Grep)** | REQUIRED | Exact grep pattern that returns >0 matches **right now** in the listed files |
| **Expected after fix** | REQUIRED | Usually "zero matches" — must be verifiable mechanically |
| **Reference example** | REQUIRED | An exact path to a file in the codebase that already demonstrates the END state of the fix, OR a small inline code snippet showing the target pattern |
| **HOW TO FIX** | REQUIRED | Numbered steps. Mechanical, not judgment-driven. |

**Flag as ❌ INCOMPLETE** if any required field is missing.

### File Splitting Fix Units — Additional Required Fields

For "split this file" fix units (file > 200 lines):

| Field | Required? | What to check |
|---|---|---|
| **SPLIT PLAN** | REQUIRED | Lists every resulting file with line ranges or section descriptions, plus import-update files |
| **Constraint** | REQUIRED | "Every resulting file under 200 lines" or equivalent |

### Two-Step Fix Units — Additional Required Fields

For fix units with sub-units (e.g., "create method first, then update callers"):

| Field | Required? | What to check |
|---|---|---|
| **Sub-unit ordering** | REQUIRED | Sub-units numbered (`2.1a` before `2.1b`) with explicit dependency |
| **Step boundaries** | REQUIRED | Each sub-unit's HOW TO FIX is independently executable — Sub-unit B's instructions don't reference Sub-unit A's intermediate state |

## Step 1.5 — Validate Grep Patterns Are Live (UNIQUE TO FIX PLANS)

This is the check that's specific to fix plans and absent from `/plan-validate`. Execute every fix unit's violation grep pattern **right now** against the codebase:

```bash
for fix_unit in plan:
    matches = grep(fix_unit.violation_pattern, fix_unit.files)
    if matches == 0:
        flag as STALE
    elif matches > 0:
        record actual count for the report
```

**Stale patterns** (zero matches right now) indicate one of:
1. The violation was already fixed since `REVIEW.md` was generated
2. The grep pattern in the plan is wrong (typo, escaping issue)
3. The file list in the plan is wrong (the violation is in different files than listed)

In all three cases the fix unit must be removed or rewritten before execution. Running `/fix-review` against a stale fix unit wastes a subagent dispatch and may produce destructive "fixes" to code that's already correct.

**Flag as ❌ BLOCKER** any fix unit whose grep pattern returns zero matches.

### Stale-pattern report row

| Fix Unit | Pattern | Files in scope | Actual matches | Action |
|----------|---------|----------------|----------------|--------|
| 2.3 | `def \w+\(.*\):\s*$` | services/*.py | **0** (was 12 in REVIEW.md) | Remove from plan — already resolved |
| 2.7 | `transition.*"[a-z_]+"` | services/order_service.py | **0** (file no longer exists) | Update file list or remove |

## Step 2 — Validate Against Architecture Rules

### Per-Layer Rule Cross-Check

Same per-layer rules as `/plan-validate` Step 2 — verify the FIX target shape matches the architecture rules. The reference example must demonstrate the END state, not the starting state.

**Python/FastAPI files:**

| File location | Rule to verify in fix-unit reference + HOW TO FIX |
|---|---|
| `services/*.py` | Reference must show repository-only DI, no Session params, Pydantic returns, no commit/flush/rollback |
| `schemas/*.py` | Reference must separate Create/Update/Out and use StrEnum for status fields |
| `routers/*.py` | Reference must include `response_model` and `status_code` |
| `enums/*.py` | Reference must use Python 3.12 `StrEnum` (built-in), lowercase snake values |
| `state_machines/*.py` | Reference must show transition map with explicit allowed transitions |
| `repositories/*.py` | Reference must show data access only — no business logic |

**Flutter files:**

| File location | Rule to verify in fix-unit reference + HOW TO FIX |
|---|---|
| `domain/entities/*.dart` | Reference must use `@freezed`, status as enum, no `Map<String, dynamic>` |
| `domain/enums/*.dart` | Reference must use enhanced enum with `fromString()` that **throws** on unknown |
| `data/models/*_dto.dart` | Reference must have typed nested DTOs and `toEntity()` mapper |
| `presentation/providers/*.dart` | Reference must use `ref.watch` in build, typed state |
| `presentation/widgets/*.dart` | Reference must avoid `setState` for server data |

**React/Next.js/Vite files:**

| File location | Rule to verify in fix-unit reference + HOW TO FIX |
|---|---|
| `features/*/types.ts` | Reference must avoid `any`/`Record<string, unknown>` |
| `features/*/schemas/*.ts` | Reference must use Zod for runtime validation, not raw TS types |
| `features/*/hooks/*.ts` | Reference must use TanStack Query, not raw `useEffect` fetch |
| `app/**/*.tsx` (or `pages/`) | Reference must show error boundary on data-fetching routes |

### Cross-File Consistency Check

| Check | What to verify |
|---|---|
| **REVIEW.md coverage** | Every actionable 🔴/🟡 finding in REVIEW.md maps to a fix unit OR appears in Deferred Items |
| **Theme + severity ordering** | 🔴 Critical fix units appear in earlier phases than 🟡 Warning ones |
| **Reference files exist** | Every "Reference example: X" → verify X actually exists in the codebase |
| **Reference demonstrates END state** | The reference file must NOT contain the violation pattern itself — it must show what the fix looks like, not what's broken |
| **Within-phase dep ordering** | Fix unit 2.3 saying "depends on Fix unit 2.1" → 2.1 actually appears earlier and produces what 2.3 needs |
| **Cross-phase dep ordering** | Phase 3 saying "requires Phase 2" → Phase 2 actually delivers the prerequisite |
| **Batch size** | No fix unit exceeds 8 files (split into 2.4a / 2.4b if so) |

## Step 3 — Validate Phase Structure

### 3a — Phase Isolation (Per-Phase Files)

If the plan has **≥30 fix units OR ≥3 themes**, it MUST be split into per-phase files:

```
FIX_PLAN.md                  ← Overview: phases, themes, dependencies
FIX_PLAN_PHASE_1.md          ← Full fix-unit specs for Phase 1 only
FIX_PLAN_PHASE_2.md          ← Full fix-unit specs for Phase 2 only
FIX_PLAN_PHASE_N.md          ← ...
```

**Why?** When `/implement-fix-phase 2` runs, the subagent receives the phase file as context. A monolithic plan with all phases pollutes the context with irrelevant fix units from other themes — Sonnet may apply the wrong HOW TO FIX, or the context truncates and critical instructions are lost.

**Each phase file MUST be self-contained:**
- All fix-unit specs for that phase's theme
- Dependencies on earlier phases stated explicitly ("Phase 2 (layer cleanup) must be complete before this phase's typing fixes")
- Agent assignment for that phase
- No references to fix units in other phase files without restating them

**Flag as ❌ BLOCKER** if:
- A monolithic plan has ≥30 fix units or ≥3 themes and hasn't been split
- A phase file references fix units from another phase without restating them
- A phase file exceeds 300 lines (too large for effective subagent context)

### 3b — Phase Structure Checks

1. **Severity ordering**: 🔴 Critical phases must precede 🟡 Warning phases must precede 🔵 Note phases.
2. **Theme coherence**: Each phase covers one theme. A phase with both "typing fixes" and "file splits" should be split (different mental models, different review focus).
3. **Phase size**: Is any phase too large (>15 fix units or >50 files)? Recommend splitting into theme-sub-phases.
4. **Agent assignment**: Does each phase have a single `subagent_type`? If a phase mixes Python + TypeScript fix units, split by stack.
5. **Dependency acyclicity**: Build the dep graph. Flag cycles.

### 3c — Sonnet Readability Test

For each fix unit, apply this mental test: **"If I gave this fix unit to a Sonnet agent with no prior conversation context, would it produce correct fixes mechanically — or would it have to make judgment calls?"**

Specifically check:

| Test | Pass criteria | Common failure |
|---|---|---|
| **Can Sonnet find every file in scope?** | Complete file list — no "e.g.", no "such as", no "and similar elsewhere" | "Apply this pattern to all relevant service files" |
| **Can Sonnet execute each HOW TO FIX step mechanically?** | Numbered steps, each step is a search/replace or insertion | "Refactor the imports to follow the new structure" |
| **Can Sonnet recognize the END state?** | Reference example shows the fix applied | Reference is just the broken file ("see services/foo.py for an example of the issue") |
| **Can Sonnet verify success?** | Grep pattern returns zero matches after fix | "Make sure the code is cleaner" |
| **Are method signatures fully specified?** (for two-step fixes that ADD code) | Full signature: `def deactivate(self, user_id: int) -> None:` | Partial: "add a deactivate method" |
| **Are imports listed?** (when fixing requires new imports) | Imports listed or trivially derivable from context | Missing — Sonnet has to guess |
| **Is the constraint specific enough?** | Stack-specific rules ("use `@freezed`, no `Map<String, dynamic>`") | Generic ("follow best practices") |
| **Are there judgment calls?** | None — every decision is pre-made in the plan | "Decide whether this should be a new service or added to an existing one" |

**Flag as ⚠️ NEEDS REFINEMENT** any fix unit where 2+ tests fail.

## Step 4 — Scan for Common Fix-Plan Gaps

Patterns most commonly missed by fix plans:

| Gap | How to detect | Fix suggestion |
|---|---|---|
| **Vague HOW TO FIX** | Steps say "fix the typing" / "refactor the imports" without concrete operations | Rewrite as numbered search/replace steps with exact patterns |
| **Stale grep pattern** | Pattern returns 0 matches right now | Remove fix unit (already resolved) or correct the pattern |
| **"e.g." / "such as" in file list** | Plan uses example syntax instead of complete enumeration | Re-run Glob/Grep, list every file |
| **Reference file shows the violation, not the fix** | Reference file's content matches the violation pattern | Find a different reference file that demonstrates the END state |
| **Reference file does not exist** | Glob for the path returns nothing | Update reference to a real file, or write an inline code snippet |
| **Missing inline snippet for greenfield fixes** | Fix introduces a new pattern not yet in the codebase | Add a code snippet showing the target pattern |
| **Fix unit > 8 files** | Batch size limit violated | Split into sub-units (2.4a, 2.4b) with sequential dependency |
| **No Agent assignment** | Plan lists files but no subagent_type | Add agent based on file types |
| **Within-phase deps unstated** | Two-step fix (create method, update callers) without ordering | Number sub-units, add explicit dependency |
| **Cross-phase deps unstated** | Phase claims "requires Phase 2" but doesn't say what Phase 2 produces | Restate the prerequisite explicitly |
| **Cycles in dep graph** | Phase 3 → Phase 2 → Phase 4 → Phase 3 | Reorder phases or split fix units |
| **Theme mismatch** | Fix unit's grep pattern is about typing but it's filed under "Layer-boundary violations" | Re-categorize |
| **Severity drift** | REVIEW.md flagged 🔴, plan filed as 🟡 (or vice versa) | Match plan severity to REVIEW.md |
| **Plan covers ≤80% of REVIEW.md findings** | Many actionable findings absent from plan AND not in Deferred | Either add fix units or document deferral with reason |
| **Tests deferred to later phase** | Code fixed in Phase 2, tests added in Phase 5 | Move tests into the same phase as the code fix |

## Step 5 — Report

Output validation results directly in conversation (no file output):

```
## Fix Plan Validation — FIX_PLAN.md (+ {N} per-phase files)

### Coverage vs REVIEW.md
| Status | Count |
|--------|-------|
| Findings covered by a fix unit | {N}/{total} |
| Findings explicitly deferred | {N} |
| Findings missing from plan | {N} ← BLOCKER if any |

### Fix Unit Completeness
| Status | Count | Details |
|--------|-------|---------|
| ✅ Complete | {N} | All required fields present, grep pattern is live, reference exists |
| ⚠️ Partial | {N} | Missing fields or weak HOW TO FIX |
| ❌ Stale | {N} | Grep pattern returns zero matches right now (BLOCKER) |
| ❌ Incomplete | {N} | Missing required fields (BLOCKER) |

### Stale Fix Units (BLOCKERS)
| Fix Unit | Pattern | Expected Matches | Actual | Action |
|----------|---------|------------------|--------|--------|
| 2.3 | `def \w+\(.*\):\s*$` | >0 | 0 | Remove or correct |

### Incomplete Fix Units
| Fix Unit | Missing |
|----------|---------|
| 1.4 | No reference example, HOW TO FIX has 1 vague step |
| 3.7 | "e.g., services/foo_service.py" — file list is incomplete |

### Architecture Rule Violations in Plan
| Fix Unit | Issue |
|----------|-------|
| 2.5 | Reference file `services/old_service.py` shows `dict` returns — Sonnet will copy the violation |
| 4.1 | Reference file `domain/entities/user.dart` does not exist |

### Phase Structure
| Check | Status |
|-------|--------|
| ≥30 units / ≥3 themes split into per-phase files | ✅ / ❌ |
| Severity ordering (🔴 → 🟡 → 🔵) | ✅ / ❌ |
| Theme coherence per phase | ✅ / ❌ |
| Phase size ≤15 fix units | ✅ / ❌ {phase N has 22} |
| Dep graph is acyclic | ✅ / ❌ |

### Sonnet Readability
| Test | Fix Units Failing |
|------|-------------------|
| Complete file list | {N} |
| Mechanical HOW TO FIX | {N} |
| END-state reference | {N} |
| Verifiable success | {N} |
| No judgment calls | {N} |

### Summary
- Total fix units in plan: {N}
- ✅ Complete: {X}/{N}
- ⚠️ Need refinement: {Y}
- ❌ Blockers (must fix before /implement-fix-phase or /fix-review): {Z}

### Verdict
✅ READY TO IMPLEMENT — plan is detailed enough for Sonnet subagents.
⚠️ NEEDS REFINEMENT — {Y} fix units have gaps. Refine before running `/implement-fix-phase` or `/fix-review`.
❌ NOT READY — {Z} blockers (stale patterns and/or missing required fields). Plan needs significant revision before execution.
```

If the verdict is not ✅, list the specific fixes needed in priority order: BLOCKERS first (stale patterns and missing required fields), then WARNINGS (Sonnet-readability gaps).

## Design Principles

- **Independent validation**: You are NOT the planner. Question everything. Re-run grep patterns. Verify references demonstrate the END state, not the starting state.
- **Sonnet-calibrated**: The bar is "would Sonnet produce correct fixes mechanically from this fix unit alone, with no judgment calls?" If not, it's incomplete.
- **Live grep is the killer feature**: Every fix unit's grep pattern is re-run right now. Stale patterns (REVIEW drift, false-positive findings, fixes already shipped) get caught here, not after a wasted subagent dispatch.
- **No code changes**: This is a read-only command. You validate the plan, you don't fix it.
- **Fast**: This should take 2-5 minutes for a small plan, ~10 minutes for a multi-phase plan with hundreds of fix units. Read the plan, re-run greps, scan references, report gaps.
- **Actionable**: Every gap must have a concrete fix suggestion. "Vague HOW TO FIX" is not actionable — "Rewrite as numbered search/replace steps with exact patterns" is.
