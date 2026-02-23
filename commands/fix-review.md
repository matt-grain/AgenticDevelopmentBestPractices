# Fix Architecture Review Findings

You are a review fix **orchestrator**. Your job is to systematically implement ALL fixes identified in `REVIEW.md` — with zero gaps. The key discipline: **expand every finding into a complete file manifest BEFORE writing any code**, then fix file-by-file with tracking.

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are an orchestrator, not an implementer. ALL code changes MUST be delegated to a subagent via the `Task` tool with the correct `subagent_type` (detected in Step 0).

Your only allowed actions:
- **Read** files (to understand context, build manifests, verify fixes)
- **Grep/Glob** (to scan for patterns, expand file lists, verify results)
- **Bash** (to run tooling gates — linters, tests, formatters)
- **Task** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)
- **Write** (ONLY for `REVIEW.md` and `REVIEW_FIX_LOG.md` — never source code)

If you catch yourself about to use Edit/Write on a `.py`, `.ts`, `.tsx`, `.dart`, or any source file — STOP and dispatch a subagent instead.

## Step 0 — Pre-flight Checks

1. Read `REVIEW.md` at the project root. If it doesn't exist, tell the user to run `/review-architecture` first and stop.
2. Check the `**Date:**` field in REVIEW.md. If it is older than 7 days, warn the user: "This review is from {date}. The codebase may have changed since then. Consider running `/review-architecture` for a fresh audit before fixing." Wait for confirmation before proceeding.
3. If `REVIEW_FIX_LOG.md` already exists, warn the user that a previous fix cycle was already run and ask if they want to continue (append to existing log) or start fresh.
4. Detect the project type (check for `pyproject.toml` with fastapi, `next.config.*`, `vite.config.*`, `pubspec.yaml` with flutter, `package.json`).
3. Select the implementation subagent by matching the project type to the custom agent definitions in `~/.claude/agents/`:

   | Project Detection | subagent_type | Agent Definition File |
   |---|---|---|
   | `pyproject.toml` contains `fastapi` in dependencies | `python-fastapi` | `~/.claude/agents/python-fastapi.md` |
   | `next.config.ts` / `next.config.js` / `next.config.mjs` exists | `react-nextjs` | `~/.claude/agents/react-nextjs.md` |
   | `vite.config.ts` / `vite.config.js` exists | `vite-react` | `~/.claude/agents/vite-react.md` |
   | `pubspec.yaml` contains `flutter` in dependencies | `flutter` | `~/.claude/agents/flutter.md` |
   | Python project with MCP server patterns | `python-mcp-expert` | `~/.claude/agents/python-mcp-expert.md` |
   | Other Python project | `general-purpose` | (built-in, no custom agent file) |
   | Other JS/TS project | `general-purpose` | (built-in, no custom agent file) |

   **Mixed projects** (e.g., FastAPI backend + React frontend): detect ALL matching project types and record them. You will use different subagent types for different fix units based on which files are affected.

   **Mixed project dispatch protocol:**
   1. Tag each fix unit with its target: `backend` (`.py` files) or `frontend` (`.ts`/`.tsx` files) or `shared` (docs, configs)
   2. Backend fix units → dispatch with the backend subagent (e.g., `python-fastapi`)
   3. Frontend fix units → dispatch with the frontend subagent (e.g., `react-nextjs` or `vite-react`)
   4. **NEVER** send `.tsx`/`.ts` files to a Python agent or `.py` files to a React agent — the agent will produce incorrect fixes
   5. In the manifest table (Step 1c), add an **Agent** column showing which subagent_type will handle each fix unit
   6. Run the backend tooling gate and frontend tooling gate separately after each phase

   Verify the selected agent files exist by reading them. If an agent file is missing, fall back to `general-purpose` and warn the user.

## Step 0b — Check for FIX_PLAN.md (recommended path)

Check if `FIX_PLAN.md` exists at the project root.

