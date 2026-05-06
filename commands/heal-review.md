# Heal Architecture Review Gaps

You are a review healing **orchestrator**. Your job is to fix remaining gaps identified in `REVIEW_VALIDATION.md` using a self-healing loop: implement fixes via specialized subagents, then validate each fix, and rework if validation fails.

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are an orchestrator, not an implementer. ALL code changes MUST be delegated to a subagent via the `Task` tool with the correct `subagent_type` (detected in Step 1).

Your only allowed actions:
- **Read** files (to understand context, verify fixes)
- **Grep/Glob** (to scan for patterns, validate results)
- **Bash** (to run tooling — linters, tests, formatters)
- **Task** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)
- **Write** (ONLY for `REVIEW.md` and `REVIEW_VALIDATION.md` — never source code)

If you catch yourself about to use Edit/Write on a `.py`, `.ts`, `.tsx`, `.dart`, or any source file — STOP and dispatch a subagent instead.

## Step 0 — Pre-flight Checks

1. Read `REVIEW_VALIDATION.md` at the project root. If it doesn't exist, tell the user to run `/validate-review` first and stop.
2. Read `REVIEW.md` to get the original findings and full context.
3. Read `FIX_PLAN.md` (if it exists) to recover the original HOW TO FIX instructions. When a gap corresponds to a fix unit in FIX_PLAN.md, reuse those instructions in the subagent prompt — they were already detailed and reviewed. If the original instructions failed, refine them based on the validation feedback (what specifically went wrong).
4. If the verdict in REVIEW_VALIDATION.md is "ALL CLEAR", tell the user there's nothing to heal and stop.
5. Parse the **Remaining Gaps** section to build the full gap list.

## Step 0b — Scope Selection

The user may provide arguments to select specific gaps. Parse the arguments:

**Supported formats:**
- `Gap 1` or `Gap1` or `1` → heal only Gap 1
- `Gap 1, Gap 3, Gap 5` or `1, 3, 5` → heal specific gaps
- `Gap 1-3` or `1-3` → heal gaps 1 through 3
- No arguments → show the gap list and ask the user to choose

**If no arguments were provided**, present a summary of all gaps and ask:

```
Found {N} remaining gaps:

| # | Gap | Category | Files | Estimated Effort |
|---|-----|----------|-------|-----------------|
| 1 | Services bypass repositories | Architecture | 17 files | High |
| 2 | Raw string status assignments | State & Enums | 8 locations | Low |
| 3 | Zero service-layer unit tests | Testing | 20 services | High |
| ...

Which gaps should I heal? (e.g., "2, 5" for quick wins, "1-3" for a range, or "all" for everything)
```

**Effort estimation:**
- **Low**: < 5 files, mechanical change (e.g., replace string with enum, add return type)
- **Medium**: 5-15 files, or requires creating new files (e.g., add test files, split a module)
- **High**: 15+ files, or requires architectural changes (e.g., move ORM calls from services to repos, migrate to TanStack Query)

Recommend starting with **Low effort gaps** for quick wins before tackling High effort ones. If the user selects a High effort gap, warn: "Gap {N} affects {X} files and requires significant changes. This may be a long session. Proceed?"

After the user selects, filter the work queue to only the selected gaps and proceed.

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

If `.shipboard.yml` exists in the repo root and `.mcp.json` registers `shipboard`:

1. Read `.shipboard.yml`; extract `component.name`.
2. Call:
   ```
   shipboard(action="report_lifecycle_stage",
             component=<component.name>,
             stage="verify_iterate",
             sub_state="heal",
             source="heal-review",
             pr_number=<if known, else null>)
   ```
3. On failure (no MCP, server down, network error), append a one-line JSON entry to `.shipboard/pending_events.log` and continue. Reporting is best-effort — it MUST NOT block the actual command execution.

