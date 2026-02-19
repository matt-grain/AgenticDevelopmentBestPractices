# Fix Architecture Review Findings

You are a review fix orchestrator. Your job is to systematically implement ALL fixes identified in `REVIEW.md` — with zero gaps. The key discipline: **expand every finding into a complete file manifest BEFORE writing any code**, then fix file-by-file with tracking.

## Step 0 — Pre-flight Checks

1. Read `REVIEW.md` at the project root. If it doesn't exist, tell the user to run `/review-architecture` first and stop.
2. Check the `**Date:**` field in REVIEW.md. If it is older than 7 days, warn the user: "This review is from {date}. The codebase may have changed since then. Consider running `/review-architecture` for a fresh audit before fixing." Wait for confirmation before proceeding.
3. If `REVIEW_FIX_LOG.md` already exists, warn the user that a previous fix cycle was already run and ask if they want to continue (append to existing log) or start fresh.
4. Detect the project type (check for `pyproject.toml` with fastapi, `next.config.*`, `vite.config.*`, `package.json`).
3. Select the implementation subagent by matching the project type to the custom agent definitions in `~/.claude/agents/`:

   | Project Detection | subagent_type | Agent Definition File |
   |---|---|---|
   | `pyproject.toml` contains `fastapi` in dependencies | `python-fastapi` | `~/.claude/agents/python-fastapi.md` |
   | `next.config.ts` / `next.config.js` / `next.config.mjs` exists | `react-nextjs` | `~/.claude/agents/react-nextjs.md` |
   | `vite.config.ts` / `vite.config.js` exists | `vite-react` | `~/.claude/agents/vite-react.md` |
   | Python project with MCP server patterns | `python-mcp-expert` | `~/.claude/agents/python-mcp-expert.md` |
   | Other Python project | `general-purpose` | (built-in, no custom agent file) |
   | Other JS/TS project | `general-purpose` | (built-in, no custom agent file) |

   **Mixed projects** (e.g., FastAPI backend + React frontend): use different subagent types for different fix units based on which files are affected. Backend fixes use `python-fastapi`, frontend fixes use `react-nextjs` or `vite-react`.

   Verify the selected agent file exists by reading it. If the agent file is missing, fall back to `general-purpose` and warn the user.

## Step 1 — Build the Exhaustive Fix Manifest

This is the critical step that prevents gaps. For EACH actionable finding (🔴 Critical and 🟡 Warning) in REVIEW.md:

### 1a — Expand Examples to Complete File Lists

The REVIEW.md findings may list only example files. You MUST expand to the full scope:

- Use **Glob** to find ALL files matching the pattern (e.g., all routers, all services, all components)
- Use **Grep** to re-run the violation pattern and capture EVERY matching file — not just the ones the review mentioned
- Record the complete list

**Example**: If REVIEW.md says "Missing type annotations in `router_users.py`, `router_orders.py`", you must:
1. Glob for ALL router files: `**/routers/*.py`
2. Grep for `def ` without `->` in ALL of them
3. Build the complete list: maybe there are 8 routers, and 6 have the issue — list all 6, not just the 2 from the review

### 1b — Group Into Fix Units

Group related findings into logical fix units to avoid redundant work:

| Fix Unit Pattern | Grouping Logic |
|---|---|
| Same violation across many files | 1 unit per violation type (e.g., "Add type annotations" with file list) |
| Multiple violations in same file | 1 unit per file if fixes interact, otherwise keep separate |
| Structural changes (new directories, moved files) | 1 unit per structural change |
| New files to create (tests, enums, FSMs, docs) | 1 unit per file to create |

### 1c — Build the Manifest Table

Create a manifest with this structure:

```
| # | Fix Unit | Category | Files In Scope | Violation Pattern (Grep) | Expected After Fix | Priority |
|---|----------|----------|---------------|------------------------|-------------------|----------|
| 1 | Add return type annotations | Typing | [list ALL files] | `def \w+\(.*\):\s*$` (no ->) | Zero matches | Phase 0 |
| 2 | Move DB queries from services to repositories | Architecture | [list ALL files] | `Session` import in services/ | Zero matches | Phase 1 |
```