**If FIX_PLAN.md exists** (produced by `/plan-fix`):
1. Read `FIX_PLAN.md` — this is the pre-approved, detailed fix plan
2. Parse the fix units, phases, file lists, HOW TO FIX instructions, and agent assignments
3. Present a summary to the user: "Found FIX_PLAN.md with {N} fix units across {M} phases. Using this as the execution plan."
4. **Skip Step 1 entirely** — go directly to Step 0c (regression check) then Step 2 (execute)
5. The HOW TO FIX instructions in FIX_PLAN.md are already concrete — paste them directly into the subagent prompt

**If FIX_PLAN.md does NOT exist:**
1. Warn the user: "No FIX_PLAN.md found. Consider running `/plan-fix` first for a detailed, reviewable plan. Proceeding with on-the-fly manifest building."
2. Continue to Step 0c and Step 1 to build the manifest from scratch

Using `/plan-fix` first is **strongly recommended** because:
- The plan gets dedicated attention (not rushed as part of fix-review)
- You can review and edit `FIX_PLAN.md` before any code is touched
- Subagents receive detailed, pre-approved HOW TO FIX instructions
- The plan document serves as audit trail of what was done and why

## Step 0c — Regression Pre-flight (for repeat fix cycles)

If `REVIEW_FIX_LOG.md` exists (indicating a previous fix cycle), run a quick regression check before starting fixes:

1. Parse the previous fix log for items marked `✅ Grep returns 0 matches`
2. Re-run those Grep patterns now to check if any violations have returned
3. If regressions are found, report them:
   ```
   ⚠️ Regression detected: {N} previously-fixed items have re-appeared:
   - "Add -> None to __init__" — 5 files now missing it again (were fixed in last cycle)
   - "Replace raw string statuses" — 2 new raw strings in test files

   These will be included as Phase 0 fix units to re-fix before proceeding.
   ```
4. Add regressed items to the manifest/plan as **Phase 0** fix units with high priority
5. If no regressions found, proceed normally

This prevents the "fix it, break it, fix it again" loop where later phases undo earlier fixes.

## Step 1 — Build the Exhaustive Fix Manifest (skip if FIX_PLAN.md exists)

**If FIX_PLAN.md was found in Step 0b, skip this entire step and go to Step 2.**

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
| File splitting (file over 200 lines) | 1 unit per file to split — see File Splitting Protocol below |

**CRITICAL — Max batch size:** A single fix unit MUST NOT affect more than **8 files**. If a violation spans 20 files, split into multiple fix units of 5-8 files each (e.g., "Add type annotations — batch 1/3: files A-H", "batch 2/3: files I-P", "batch 3/3: files Q-T"). This prevents subagent overload and ensures each file actually gets fixed.

**CRITICAL — Test files are in scope:** When expanding file lists, include test files (`tests/`, `test_*.py`, `*_test.dart`, `*.test.tsx`) that have the same violation. Test fixtures with raw strings, hardcoded dicts, or wrong patterns must be fixed alongside production code.

**CRITICAL — One issue per fix unit:** Never bundle unrelated fixes into one unit even if they're in the same file. "Remove ORM imports from payment_service.py" and "Fix swallowed exception in payment_service.py" are TWO separate fix units — they require different reasoning and the subagent may succeed at one and fail at the other.

**CRITICAL — Micro-fixes get their own batch:** Trivial 1-5 line changes (adding a type annotation, replacing a string with an enum, adding `Final[T]`, removing a `# type: ignore`) MUST be grouped into a dedicated **"Phase 0 — Micro-fixes"** batch, separate from larger architectural changes. These are mechanical find-and-replace changes that get lost when mixed with complex multi-file refactors. Create one fix unit per violation type (e.g., "Add `Final[T]` to all module-level constants" as one unit, "Replace raw string statuses with enum" as another). Each micro-fix unit can include up to 8 files.

**CRITICAL — Two-step fixes need sequencing:** When a fix requires creating something new before updating existing code (e.g., "create a repository method, then update the service to call it"), the fix unit MUST be split into two sequential sub-units with explicit dependency:
- **Sub-unit A (Create):** "Create `calculate_total()` in `repositories/order_repo.py`" — dispatched first
- **Sub-unit B (Update):** "Update `services/order_service.py` to call `order_repo.calculate_total()` instead of inline SQL" — dispatched after A completes, with A's output as context
Never combine "create X" and "update Y to use X" in a single subagent dispatch — the subagent will often do the update but forget to create X, or create X but not wire it up correctly.