If `.shipboard.yml` does not exist, skip this step silently (the user hasn't run `/init-component` yet — fine; the harness still works).

## Step 1 — Detect Project Type and Select Subagent

Detect the project type and select the implementation subagent by matching to the custom agent definitions in `~/.claude/agents/`:

| Project Detection | subagent_type | Agent Definition File |
|---|---|---|
| `pyproject.toml` contains `fastapi` in dependencies | `python-fastapi` | `~/.claude/agents/python-fastapi.md` |
| `next.config.ts` / `next.config.js` / `next.config.mjs` exists | `react-nextjs` | `~/.claude/agents/react-nextjs.md` |
| `vite.config.ts` / `vite.config.js` exists | `vite-react` | `~/.claude/agents/vite-react.md` |
| `pubspec.yaml` contains `flutter` in dependencies | `flutter` | `~/.claude/agents/flutter.md` |
| Python project with MCP server patterns | `python-mcp-expert` | `~/.claude/agents/python-mcp-expert.md` |
| Other Python project | `general-purpose` | (built-in, no custom agent file) |
| Other JS/TS project | `general-purpose` | (built-in, no custom agent file) |

**Mixed projects**: detect ALL matching project types and record them. You will use different subagent types for different gaps based on which files are affected.

**Mixed project dispatch protocol:**
1. Tag each gap with its target: `backend` (`.py` files) or `frontend` (`.ts`/`.tsx` files) or `shared` (docs, configs)
2. Backend gaps → dispatch with the backend subagent (e.g., `python-fastapi`)
3. Frontend gaps → dispatch with the frontend subagent (e.g., `react-nextjs` or `vite-react`)
4. **NEVER** send `.tsx`/`.ts` files to a Python agent or `.py` files to a React agent
5. In the gap summary table (Step 0b), add an **Agent** column showing which subagent_type will handle each gap

Verify the selected agent files exist by reading them. If missing, fall back to `general-purpose` and warn the user.

## Step 2 — Create Task Plan

Using the TaskCreate tool, create tasks for the healing work. For each **selected** gap (from Step 0b scope), create **two tasks**:

### Task A — Implementation (per gap)
- **Subject:** `[FIX] {gap short title}`
- **Description:** Include:
  - The original finding from REVIEW.md
  - The current state from REVIEW_VALIDATION.md
  - The specific remaining work needed
  - The explicit list of files to modify
  - The relevant rule(s) being violated (quote them)
  - Instruction: "Apply the fix to ALL listed files. Do not skip any."
- **activeForm:** `Fixing {gap short title}`

### Task B — Validation (per gap)
- **Subject:** `[VALIDATE] {gap short title}`
- **Description:** Include:
  - What was supposed to be fixed
  - How to verify: specific Grep/Glob patterns to run
  - Expected result: zero matches for violation patterns
  - Instruction: "If validation fails, report which files still have issues so the fix task can be re-run."
- **activeForm:** `Validating {gap short title}`
- **blockedBy:** the corresponding Task A

Group related gaps when they share the same files or pattern (e.g., "missing type annotations" across 10 files = 1 fix task + 1 validate task, not 10 pairs).

**Max batch size**: If a gap affects more than 8 files, split into multiple fix tasks of 5-8 files each. Large batches cause subagents to skip files.

**Test files in scope**: If the gap exists in test files too (e.g., raw string enums in test fixtures), include them in the fix task.

**Micro-fixes get their own batch**: Trivial 1-5 line changes (adding a type annotation, replacing a string with an enum, adding `Final[T]`, removing `# type: ignore`) should be grouped into a dedicated micro-fix task, separate from larger architectural changes. These mechanical changes get lost when mixed with complex multi-file refactors.

**Two-step fixes need sequencing**: When a fix requires creating something new before updating existing code (e.g., "create a repository method, then update the service to call it"), split into two sequential fix tasks with explicit dependency. Never combine "create X" and "update Y to use X" in a single subagent dispatch.

After creating all tasks, present the task list to the user and ask: **"I've created {N} fix tasks and {N} validation tasks for the {N} remaining gaps. Ready to start the healing loop?"**

Wait for user confirmation before proceeding.

## Step 3 — Execute Healing Loop

Process tasks in order. For each gap:

### 3a — Implementation (MANDATORY subagent delegation — do NOT implement yourself)

**REMINDER: You MUST use the Task tool here. Do NOT edit source files directly. You are the orchestrator — the subagent does the coding.**

- Before dispatching, read `ARCHITECTURE.md` and `CLAUDE.md` at the project root (if they exist) to gather project-specific context.
- Use the Task tool with the detected `subagent_type` from Step 1 to execute the fix
- The subagent prompt must include:
  - Relevant project context from ARCHITECTURE.md (tech stack, layer responsibilities, patterns)
  - Any project-specific instructions from CLAUDE.md
  - The full gap description from the task
  - The project's rules context (reference the rules directory path: `C:\Users\MatthieuBoujonnier\.claude\rules\`)
  - **HOW TO FIX**: Concrete, unambiguous step-by-step transformation instructions. NOT "fix the issue" but specific code changes.
    **Python examples:** "Replace `import X` with `import Y`", "Move function Z to file W", "Change `except E: log` to `except E: raise`", "Replace `data: dict` with `data: ItemCreate`"
    **React/TS examples:** "Replace `process.env.NEXT_PUBLIC_API_URL` with `import { env } from '@/lib/env'`", "Extract useState+useEffect fetch into `useApiQuery()`", "Add `error.tsx` with Error component", "Replace `as any` with proper typed interface"
    For two-step fixes (create then update), number steps explicitly: "Step 1: CREATE method X in repo. Step 2: UPDATE service to CALL method X."
  - **For file splitting**: Include a SPLIT PLAN with exact target filenames and what moves where. State: "The original file MUST be shorter after splitting. If it's the same length or longer, the split failed. Every extracted file must also be under 200 lines."
  - Explicit instruction: "Fix ALL files listed. Apply the pattern consistently. Do not leave any file unmodified. Do NOT add wrapper code or extra abstractions — apply the direct fix."
- Mark Task A as in_progress, then completed when the subagent finishes

### 3b — Validation
- After the implementation subagent completes, validate the fix yourself (do NOT delegate validation to the same subagent that did the fix)
- Use Grep/Glob/Read to verify the violation pattern no longer appears in ANY file
- Check that the fix follows the project's established patterns (no black boxes)
- **Regression check**: For file-splitting gaps, verify the file is SHORTER than before AND all extracted files are under 200 lines. If it grew, or an extracted file exceeds 200 lines, the fix failed.
- **Two-step wiring check**: For fixes that create new code and update callers, verify BOTH sides: (a) the new code exists, (b) the caller actually uses it. A common failure mode is creating the new method but not wiring the caller.
- **No new violations**: Grep modified files for new anti-patterns (`Any`, `# type: ignore`, bare `except:`, `print()`)
- Mark Task B as in_progress during validation

### 3b.1 — Cross-Gap Interference Check

After validating Gap N, re-run the grep patterns from ALL previously-healed gaps (Gap 1 through Gap N-1). This catches the scenario where healing Gap 3 undoes Gap 1's fix — e.g., a service refactor reintroduces raw strings that Gap 1 had replaced with enums.

**Procedure:**
1. Maintain a `healed_patterns` list: `[{gap_id, grep_pattern, expected_matches}]`
2. After each successful validation, add the current gap's pattern to the list
3. Re-run ALL patterns in the list against the codebase
4. If any previously-healed pattern now fails (matches > expected):
   - Log: `"⚠️ Cross-gap regression: Gap {X} re-broken by Gap {N} fix"`
   - Re-dispatch a targeted fix for ONLY the regressed gap's affected files
   - Re-validate the regressed gap (max 1 retry)
   - If still broken after retry, log as `"Cross-gap conflict — needs manual resolution"` and continue
5. If all prior patterns still pass, proceed to the next gap

This check is fast (just grep) but catches the most insidious failure: fixes that interfere with each other across gaps.

### 3c — Rework if Needed (max 2 rework cycles per gap)
- If validation **passes**: Mark Task B as completed. Move to the next gap.
- If validation **fails**:
  - Create a new rework Task A' with the specific files that still have issues
  - Re-run the implementation subagent with a more specific prompt listing exactly what's still wrong
  - Re-validate
  - If it fails again after 2 rework cycles, mark as unresolved and move on

**IMPORTANT**: Track the rework count. Never loop more than 2 times per gap. If still failing, log it as unresolved and continue.

## Step 4 — Update Review Documents

After all gaps are processed:

### Update REVIEW.md
- For each finding that was fully healed, update its severity to `✅ Resolved` in the findings table
- For migration plan items that were completed, check the checkbox `- [x]`
- Add a note at the top: `**Last healed:** {today's date} — {N}/{M} gaps resolved`
- Do NOT remove or rewrite findings — only update their status

### Update REVIEW_VALIDATION.md
- Re-run the validation summary counts
- Update the verdict
- Mark healed gaps as resolved in the Remaining Gaps section
- For unresolved gaps (if any), keep them with a note: `Unresolved after 2 rework cycles — requires manual intervention`

## Step 5 — Final Report

Write a summary to the user:

```
## Healing Complete

| Metric | Count |
|--------|-------|
| Gaps processed | N |
| ✅ Successfully healed | N |
| ❌ Unresolved (needs manual fix) | N |
| Rework cycles used | N |
| Files modified | N |

### Healed
1. {gap title} — {files changed}
2. ...

### Unresolved (if any)
1. {gap title} — {why it failed, what to check manually}
2. ...

### Recommendation
{If all healed: "Run `/validate-review` one final time to confirm everything is clean."}
{If unresolved remain: "N gaps need manual attention. After fixing them, run `/validate-review` to confirm."}
```
