# Implement Fix Phase from FIX_PLAN

You are a fix-phase implementation **orchestrator**. Your job is to execute one themed refactoring phase from a multi-phase `FIX_PLAN.md`, verify completion, and update the fix-tracking status. This command is the refactoring analog of `/implement-phase` — it ships one focused PR worth of architectural debt cleanup.

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are an orchestrator, not an implementer. ALL code changes MUST be delegated to a subagent via the `Task` tool with the correct `subagent_type`.

Your only allowed actions:
- **Read** files (to understand context, verify output)
- **Grep/Glob** (to scan codebase, verify files exist, re-run violation patterns)
- **Bash** (to run tooling gates, tests, git operations)
- **Task** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)
- **Write** (ONLY for `FIX_PLAN.md`, `FIX_PLAN_PHASE_*.md`, and `FIX_STATUS.md` — never source code)

## Step 0 — Pre-flight

1. **Parse arguments**: The user provides a phase number (e.g., `/implement-fix-phase 2`). If no phase specified, ask which phase to implement.

2. **Find the plan files.** Check for:
   - `FIX_PLAN_PHASE_{N}.md` (per-phase file) — **preferred**, read this for the target phase
   - `FIX_PLAN.md` (single-phase plan) — if no per-phase files exist, the plan is single-phase and `/fix-review` (not this command) is the right tool. Tell the user: "FIX_PLAN.md is single-phase. Use `/fix-review` to run the whole plan in one pass; this command is for multi-phase plans only." and stop.
   - If neither exists, tell the user: "No fix plan found. Run `/review-architecture` then `/plan-fix` first." and stop.

3. **Read the plan**: Read `FIX_PLAN_PHASE_{N}.md` — it contains all per-fix-unit specs for this phase and is self-contained. Also read `FIX_PLAN.md` for cross-phase context (theme, severity, dependencies).

4. **Parse the plan**: Extract:
   - Phase theme (used to derive the branch slug)
   - Phase severity (🔴/🟡/🔵)
   - The fix units in this phase, with files / violation patterns / expected-after-fix / HOW TO FIX
   - Within-phase dependencies (some fix units must run sequentially)
   - Cross-phase dependencies (does this phase depend on earlier phases being done?)

5. **Check phase dependencies**: If this phase depends on earlier phases, verify those are marked complete in `FIX_STATUS.md` (if it exists). If not, warn: "Phase {N} depends on Phase {M} which is not complete. Proceed anyway?" Wait for confirmation.

6. **Detect project type** (same logic as other commands: `pyproject.toml` with fastapi, `next.config.*`, `pubspec.yaml` with flutter, etc.)

7. **Read project context**: `ARCHITECTURE.md`, `CLAUDE.md`, `decisions.md`, `REVIEW.md` (if they exist) — the original review provides the why behind each fix unit.

## Step 1 — Present Phase Summary

Show the user what will be fixed:

```
## Fix Phase {N}: {theme}

**Severity:** 🔴/🟡/🔵
**Cross-phase deps:** Phase {M} (✅ complete / ⚠️ incomplete)
**Fix units:** {count}
**Files affected:** {count}
**Agent:** {subagent_type}

### Fix units in this phase:
1. Fix Unit {N}.1: {title} — {file count} files
2. Fix Unit {N}.2: {title} — {file count} files
...

### Violation patterns that should return ZERO matches after this phase:
{list grep patterns from each fix unit}

Proceed with implementation?
```

Wait for confirmation.

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

If `.shipboard.yml` exists in the repo root and `.mcp.json` registers `shipboard`:

1. Read `.shipboard.yml`; extract `component.name`.
2. Call:
   ```
   shipboard(action="report_lifecycle_stage",
             component=<component.name>,
             stage="generate",
             sub_state="fix-phase-<N>",   # N is the phase number from /implement-fix-phase <N>
             source="implement-fix-phase",
             pr_number=<if known, else null>)
   ```
3. On failure (no MCP, server down, network error), append a one-line JSON entry to `.shipboard/pending_events.log` and continue. Reporting is best-effort — it MUST NOT block the actual command execution.