- **Files In Scope**: The COMPLETE list. No "e.g." or "such as". Every. Single. File.
- **Violation Pattern**: The exact Grep pattern to check this fix. This becomes the validation criterion.
- **Expected After Fix**: What the Grep should return (usually "zero matches")
- **Priority**: Map to REVIEW.md migration phases (Phase 0 = quick wins first)

### 1d — Present Manifest and Confirm

Present the manifest table to the user. State:
- Total fix units: N
- Total files affected: N
- Estimated phases: list phases and their fix unit counts

Ask: **"Here is the complete fix manifest with {N} fix units across {N} files. Should I proceed with all fixes, or would you like to select specific phases/units?"**

Wait for confirmation before proceeding.

## Step 2 — Execute Fixes Phase by Phase

Process fix units in phase order (Phase 0 → Phase 1 → Phase 2 → Phase 3).

### For Each Fix Unit:

#### 2a — Create Tracking Tasks

Use TaskCreate for each fix unit:
- **Subject:** `[Phase N] Fix: {fix unit title}`
- **Description:** Include the COMPLETE file list, the exact violation, the rule being enforced, and the expected pattern after fix
- **activeForm:** `Fixing: {fix unit title}`

#### 2b — Dispatch to Implementation Subagent

Before dispatching, read `ARCHITECTURE.md` and `CLAUDE.md` at the project root (if they exist). Include relevant sections in the subagent prompt so it understands project-specific conventions — not just generic rules.

Use the Task tool with the detected subagent_type. The prompt MUST include:

```
You are fixing a specific architecture review finding.

PROJECT CONTEXT:
{Paste relevant sections from ARCHITECTURE.md — tech stack, layer responsibilities, data flow}
{Paste any relevant project-specific instructions from CLAUDE.md}

FIX UNIT: {title}
CATEGORY: {category}
RULE VIOLATED: {quote the exact rule from the rules directory}

FILES TO MODIFY (you MUST modify ALL of these — do not skip any):
{complete file list, one per line}

VIOLATION PATTERN: {exact description of what's wrong}
EXPECTED RESULT: {what each file should look like after}

REFERENCE EXAMPLE:
{If any file in the project already follows the correct pattern, show it as a template}

INSTRUCTIONS:
1. Read each file in the list above
2. Apply the fix consistently using the same pattern
3. After modifying each file, confirm it follows the expected pattern
4. Report back which files you modified and any files you could NOT modify (with reason)

IMPORTANT:
- Do NOT skip files. The full list is provided — every file needs the fix.
- Follow the project's existing code style and patterns exactly.
- If a file doesn't actually have the violation (false positive from Grep), note it but move on.
```

#### 2c — Verify Subagent Output

After the subagent completes, immediately verify:

1. **File count check**: Did the subagent report modifying the same number of files as the manifest? If fewer, which ones were skipped?
2. **Grep re-check**: Re-run the violation pattern Grep. Are there still matches?
3. **Spot-check quality**: Read 1-2 modified files to confirm the fix follows project patterns (no black boxes).

**For fix units that involve writing or modifying tests**, apply additional verification:

4. **Tests pass**: Run the test suite (`uv run pytest` / `pnpm vitest run`) and confirm zero failures among the new/modified tests. A test that exists but fails is worse than no test — it blocks CI.
5. **Test coverage completeness**: For each source module the tests are supposed to cover, verify:
   - At least 1 happy-path test AND 1 error-path test per public service method
   - Every FSM transition tested (valid AND invalid) if FSMs exist
   - Every custom validator tested if schemas were modified
   - Use Grep to enumerate public methods (`def ` in services, `async def ` in routers) and cross-reference against test function names
6. **Test naming convention**: Grep new test files for function names. They must follow `test_<action>_<scenario>_<expected_outcome>`. Flag any `test_1`, `test_create`, `test_it_works` style names.
7. **Test structure**: Spot-check 1-2 new test files for AAA pattern (look for `# Arrange` / `# Act` / `# Assert` comments or clear visual separation).

If tests fail or coverage is incomplete:
- Re-dispatch subagent with specific instructions: "These tests fail: {list}. These methods lack tests: {list}. Fix/add them."
- Re-run tests to confirm (max 1 retry)

