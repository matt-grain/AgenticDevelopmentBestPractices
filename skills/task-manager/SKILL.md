---
name: task-manager
description: Create and manage tasks visible in the Claude Code task viewer. Use this skill when you need to track progress on multi-step work, create task lists, or update task status. Essential when the built-in TaskCreate/TaskUpdate tools are not available.
allowed-tools: Bash(python *), Bash(pip install *)
---

# Task Manager

Manage tasks displayed in the Claude Code task viewer by reading/writing the same JSON files the built-in TaskCreate/TaskUpdate tools use.

## Setup (first time only)

```bash
pip install filelock
```

## Session ID

**CRITICAL**: Always pass the conversation session ID so the task viewer can display the project name, slug, and git branch instead of a raw UUID.

The current session ID is: `${CLAUDE_SESSION_ID}`

All commands below must include `--session-id ${CLAUDE_SESSION_ID}`.

When delegating to subagents, pass the session ID in the prompt so they can use it too.

## CLI location

```
~/.claude/skills/task-manager/scripts/task_manager.py
```

Shorthand used below: `TM="python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id ${CLAUDE_SESSION_ID}"`

## Commands

### Create a task

```bash
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id ${CLAUDE_SESSION_ID} create \
  --subject "Fix authentication bug" \
  --description "Detailed description of what needs to be done" \
  --active-form "Fixing authentication bug"
```

- `--subject` (required): Task title in imperative form (e.g., "Run tests")
- `--description`: Detailed description of what needs to be done
- `--active-form`: Present continuous form shown in the spinner while task is in_progress (e.g., "Running tests")

### Update a task

```bash
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id ${CLAUDE_SESSION_ID} update <task_id> \
  --status in_progress
```

- `<task_id>` (required): The task ID to update
- `--status`: One of `pending`, `in_progress`, `completed`, `deleted`
- `--subject`: New task title
- `--description`: New description
- `--active-form`: New spinner text
- `--add-blocks`: Comma-separated task IDs this task blocks (e.g., "2,3")
- `--add-blocked-by`: Comma-separated task IDs that block this task (e.g., "1")

### Get a task

```bash
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id ${CLAUDE_SESSION_ID} get <task_id>
```

### List all tasks

```bash
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id ${CLAUDE_SESSION_ID} list
```

## Orchestrating sequential tasks with subagents

The `blocks`/`blockedBy` fields are **metadata for the viewer** — they show dependency arrows but do NOT enforce execution order. **You (the main agent) must orchestrate the sequencing.**

### Pattern: Sequential tasks with different models

To run Task #1 (Sonnet) then Task #2 (Haiku) where #2 depends on #1's output:

**Step 1 — Create both tasks with dependency metadata:**

```bash
# Create tasks
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID create \
  --subject "Research topic" --active-form "Researching topic"
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID create \
  --subject "Summarize findings" --active-form "Summarizing findings"

# Set dependency: #1 blocks #2
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 1 --add-blocks 2
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 2 --add-blocked-by 1
```

**Step 2 — Mark #1 in_progress, launch Sonnet subagent:**

```bash
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 1 --status in_progress
```

Then use the Task tool to spawn a Sonnet subagent. In the subagent prompt, include:
- The session ID so the subagent can update task status
- Instructions to write output to a shared file (e.g., `/tmp/task1_result.txt`)
- Instructions to mark the task completed when done:
  `python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 1 --status completed`

**Step 3 — Wait for Sonnet to finish, then launch Haiku:**

After the Sonnet subagent returns, mark #2 in_progress and launch Haiku:

```bash
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 2 --status in_progress
```

Spawn a Haiku subagent with instructions to:
- Read the output from step 1 (e.g., `/tmp/task1_result.txt`)
- Do its work
- Mark task completed:
  `python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 2 --status completed`

### Pattern: Parallel tasks

For independent tasks that can run simultaneously, create them without dependencies and launch subagents in parallel:

```bash
# Create parallel tasks
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID create \
  --subject "Lint code" --active-form "Linting code"
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID create \
  --subject "Run tests" --active-form "Running tests"

# Mark both in_progress
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 1 --status in_progress
python ~/.claude/skills/task-manager/scripts/task_manager.py --session-id SESSION_ID update 2 --status in_progress
```

Then launch both subagents simultaneously using the Task tool.

### Pattern: Fan-out then merge

Create N parallel tasks that all block a final merge task:

```bash
# Create worker tasks
python ... create --subject "Worker A" --active-form "Running worker A"  # -> #1
python ... create --subject "Worker B" --active-form "Running worker B"  # -> #2
python ... create --subject "Merge results" --active-form "Merging results"  # -> #3

# #1 and #2 both block #3
python ... update 1 --add-blocks 3
python ... update 2 --add-blocks 3
python ... update 3 --add-blocked-by 1,2
```

Launch workers in parallel, wait for both, then launch the merge task.

## Important notes

- Tasks are stored as JSON files in `~/.claude/tasks/<session-uuid>/`
- The task viewer picks up changes in real time — no restart needed
- Status transitions: `pending` -> `in_progress` -> `completed`
- Use `--status deleted` to permanently remove a task
- Always provide `--active-form` when creating tasks (shown in the spinner UI)
- The `--subject` should be imperative ("Run tests") while `--active-form` should be present continuous ("Running tests")
- **Always pass `--session-id`** with the conversation session ID so the viewer shows the project name and slug instead of a raw UUID