If `.shipboard.yml` does not exist, skip this step silently (the user hasn't run `/init-component` yet — fine; the harness still works).

This step runs BEFORE Step 1.5 (branch creation) so the dashboard knows the work has started even if branch creation fails.

## Step 1.5 — Create the fix-phase branch

Before any subagent runs, isolate the work on its own git branch. This is what enables **formal mode** for refactoring — each themed phase becomes one PR with a CI gate before merge. Skipping this step puts you in **fast mode** (direct commits to main), which is fine for solo prototypes but loses code review and per-phase CI on architectural changes that often touch many files.

Branch creation is reversible (`git branch -D <name>` if you need to back out), so this does not break the orchestrator's "no source code edits" rule — branches are not source.

1. **Detect the main branch:**
   ```bash
   git rev-parse --verify main 2>/dev/null || git rev-parse --verify master
   ```
   Use whichever exists; treat both as "the trunk" for the rules below.

2. **Inspect the current branch and working tree:**
   - On trunk (`main`/`master`) with **clean** working tree → proceed to step 3.
   - On trunk with **dirty** working tree → stop and tell the user: "Working tree has uncommitted changes. Stash or commit them before starting Fix Phase {N}." Wait.
   - Already on `fix-phase-{N}-*` (re-running this phase) → skip step 3, continue to Step 2.
   - On any other branch → ask: "You're on `{branch}`, not trunk. Stay here (treat as the fix-phase branch), or switch to trunk and create `fix-phase-{N}-*`?" Wait for the answer.

3. **Derive the slug** from the phase theme. Lowercase, kebab-case, max ~30 chars, ASCII only. Examples:
   - "Layer-boundary violations" → `fix-phase-2-layer-boundaries`
   - "Typing discipline" → `fix-phase-3-typing-discipline`
   - "File/function size violations" → `fix-phase-4-size-violations`

4. **Create the branch:**
   ```bash
   git checkout -b fix-phase-{N}-{slug}
   ```
   If the branch already exists, ask the user whether to switch to it (re-run scenario) or pick a different name.

5. **Confirm:** print the branch name and the chosen mode (formal / fast) so the user has one last chance to redirect before any subagent runs. Wait for "yes" / "go" / Enter.

If the user explicitly chooses to stay on trunk for fast mode, note that in the Step 6 final report so the "Next steps" section proposes the right command (commit, not PR).

## Step 2 — Execute Fix Units

For each fix unit in the phase (in order if there are within-phase dependencies, parallel-friendly otherwise):

### 2a — Create Tracking Task

Use TaskCreate:
- **Subject:** `[Fix Phase {N}] Fix Unit {N}.{X}: {title}`
- **Description:** Full fix-unit spec from the plan (files, violation pattern, HOW TO FIX, reference example)
- **activeForm:** `Fixing: {title}`

### 2b — Dispatch to Subagent (MANDATORY)

**REMINDER: You MUST use the Task tool. Do NOT edit source files directly.**

Select subagent by file types (same matrix as `/implement-phase`):

| Files Affected | subagent_type |
|---|---|
| `.py` files (FastAPI) | `python-fastapi` |
| `.ts/.tsx` files (Next.js) | `react-nextjs` |
| `.ts/.tsx` files (Vite) | `vite-react` |
| `.dart` files (Flutter) | `flutter` |
| MCP server files | `python-mcp-expert` |
| Other | `general-purpose` |

The subagent prompt MUST include:
- Project context from ARCHITECTURE.md / CLAUDE.md / REVIEW.md (the **why** behind the fix)
- **The exact fix-unit spec from FIX_PLAN_PHASE_{N}.md** — paste verbatim: Files, Violation pattern, Expected-after-fix, Reference example, full HOW TO FIX steps. This is the primary quality mechanism.
- Project-type constraints (same as `/implement-phase`)
- Instructions to run tooling and tests after fixing
- A direct verification step: re-run the violation pattern after fixing; it MUST return zero matches
- **Self-verification checklist** — same checklist as `/implement-phase`:

```
BEFORE returning your result, verify EVERY file you modified against this checklist. Fix any violations inline — do NOT leave them for a later pass.

FLUTTER:
- [ ] Every domain entity uses @freezed — no hand-rolled copyWith or plain classes
- [ ] No Map<String, Object?> or Map<String, dynamic> anywhere in presentation — use typed data classes
- [ ] No raw string comparisons for state/status — use enum values everywhere
- [ ] No ?? defaultValue on required fields — validate and fail early instead
- [ ] No ref.read() inside build() — use ref.watch (ref.read only in callbacks)
- [ ] No business logic in presentation (no domain object construction in providers/widgets)
- [ ] No hardcoded Color(0xFF...) — use Theme tokens from core/theme/
- [ ] No scattered string constants — consolidate into enum or core/constants/
- [ ] No // TODO without issue reference
- [ ] Run dart analyze --fatal-infos and fix before returning

PYTHON/FASTAPI:
- [ ] Services depend on repositories only — never on other services (use workflows)
- [ ] No Session parameter in services — not even private methods
- [ ] All status/type fields use StrEnum — never raw str
- [ ] No dict[str, Any] returns — use Pydantic schemas
- [ ] No eager loading of all deps when only a subset is needed
- [ ] All list endpoints are paginated — no hardcoded limits
- [ ] No // TODO without issue reference
- [ ] Run ruff check and ruff format before returning

REACT/NEXT.JS/VITE:
- [ ] No Record<string, unknown> or { [key: string]: any } — use Zod schemas
- [ ] No raw string status comparisons — use const objects or string unions
- [ ] Multi-step forms extract each step into its own component
- [ ] No // TODO without issue reference
- [ ] Run tsc --noEmit and eslint before returning

ALL STACKS:
- [ ] Files under 200 lines, test files under 300 lines
- [ ] Functions under 30 lines
- [ ] No // TODO, // FIXME, // HACK without tracker reference
- [ ] After fixing, the violation pattern returns ZERO matches in the affected files
```

### 2c — Verify Fix Unit Output

After each fix unit completes:
1. **File check**: Glob for the expected files — were they all touched?
2. **Grep re-check**: Re-run the violation pattern from the fix unit. It MUST return zero matches in the targeted files. If it doesn't, dispatch a targeted retry with explicit "the pattern still matches in {file:line} — fix that specific occurrence" instructions (max 1 retry).
3. **Tooling gate**: Run type checker, linter on the touched files.
4. **Spot-check**: Read 1-2 files to verify they follow project patterns (the fix shouldn't introduce a new violation while resolving the original).
5. **Mark task complete** or flag partial.

### 2d — Between Fix Units

Report progress:
```
Fix Unit {N}.{X}/{Y} complete: {title}
- Files modified: {list}
- Violation pattern: {count before} → {count after}
- Tooling: ✅ pass / ❌ {errors}

Continuing to next fix unit...
```

## Step 3 — Phase Tooling Gate

After all fix units in the phase, run the full tooling suite (same as `/implement-phase` Step 3):

**Python/FastAPI:**
```bash
uv run pyright .
uv run ruff check . --fix
uv run ruff format .
uv run pytest
```

**Next.js/Vite:**
```bash
pnpm tsc --noEmit
pnpm eslint . --fix
pnpm prettier --write .
pnpm vitest run
```

**Flutter:**
```bash
dart analyze --fatal-infos
dart format .
flutter test
```

If any tool fails, dispatch a targeted subagent to fix the issues before proceeding.

## Step 4 — Phase Verification

### 4a — Re-run All Violation Patterns

Re-run EVERY grep pattern from this phase's fix units. They must ALL return zero matches. Build a verification table:

```
| Fix Unit | Grep Pattern | Before | After | Status |
|----------|-------------|--------|-------|--------|
| {N}.1 | {pattern} | 12 | 0 | ✅ |
| {N}.2 | {pattern} | 8 | 0 | ✅ |
| {N}.3 | {pattern} | 3 | 1 | ⚠️ |
```

If any row is ⚠️, re-dispatch a targeted fix for the remaining matches before proceeding (max 1 retry).

### 4b — Cross-Phase Regression Check

Re-run grep patterns from earlier completed phases (read `FIX_STATUS.md` for the list). A fix in this phase that undoes an earlier phase's fix is the most insidious failure mode. If detected:
1. Flag as 🔴 CRITICAL
2. Re-dispatch a targeted fix for ONLY the regressed items
3. Re-verify

### 4c — Build Verification Checklist

```
### Fix Phase {N} Verification Checklist

| Item | Status | Notes |
|------|--------|-------|
| All fix units processed | ✅ |
| All grep patterns return 0 | ✅ |
| Pyright/tsc clean | ✅ |
| Ruff/eslint clean | ✅ |
| Tests pass | ✅ |
| No cross-phase regressions | ✅ |
| Files modified within plan scope (no scope creep) | ✅ |
```

## Step 5 — Update Fix-Tracking Status

### 5a — Update `FIX_PLAN_PHASE_{N}.md`

Mark each fix unit's status inline (`✅ Complete` / `⚠️ Partial` / `❌ Failed`).

Add a status header at the top of the phase file:
```markdown
## Phase {N}: {theme}
**Status:** ✅ Complete / ⚠️ Partial ({X}/{Y} fix units) / ❌ Incomplete
**Branch:** fix-phase-{N}-{slug}
**Completed:** {date}
```

### 5b — Write/Update `FIX_STATUS.md` (MANDATORY)

**You MUST write this file.** This is the refactoring analog of `IMPLEMENTATION_STATUS.md`. Use the Write tool to create or update `FIX_STATUS.md` at the project root.

If the file exists, read it first, then update the Progress Summary table and append the new phase section. If it doesn't exist, create it:

```markdown
# Fix Status — {project_name}

**Last updated:** {date}
**Plan:** FIX_PLAN.md (multi-phase, {P} phases)

## Progress Summary

| Phase | Theme | Severity | Status | Fix Units | Completion |
|-------|-------|----------|--------|-----------|------------|
| 1 | Security findings | 🔴 | ✅ Complete | 5/5 | 100% |
| 2 | Layer-boundary violations | 🔴 | ✅ Complete | 8/8 | 100% |
| 3 | Typing discipline | 🟡 | 🔄 In Progress | 6/12 | 50% |
| 4 | File-size violations | 🟡 | ⏳ Pending | 0/15 | 0% |

**Overall:** {X}/{Y} fix units complete ({Z}%)

---

## Phase {N} — {theme}

**Implemented:** {date}
**Branch:** fix-phase-{N}-{slug}
**Agent:** {subagent_type}
**Tooling:** ✅ All pass / ⚠️ {N} warnings / ❌ {N} errors

### Completed
- ✅ Fix Unit {N}.1: {title} — {N} files, grep {before}→{after}
- ✅ Fix Unit {N}.2: {title} — {N} files, grep {before}→{after}

### Partial (needs attention)
- ⚠️ Fix Unit {N}.3: {title} — {what's still matching}

### Cross-phase Regressions
- {none, or list with re-fix status}

### Verification Checklist
| Item | Status |
|------|--------|
| All fix units processed | ✅ |
| All grep patterns clean | ✅ |
| Tooling clean | ✅ |
| No cross-phase regressions | ✅ |

---

## Next Phase Preview

**Phase {N+1}: {theme}**
- {fix unit count} fix units
- Severity: 🔴/🟡/🔵
- Dependencies: Phase {N} ✅
- Ready to start

---

## Gaps Requiring Attention

{List any ⚠️ or ❌ items that need manual intervention}
```

## Step 6 — Report to User

**Before reporting, verify you completed Step 5b** — `FIX_STATUS.md` MUST exist and be updated.

Summarize the phase:

```
## Fix Phase {N} Implementation Complete

**Status:** ✅ Complete / ⚠️ Partial
**Theme:** {theme}
**Severity:** 🔴/🟡/🔵
**Fix units:** {X}/{Y} complete
**Files modified:** {count}
**Violations resolved:** {total grep matches before → 0 after}
**Tooling:** ✅ All checks pass

### What was fixed:
{Brief summary, e.g., "Eliminated 27 raw string status comparisons across services and routers; all sites now use ComponentStatus / PRStatus enum members."}

### Cross-phase regressions: {none / list}

### Gaps (if any):
{List any partial/missing items}

### Next steps

Branch the user is currently on determines the recommended next move:

**Formal mode** (you're on `fix-phase-{N}-{slug}` from Step 1.5 — recommended):
1. Run `/check` to verify no architectural violations were introduced and all gates are green
2. If green, push the branch and open a focused PR:
   ```bash
   git push -u origin fix-phase-{N}-{slug}
   gh pr create \
     --title "fix: Phase {N} — {theme}" \
     --body "Resolves {N} fix units from FIX_PLAN_PHASE_{N}.md.

   ## Theme
   {theme} ({severity})

   ## Resolved
   - {fix unit 1 title}
   - {fix unit 2 title}
   - ...

   ## Verification
   - All grep patterns from this phase return zero matches
   - No cross-phase regressions
   - Tooling clean

   See FIX_STATUS.md for the full per-phase entry."
   ```
3. After CI passes and a reviewer approves, merge the PR (squash recommended)
4. Switch back to trunk and run `/implement-fix-phase {N+1}` for the next theme

**Fast mode** (you stayed on trunk in Step 1.5 — solo prototypes only):
1. Run `/check` to verify no architectural violations
2. Commit directly: `git add . && git commit -m "fix: Phase {N} — {theme}"`
3. Run `/implement-fix-phase {N+1}` for the next theme

After all phases complete:
- Run `/validate-review` for the full audit confirming every original REVIEW.md finding is resolved
- Optionally run `/heal-review` if any gaps remain

FIX_STATUS.md has been updated with full details.
```
