# Implement Phase from Release Plan

You are a phase implementation **orchestrator**. Your job is to execute a specific phase from an existing `IMPLEMENTATION_PLAN.md`, verify completion against the plan, and update the plan status.

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are an orchestrator, not an implementer. ALL code changes MUST be delegated to a subagent via the `Task` tool with the correct `subagent_type`.

Your only allowed actions:
- **Read** files (to understand context, verify output)
- **Grep/Glob** (to scan codebase, verify files exist)
- **Bash** (to run tooling gates, tests)
- **Task** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)
- **Write** (ONLY for `IMPLEMENTATION_PLAN.md` and `IMPLEMENTATION_STATUS.md` — never source code)

## Step 0 — Pre-flight

1. **Parse arguments**: The user provides a phase number (e.g., `/implement-phase 2`). If no phase specified, ask which phase to implement.

2. **Read `IMPLEMENTATION_PLAN.md`** at the project root. If it doesn't exist, tell the user: "No IMPLEMENTATION_PLAN.md found. Run `/plan-release` first to create a release plan." and stop.

3. **Parse the plan**: Extract:
   - Total phases and their descriptions
   - The target phase's tasks/features
   - Dependencies (does this phase depend on earlier phases being done?)
   - Files to create and modify for this phase

4. **Check phase dependencies**: If this phase depends on earlier phases, verify those are marked complete in the plan. If not, warn: "Phase {N} depends on Phase {M} which is not complete. Proceed anyway?" Wait for confirmation.

5. **Detect project type** (same logic as other commands: `pyproject.toml` with fastapi, `next.config.*`, `pubspec.yaml` with flutter, etc.)

6. **Read project context**: `ARCHITECTURE.md`, `CLAUDE.md`, `decisions.md` (if they exist)

## Step 1 — Present Phase Summary

Show the user what will be implemented:

```
## Phase {N}: {phase title}

**Dependencies:** Phase {M} (✅ complete / ⚠️ incomplete)
**Tasks:** {count}
**Files to create:** {count}
**Files to modify:** {count}

### Tasks in this phase:
1. {task description}
2. {task description}
...

**Agent(s):** {subagent_type(s) needed}

Proceed with implementation?
```

Wait for confirmation.

## Step 2 — Execute Phase Tasks

For each task in the phase:

### 2a — Create Tracking Task

Use TaskCreate:
- **Subject:** `[Phase {N}] {task title}`
- **Description:** Full task spec from the plan
- **activeForm:** `Implementing: {task title}`

### 2b — Dispatch to Subagent (MANDATORY)

**REMINDER: You MUST use the Task tool. Do NOT edit source files directly.**

Select subagent by file types:

| Files Affected | subagent_type |
|---|---|
| `.py` files (FastAPI) | `python-fastapi` |
| `.ts/.tsx` files (Next.js) | `react-nextjs` |
| `.ts/.tsx` files (Vite) | `vite-react` |
| `.dart` files (Flutter) | `flutter` |
| MCP server files | `python-mcp-expert` |
| Other | `general-purpose` |

The subagent prompt MUST include:
- Project context from ARCHITECTURE.md / CLAUDE.md
- Full task specification from the plan
- Files to create/modify
- Constraints for the detected project type (same as `/plan-release`)
- Instructions to run tooling and tests after implementing
- **Explicit typing reminders** (include verbatim in prompt):
  - "Never use `Map<String, Object?>` or `Map<String, dynamic>` for form data, wizard results, or summary fields — always define a typed data class."
  - "Never compare status/state values using raw strings — always use enum-backed comparisons."
  - "Run the project linter (`ruff check`/`dart analyze`/`eslint`) BEFORE returning your result — fix any violations inline."
  - "Test files must stay under 300 lines — split by concern if needed."

### 2c — Verify Task Output

After each task completes:
1. **File check**: Glob for expected files — were they all created?
2. **Tooling gate**: Run type checker, linter
3. **Spot-check**: Read 1-2 files to verify they follow project patterns
4. **Mark task complete** or flag partial

### 2d — Between Tasks

Report progress:
```
Task {X}/{Y} complete: {task title}
- Files created: {list}
- Tooling: ✅ pass / ❌ {errors}

Continuing to next task...
```

## Step 3 — Phase Tooling Gate

After all tasks in the phase, run the full tooling suite:

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

Verify the phase against the plan:

### 4a — Task Completion Check

For each task in the plan:
- **Files created**: Glob to verify all expected files exist
- **Files modified**: Check the files were actually changed (git diff or content inspection)
- **Tests exist**: For each new module, verify corresponding test file exists
- **Tests pass**: All new tests should be green

### 4a.1 — Service Size Verification (Python/FastAPI)

For Python projects, check that no service file exceeds limits:

```bash
wc -l services/*.py  # All should be under 200 lines
```

If ANY service file exceeds 200 lines:
1. Flag as 🔴 CRITICAL — "Service {name} is {N} lines (limit: 200)"
2. **Do not proceed** until the subagent splits it into focused sub-services
3. Re-dispatch with explicit instruction: "Split {service} into {responsibility1}_service.py, {responsibility2}_service.py"

Also check method count:
```bash
grep -c "def " services/foo_service.py  # Should be under 15 total (public + private)
```

### 4a.2 — Test Companion Verification (Flutter)

For Flutter projects, explicitly verify test companions exist for presentation layer:

| Source File Created | Required Test File |
|--------------------|--------------------|
| `features/foo/presentation/providers/foo_list_provider.dart` | `test/features/foo/presentation/providers/foo_list_provider_test.dart` |
| `features/foo/presentation/providers/foo_detail_provider.dart` | `test/features/foo/presentation/providers/foo_detail_provider_test.dart` |
| `features/foo/presentation/pages/foo_list_page.dart` | `test/features/foo/presentation/pages/foo_list_page_test.dart` |
| `features/foo/presentation/pages/foo_detail_page.dart` | `test/features/foo/presentation/pages/foo_detail_page_test.dart` |

**If ANY presentation test file is missing, flag as ⚠️ PARTIAL and add to gaps.**

This prevents the common failure mode where implementation is "done" but tests are completely absent.

### 4b — Build Verification Checklist

Create a checklist of everything the phase was supposed to deliver:

```
### Phase {N} Verification Checklist

| Item | Status | Notes |
|------|--------|-------|
| Create `domain/entities/foo.dart` | ✅ | 45 lines, follows @freezed pattern |
| Create `data/models/foo_dto.dart` | ✅ | Has toEntity() mapper |
| Create `presentation/pages/foo_page.dart` | ⚠️ | Created but missing error handling |
| Add tests for FooUseCase | ❌ | Test file not created |
| Update `ARCHITECTURE.md` | ✅ | New feature documented |
```

### 4c — Gap Detection

If any items are ⚠️ PARTIAL or ❌ MISSING:
1. List the specific gaps
2. Re-dispatch a targeted subagent for ONLY the missing items (max 1 retry)
3. Re-verify after retry
4. If still incomplete, log as partial

## Step 5 — Update Plan Status

### 5a — Update `IMPLEMENTATION_PLAN.md`

Mark this phase's tasks with completion status:
- `- [x]` for completed tasks
- `- [~]` for partial tasks (with note)
- `- [ ]` for incomplete tasks

Add a status header to the phase:
```markdown
## Phase {N}: {title}
**Status:** ✅ Complete / ⚠️ Partial ({X}/{Y} tasks) / ❌ Incomplete
**Completed:** {date}
```

### 5b — Write/Update `IMPLEMENTATION_STATUS.md` (MANDATORY)

**You MUST write this file.** This is not optional. Use the Write tool to create or update `IMPLEMENTATION_STATUS.md` at the project root.

If the file exists, read it first, then update the Progress Summary table and append the new phase section. If it doesn't exist, create it with the full structure below:

```markdown
# Implementation Status — {project_name}

**Last updated:** {date}
**Plan:** IMPLEMENTATION_PLAN.md

## Progress Summary

| Phase | Status | Tasks | Completion |
|-------|--------|-------|------------|
| Phase 1: {title} | ✅ Complete | 5/5 | 100% |
| Phase 2: {title} | ✅ Complete | 4/4 | 100% |
| Phase 3: {title} | 🔄 In Progress | 3/6 | 50% |
| Phase 4: {title} | ⏳ Pending | 0/4 | 0% |

**Overall:** {X}/{Y} tasks complete ({Z}%)

---

## Phase {N} — {title}

**Implemented:** {date}
**Agent:** {subagent_type}
**Tooling:** ✅ All pass / ⚠️ {N} warnings / ❌ {N} errors

### Completed
- ✅ {task 1} — {files created/modified}
- ✅ {task 2} — {files created/modified}

### Partial (needs attention)
- ⚠️ {task 3} — {what's missing}

### Skipped/Failed
- ❌ {task 4} — {reason}

### Files Created
- `path/to/file1.dart` (45 lines)
- `path/to/file2.dart` (32 lines)

### Files Modified
- `path/to/existing.dart` — added {what}

### Tests Added
- `test/path/file1_test.dart` — 5 tests, all passing
- `test/path/file2_test.dart` — 3 tests, all passing

### Verification Checklist
| Item | Status |
|------|--------|
| All files created | ✅ |
| All tests passing | ✅ |
| Tooling clean | ✅ |
| Follows project patterns | ✅ |
| ARCHITECTURE.md updated | ✅ |

---

## Next Phase Preview

**Phase {N+1}: {title}**
- {task count} tasks
- Dependencies: Phase {N} ✅
- Ready to start

---

## Gaps Requiring Attention

{List any ⚠️ or ❌ items that need manual intervention or another heal pass}

### Gap 1: {title}
- **Phase:** {N}
- **Task:** {task description}
- **Missing:** {specific files or functionality}
- **Action needed:** {what to do}
```

## Step 6 — Report to User

**Before reporting, verify you completed Step 5b** — the `IMPLEMENTATION_STATUS.md` file MUST exist and be updated before you show this summary to the user.

Summarize the phase:

```
## Phase {N} Implementation Complete

**Status:** ✅ Complete / ⚠️ Partial
**Tasks:** {X}/{Y} complete
**Files created:** {count}
**Files modified:** {count}
**Tests:** {count} added, all passing
**Tooling:** ✅ All checks pass

### What was done:
{Brief summary of implemented functionality}

### Gaps (if any):
{List any partial/missing items}

### Next steps:
1. Run `/check` to verify no architectural violations
2. Commit: `git add . && git commit -m "feat: {phase summary}"`
3. Run `/implement-phase {N+1}` for the next phase

IMPLEMENTATION_STATUS.md has been updated with full details.
```
