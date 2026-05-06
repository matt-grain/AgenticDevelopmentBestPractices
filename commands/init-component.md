# Scaffold a New Component (Discovery Stage Entry Point)

You are a component-scaffolding **orchestrator**. Your job is to bootstrap a new ShipBoard-tracked component from scratch in the current working directory: initialize git, write the `.shipboard.yml` identity file, scaffold a `docs/` skeleton + `CLAUDE.md` + `ARCHITECTURE.md`, push the first lifecycle event to ShipBoard (best-effort), and produce one clean first commit on `main`.

This is the **only** harness command that creates a component from zero. Every subsequent harness command (`/plan-release`, `/plan-validate`, `/implement-phase`, `/check`, `/fix-check`, ...) reads `.shipboard.yml` to know which component it's reporting against.

## CRITICAL — Delegation Rule

**You MUST NOT write source code for the component being scaffolded.** This command produces *only* harness/config artifacts — `.shipboard.yml`, `.gitignore`, `docs/REQUIREMENTS.md` template, placeholder `MOCKUPS.md`/`SPECS.md`/`UI.md`, `CLAUDE.md`, `ARCHITECTURE.md`. Application code arrives later via `/plan-release` → `/implement-phase`.

Allowed actions:
- **Read** files (to detect existing state)
- **Write** the scaffolded harness/config files listed above (these are configuration, not source)
- **Bash** for `git init`, `git add`, `git commit`, MCP probe
- **Grep/Glob** to detect prior state

Forbidden:
- Writing source code (`.py`, `.ts`, `.tsx`, `.dart`, `.js`, `.jsx`, etc.)
- Calling other slash commands implicitly
- Modifying any file outside the current working directory

## Step 0 — Parse arguments

Usage:
```
/init-component <name> [--pm "<name>"] [--ai-dev "<name>"] [--repo-owner <owner>] [--repo-name <name>]
```

Required:
- `<name>` — positional, the component name. Must be a valid identifier: `[A-Za-z][A-Za-z0-9_-]*`. Examples: `QuotingAgent`, `scheduling-service`, `InvoiceWorker`.

Optional flags (default to `"TBD"` if omitted, except repo flags which default to `null`):
- `--pm "<name>"` — Product Manager full name
- `--ai-dev "<name>"` — AI developer label (e.g. `"Anima (Claude Opus 4.7)"`)
- `--repo-owner <owner>` — GitHub org/user (used for PR-detail flows later)
- `--repo-name <name>` — GitHub repo name (defaults to `<name>` lowercased)

If `<name>` is missing, print usage and stop.

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

The `register_component` MCP call in Step 7 also records the first lifecycle event (Discovery), so this command does NOT need a separate `report_lifecycle_stage` push at Step 0.5. The Step 0.5 pattern that other harness commands use is folded into Step 7 here.

## Step 1 — Pre-flight refusal conditions

Refuse and stop immediately if any of the following hold. The check ordering matters: cheaper checks first.

1. **`.shipboard.yml` already exists** at the working directory root (regardless of whether the named component already exists in ShipBoard):
   ```
   Refused: a `.shipboard.yml` already exists in this directory (component: <existing.component.name>).
   To re-scaffold, delete it first: rm .shipboard.yml
   To start a different component, run /init-component from a different directory.
   ```

2. **Working tree is dirty** in a non-empty git repo (`git status --porcelain` is non-empty AND there is at least one prior commit):
   ```
   Refused: working tree has uncommitted changes. Stash or commit them before running /init-component
   so the scaffolding goes into a clean first commit.
   ```

3. Otherwise proceed. Specifically allow these starting states:
   - Brand-new empty directory (no `.git`, no `.shipboard.yml`, no other files)
   - Empty directory that is already a git repo with no commits and no `.shipboard.yml`
   - Non-empty directory whose only tracked files are pre-existing harness boilerplate (`.gitignore`, `README.md`) AND no `.shipboard.yml` AND clean working tree

Do not modify any files until the pre-flight passes.

## Step 2 — Initialize git (only if not already a repo)

Run:
```bash
git rev-parse --git-dir 2>/dev/null
```

If exit code is non-zero (not a git repo):
```bash
git init
git branch -M main
```

Write a `.gitignore` covering the usual suspects:
```
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.coverage

# Node
node_modules/
*.log

# IDE / OS
.vscode/
.idea/
.DS_Store

# Harness scratch
.shipboard/pending_events.log
.shipboard/history.log
```

If `.gitignore` already exists, leave it alone — do not overwrite.

If the repo already had a remote and `--repo-owner`/`--repo-name` are missing, attempt to derive them:
```bash
git remote get-url origin 2>/dev/null
```
Parse the URL (https/ssh forms of `github.com/<owner>/<name>(.git)?`). On parse failure, leave both fields `null`.

## Step 3 — Write `.shipboard.yml`

Compute today's date as `YYYY-MM-DD`. Write `.shipboard.yml` at the repo root:

```yaml
# .shipboard.yml — managed by the harness; commit this file.
schema_version: 1

component:
  name: <name>
  pm: "<pm>"
  ai_developer: "<ai-dev>"
  created_at: <YYYY-MM-DD>

repo:
  primary: <repo-owner>/<repo-name>     # null if neither flag was supplied AND no git remote was detected

shipboard:
  url: http://localhost:8000
  fail_silently: true

stage:
  current: discovery
  history_path: .shipboard/history.log
```

If `repo.primary` is null, write the line as `primary: null` (preserve schema for downstream readers).

## Step 4 — Scaffold `docs/`

Create the `docs/` directory if it doesn't exist. Write four files.

