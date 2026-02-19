# Heal Architecture Review Gaps

You are a review healing orchestrator. Your job is to fix remaining gaps identified in `REVIEW_VALIDATION.md` using a self-healing loop: implement fixes via specialized subagents, then validate each fix, and rework if validation fails.

## Step 0 — Pre-flight Checks

1. Read `REVIEW_VALIDATION.md` at the project root. If it doesn't exist, tell the user to run `/validate-review` first and stop.
2. Read `REVIEW.md` to get the original findings and full context.
3. If the verdict in REVIEW_VALIDATION.md is "ALL CLEAR", tell the user there's nothing to heal and stop.
4. Parse the **Remaining Gaps** section to build the full gap list.

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

**Mixed projects**: use different subagent types for different gaps based on which files are affected.

Verify the selected agent file exists by reading it. If missing, fall back to `general-purpose` and warn the user.

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

After creating all tasks, present the task list to the user and ask: **"I've created {N} fix tasks and {N} validation tasks for the {N} remaining gaps. Ready to start the healing loop?"**

Wait for user confirmation before proceeding.

## Step 3 — Execute Healing Loop

Process tasks in order. For each gap:

### 3a — Implementation
- Before dispatching, read `ARCHITECTURE.md` and `CLAUDE.md` at the project root (if they exist) to gather project-specific context.
- Use the Task tool with the detected subagent_type to execute the fix
- The subagent prompt must include:
  - Relevant project context from ARCHITECTURE.md (tech stack, layer responsibilities, patterns)
  - Any project-specific instructions from CLAUDE.md
  - The full gap description from the task
  - The project's rules context (reference the rules directory path: `C:\Users\MatthieuBoujonnier\.claude\rules\`)
  - Explicit instruction: "Fix ALL files listed. Apply the pattern consistently. Do not leave any file unmodified."
- Mark Task A as in_progress, then completed when the subagent finishes

### 3b — Validation
- After the implementation subagent completes, validate the fix yourself (do NOT delegate validation to the same subagent that did the fix)
- Use Grep/Glob/Read to verify the violation pattern no longer appears in ANY file
- Check that the fix follows the project's established patterns (no black boxes)
- Mark Task B as in_progress during validation

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