If the subagent missed files:
- Log which files were missed
- Re-dispatch a focused subagent call for ONLY the missed files
- Verify again (max 1 retry per fix unit)

#### 2d — Update Task Status

- If verified: Mark task as completed
- If partially done after retry: Mark as completed with a note about remaining files

### Between Phases — Run Tooling Gate

After completing all fix units in a phase, run the project's code quality tooling as a hard gate. These tools are the **source of truth** — they catch issues that Grep heuristics miss.

Detect which tooling suite to run based on project type:

**Python/FastAPI:**
```bash
uv run pyright .
uv run ruff check . --fix
uv run ruff format .
uv run bandit -r src/ -c pyproject.toml
uv run lint-imports
uv run radon cc src/ -a -nc
```

**Next.js:**
```bash
pnpm tsc --noEmit
pnpm eslint . --fix
pnpm prettier --write .
pnpm vitest run
```

**Vite/React:**
```bash
pnpm tsc --noEmit
pnpm eslint . --fix
pnpm prettier --write .
pnpm vitest run
```

If any tool reports errors:
1. Parse the errors and map them back to fix units from this phase
2. Fix the errors (dispatch subagent if needed, or apply auto-fixes like `ruff --fix` / `eslint --fix`)
3. Re-run the failing tool to confirm resolution
4. Only proceed when all tools pass

**Note:** Some tools may not be installed yet in the project. If a tool command fails with "not found", skip it and note it in the fix log. Do not install tools yourself — flag it as a migration plan item.

### Phase Checkpoint

After the tooling gate passes, report to the user:
```
Phase {N} complete: {X}/{Y} fix units fully verified.
Tooling gate: ✅ all checks pass / ⚠️ {N} issues fixed by auto-formatter / ❌ {N} issues need attention
{List any partial fixes with details}
Proceeding to Phase {N+1} with {Z} fix units. Continue?
```

Wait for confirmation before proceeding to the next phase.

## Step 3 — Update REVIEW.md

After all phases are complete, update `REVIEW.md`:

### 3a — Update Finding Statuses

For each finding row in the Detailed Findings tables, append a status:
- Findings where the Grep re-check shows zero remaining violations: add `✅ Fixed` to the Recommendation column
- Findings with partial fixes: add `⚠️ Partial — {N} files remaining` to the Recommendation column
- Findings not addressed (Phase 3 / deferred): leave unchanged

### 3b — Update Migration Plan Checkboxes

- Check completed items: `- [ ]` → `- [x]`
- Add notes to partial items: `- [ ] {item} — ⚠️ {N} files remaining`

### 3c — Add Fix Summary Header

Add below the date line in REVIEW.md:
```markdown
**Last fixed:** {today's date} — {N}/{M} findings resolved, {X}/{Y} migration items completed
```

### 3d — Update Executive Summary

Recalculate conformance levels based on remaining unresolved findings.

## Step 4 — Generate Fix Report

Write `REVIEW_FIX_LOG.md` at the project root:

```markdown
# Fix Log — {project_name}

**Date:** {today's date}
**Based on:** REVIEW.md dated {review date}

## Summary

| Phase | Fix Units | Fully Fixed | Partial | Files Modified |
|-------|-----------|-------------|---------|----------------|
| Phase 0 | N | N | N | N |
| Phase 1 | N | N | N | N |
| Phase 2 | N | N | N | N |
| **Total** | N | N | N | N |

## Fix Details

### Fix Unit 1: {title}
- **Files modified:** {list}
- **Verification:** ✅ Grep returns 0 matches / ⚠️ {N} files still have issues
- **Files skipped (if any):** {list with reasons}

### Fix Unit 2: ...

## Remaining Issues (if any)
{List anything not fully resolved, with file names and what's still wrong}

## Next Steps
- Run `/validate-review` to perform a comprehensive validation pass
- {Any manual steps needed for Phase 3 items}
```

## Step 5 — Report to User

Summarize:
1. Total fix units processed and completion rate
2. Files modified count
3. Any remaining issues
4. Recommend running `/validate-review` for a full independent verification