### 1c — Build the Manifest Table

Create a manifest with this structure:

```
| # | Fix Unit | Category | Files In Scope | Violation Pattern (Grep) | Expected After Fix | Priority | Agent |
|---|----------|----------|---------------|------------------------|-------------------|----------|-------|
| 1 | Add return type annotations (backend) | Typing | [list ALL .py files] | `def \w+\(.*\):\s*$` (no ->) | Zero matches | Phase 0 | python-fastapi |
| 2 | Replace process.env with lib/env.ts | Architecture | [list ALL .ts/.tsx files] | `process\.env\.` | Zero matches | Phase 0 | react-nextjs |
| 3 | Move DB queries from services to repos | Architecture | [list ALL .py files] | `Session` import in services/ | Zero matches | Phase 1 | python-fastapi |
```

- **Files In Scope**: The COMPLETE list. No "e.g." or "such as". Every. Single. File.
- **Violation Pattern**: The exact Grep pattern to check this fix. This becomes the validation criterion.
- **Expected After Fix**: What the Grep should return (usually "zero matches")
- **Priority**: Map to phases: **Phase 0 = micro-fixes** (1-5 line mechanical changes per file), Phase 1-3 = REVIEW.md migration phases

### File Splitting Protocol

For fix units that require splitting a large file (over 200 lines), the subagent prompt MUST include explicit splitting instructions. Do NOT just say "split this file" — the subagent will add code instead. Provide:

1. **Read the file first** and identify logical sections (by class, by domain entity, by responsibility)
2. **Define the exact target files** with their names and what moves where:
   ```
   SPLIT PLAN:
   - seed_demo.py (913 lines) → split into:
     - seed/orders.py (move lines 1-150: order seeding functions)
     - seed/inventory.py (move lines 151-300: inventory seeding functions)
     - seed/customers.py (move lines 301-400: customer seeding functions)
     - seed/__init__.py (import and re-export the main seed function)
   ```
3. **Specify import updates** — which other files import from the original and need updating
4. **State the constraint**: "After splitting, the ORIGINAL file must be SHORTER than before. If the original file is the same length or longer, the split failed."
5. **Extracted files must also respect the 200-line limit.** If moving 350 lines of code out, split into 2+ target files, not one large helper. Plan the split so that EVERY resulting file (original + all extracted) is under 200 lines.

**Regression guard**: For file-length fix units, record the BEFORE line count. After the subagent finishes, check the line count for ALL files (original AND extracted). If the original is equal or longer than before, OR if any extracted file exceeds 200 lines, the fix FAILED — re-dispatch with explicit instructions to MOVE code out (not add wrappers) and split extracted files further if needed.

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

#### 2b — Dispatch to Implementation Subagent (MANDATORY — do NOT implement yourself)

**REMINDER: You MUST use the Task tool here. Do NOT edit source files directly. You are the orchestrator — the subagent does the coding.**

Before dispatching, read `ARCHITECTURE.md` and `CLAUDE.md` at the project root (if they exist). Include relevant sections in the subagent prompt so it understands project-specific conventions — not just generic rules.

Use the Task tool with the detected `subagent_type` from Step 0. The prompt MUST include:

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