### `docs/REQUIREMENTS.md`
```markdown
# <name> — Requirements

**Status:** Discovery (filled in by PM during this stage)
**Last updated:** <YYYY-MM-DD>

## Problem statement
What problem does this component solve, in 2–3 sentences?

## Value hypothesis
Why does solving this matter? Who benefits, and how is the win measured?

## Target users
Who interacts with this component (humans, other components, AI agents)?

## Functional requirements
What must the component do? List 3–10 capabilities.

## Non-functional requirements
- Performance budgets (latency, throughput)
- Reliability targets (uptime, error rate)
- Security boundaries (auth, data classification)
- Compliance constraints (PII, regulated data)

## Open questions
What's still unknown? Each open question blocks the move from Discovery → Plan-Pending.

## Out of scope (v1)
What this component will NOT do — keep this section honest, it prevents scope creep.
```

### `docs/MOCKUPS.md`
```markdown
# <name> — UI Mockups

(Filled in during Plan-Pending. Add screenshots, Figma links, or text-based wireframes here.)
```

### `docs/SPECS.md`
```markdown
# <name> — Technical Specification

(Filled in during Plan-Pending. Data model, schemas, API contracts, FSM definitions go here.)
```

### `docs/UI.md`
```markdown
# <name> — Design System

(Filled in during Plan-Pending. CSS tokens, Tailwind config, fonts, component primitives go here.
For non-frontend components, mark this file as N/A and remove it.)
```

## Step 5 — Scaffold `CLAUDE.md`

If a `CLAUDE.TEMPLATE.md` exists at `D:\OSS\AgenticDevelopmentBestPractices\CLAUDE.TEMPLATE.md` (or wherever this harness repo lives), copy it to `./CLAUDE.md` with `<name>` substituted for `{PROJECT_NAME}`.

If the template is unreachable, write a minimal fallback:
```markdown
# <name>

**Stack / Run dev / Run tests / Lint:** TBD — filled during Plan-Pending.

## Hard Rules
1. Read before writing.
2. No file over 200 lines.
3. No function over 30 lines.
4. No `Any`/`any` without justification.
5. Every public method has full type annotations.
6. ≥1 happy + 1 error test per public method.
7. Tooling must pass before "complete".

See `~/.claude/CLAUDE.TEMPLATE.md` for the full template once available.
```

## Step 6 — Scaffold `ARCHITECTURE.md`

```markdown
# <name> — Architecture

**Status:** placeholder — filled in during Plan-Pending.

See `docs/REQUIREMENTS.md` for the problem statement and `docs/SPECS.md` for the technical spec
(both populated when the component moves out of Discovery).

The required sections (Overview / Tech Stack / Project Structure / Layer Responsibilities /
Data Flow / Key Domain Concepts / State Machines) will be filled in once `/plan-release` runs
and the implementation phases are scoped. See `~/.claude/rules/shared/documentation.md` for the
canonical `ARCHITECTURE.md` shape.
```

## Step 7 — Push the initial MCP event (best-effort, NEVER blocks)

If `.mcp.json` exists in the working directory AND it registers a `shipboard` server AND that server is reachable, call:

```
shipboard(action="register_component",
          name=<name>,
          pm=<pm>,
          ai_developer=<ai-dev>,
          repo_owner=<repo-owner or null>,
          repo_name=<repo-name or null>,
          stage="discovery",
          source="init-component")
```

`register_component` is a write action that upserts: it creates the component row if absent, updates metadata if present, and writes the first lifecycle event (Discovery) atomically.

On any failure (no `.mcp.json`, server down, network error, permission denied, schema mismatch):
1. Append a one-line JSON record to `.shipboard/pending_events.log` with the same payload plus a `timestamp` field. Create the `.shipboard/` directory if needed.
2. Continue silently. **NEVER** abort the scaffolding because of an MCP failure.

The first successful future event push (from `/plan-release`, `/check`, etc.) flushes any queued entries.

## Step 8 — First commit

Stage everything and commit:
```bash
git add .
git commit -m "chore: scaffold <name> (discovery stage)"
```

Do NOT push. Pushing requires a remote that the user has not yet configured (and may not want).

If pre-commit hooks fail (rare in a freshly scaffolded repo), report the failure and stop. Do not retry, do not `--no-verify`.

## Step 9 — Print next steps

Output a short, action-oriented summary that lists each scaffolded file, the initial commit hash, the ShipBoard event status (`pushed` vs `queued to .shipboard/pending_events.log`), and the recommended next actions:

1. PM: edit `docs/REQUIREMENTS.md` — problem statement, target users, NFRs, open questions.
2. When requirements are clear, run `/plan-release` to design the implementation phases.
3. After `/plan-release`, run `/plan-validate` to verify the spec is Sonnet-ready.
4. Then `/implement-phase 1` to ship the first phase.

## Failure modes (summary)

| Condition | Response |
|-----------|----------|
| `<name>` missing | Print usage, stop. No files modified. |
| `.shipboard.yml` already exists | Refuse with recovery message. No files modified. |
| Dirty working tree (existing repo with commits) | Refuse with recovery message. No files modified. |
| `.gitignore` already exists | Leave it alone, continue. |
| `CLAUDE.TEMPLATE.md` unreachable | Use minimal fallback CLAUDE.md, continue. |
| MCP unreachable / call fails | Queue event to `.shipboard/pending_events.log`, continue. |
| Pre-commit hook fails on first commit | Report and stop. Do not retry, do not `--no-verify`. |

## Why scaffolding lives in the harness, not in ShipBoard

Scaffolding is a **workflow** operation, peer to `/plan-release` and `/implement-phase`. Keeping it here keeps the `CLAUDE.md` template + `.shipboard.yml` schema in sync with the rest of the harness commands that read them. ShipBoard remains a pure observability layer — it stores events, it doesn't dictate them.