HOW TO FIX (step-by-step — follow this exactly):
{Provide concrete, unambiguous steps. NOT "fix the issue" but specific transformations.

 **Python/FastAPI examples:**
 - "Replace `from ..models.tenant import User` with `from ..schemas.users import UserOut`"
 - "Move the dict-building block (lines 91-104) into a `PaymentResponse.from_orm()` classmethod"
 - "Change `except InvalidTransitionError as e: logger.warning(...)` to `except InvalidTransitionError: raise`"
 - "Create file `seed/orders.py`, move functions X, Y, Z from seed_demo.py into it, update imports in seed_demo.py"
 - "Add `-> None` to the `__init__` method signature"
 - "Replace `data: dict` parameter with `data: ItemCreate` (Pydantic schema)"

 **React/Next.js examples:**
 - "Create `src/lib/env.ts` with `import { z } from 'zod'`, define schema for NEXT_PUBLIC_API_URL, export validated `env` object"
 - "Replace `process.env.NEXT_PUBLIC_API_URL` with `import { env } from '@/lib/env'` then `env.NEXT_PUBLIC_API_URL`"
 - "Extract the `useState` + `useEffect` fetch block (lines 19-38) into a `useApiQuery('/api/tenants')` call"
 - "Replace `const [data, setData] = useState(null); useEffect(() => fetch(...), [])` with `const { data } = useApiQuery<Tenant[]>('/api/tenants')`"
 - "Extract lines 56-120 (BackendUnavailableModal) into `src/components/BackendUnavailableModal.tsx` with a `BackendUnavailableModalProps` interface"
 - "Add `error.tsx` file in `app/(dashboard)/purchases/` exporting a default Error component that shows the error message and a retry button"
 - "Replace `(customer as any).orders` with proper type: add `orders?: Order[]` to the `Customer` interface in `types/sales.ts`"
 - "Move filter state from `useState` to URL params: replace `const [search, setSearch] = useState('')` with `const [search, setSearch] = useQueryState('q', { defaultValue: '' })` from nuqs"

 For TWO-STEP fixes (create then update), number the steps explicitly:
 - "Step 1: In `repositories/order_repo.py`, ADD method `calculate_total(order_id: int) -> Decimal` that runs the SQL query."
 - "Step 2: In `services/order_service.py`, REPLACE the inline SQL block (lines 45-60) with a call to `self.order_repo.calculate_total(order_id)`."
 - "Step 3: Verify both files compile — the service must import and call the new repo method."
}

INSTRUCTIONS:
1. Read each file in the list above
2. Apply the fix using the HOW TO FIX steps above — follow them exactly
3. After modifying each file, confirm it follows the expected pattern
4. Report back which files you modified and any files you could NOT modify (with reason)

IMPORTANT:
- Do NOT skip files. The full list is provided — every file needs the fix.
- Follow the project's existing code style and patterns exactly.
- If a file doesn't actually have the violation (false positive from Grep), note it but move on.
- NEVER add wrapper code, adapter layers, or extra abstractions to "solve" the issue — apply the direct fix described above.
```

#### 2c — Verify Subagent Output

After the subagent completes, immediately verify:

1. **File count check**: Did the subagent report modifying the same number of files as the manifest? If fewer, which ones were skipped?
2. **Grep re-check**: Re-run the violation pattern Grep. Are there still matches?
3. **Spot-check quality**: Read 1-2 modified files to confirm the fix follows project patterns (no black boxes).
4. **Regression check**: For file-length and file-splitting fix units, check that the target file is SHORTER than before. If it's the same length or longer, the fix failed — the subagent likely added wrapper code instead of moving code out. Re-dispatch with explicit move instructions. Also check that ALL extracted/new files are under 200 lines — if an extracted helper is 300+ lines, the split needs to go further.
5. **No new violations**: Quickly Grep the modified files for common anti-patterns introduced by fixes (new `Any` types, new `# type: ignore`, new bare `except:`, new `print()` calls). A fix that introduces new violations is not a fix.
6. **Two-step wiring check**: For fix units that create new code and update callers, verify BOTH sides: (a) the new code exists (Grep for the new function/method name), (b) the caller actually uses it (Grep the calling file for the new import/call). A common failure mode is creating the new method but not wiring the caller.

**For fix units that involve writing or modifying tests**, apply additional verification:

4. **Tests pass**: Run the test suite (`uv run pytest` / `pnpm vitest run` / `flutter test`) and confirm zero failures among the new/modified tests. A test that exists but fails is worse than no test — it blocks CI.
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

Detect which tooling suite to run based on project type. **For mixed projects, run BOTH backend and frontend tooling gates separately:**

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

**Flutter:**
```bash
dart analyze --fatal-infos
dart format --set-exit-if-changed .
dart run build_runner build --delete-conflicting-outputs  # if project uses code generation
flutter test
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
