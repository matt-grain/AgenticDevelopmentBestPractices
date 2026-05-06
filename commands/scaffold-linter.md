# Scaffold a Mechanical Linter from the Recipe Catalog

You are a linter-scaffolding **orchestrator**. Your job is to take a rule description, pick the closest reference recipe from `recipes/linters/<project-type>/`, adapt it to this project's package name and layer paths, write the new check file under `tools/pre_commit_checks/`, append a hook entry to `.pre-commit-config.yaml`, and verify the linter runs.

This is the high-leverage step that converts an architecture rule from "LLM judgment during `/check`" into "deterministic mechanical evaluator" — the Anthropic harness paper's main insight in practice.

## CRITICAL — Delegation Rule

This command writes a single tooling file (~50–150 lines) plus a YAML config block. The work is template-adaptation from a recipe (find-replace + path adjustments + occasional value-set tweaks), not original code authoring — the orchestrator writes directly. Same scaffolding pattern as `/init-component`.

Allowed actions:
- **Read** files (recipes, project structure, ARCHITECTURE.md, existing pre-commit config)
- **Write** the new linter file + entries (and `_base.{py|ts}` if missing in `tools/pre_commit_checks/`)
- **Edit** `.pre-commit-config.yaml`
- **Bash** for `pre-commit run` verification, `ls`, file detection
- **Glob/Grep** for project structure detection

Forbidden:
- Writing application source code
- Modifying any file outside `tools/pre_commit_checks/` and `.pre-commit-config.yaml`

## Step 0 — Parse arguments

Usage:
```
/scaffold-linter <rule-id> [--recipe <recipe-name>[/<file>]] [--reason "<reason>"]
```

Required:
- `<rule-id>` — kebab-case identifier matching the convention `check_<rule-id>.{py|ts}`
  - Examples: `no-session-in-services`, `useeffect-has-why`, `no-direct-env-access`

Optional:
- `--recipe <name>` — recipe directory (e.g. `python-fastapi-layered`, `python-clean-arch`, `vite-react`). If omitted, auto-detected from project type.
- `--recipe <name>/<file>` — exact recipe file (e.g. `python-fastapi-layered/check_no_session_in_services.py`). Overrides auto-match.
- `--reason "<text>"` — short reason used in the pre-commit hook `name:` field and the commit message. Defaults to a description derived from the recipe.

If `<rule-id>` is missing, print usage and stop.

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

If `.shipboard.yml` exists in the repo root and `.mcp.json` registers `shipboard`:

1. Read `.shipboard.yml`; extract `component.name`.
2. Call:
   ```
   shipboard(action="report_lifecycle_stage",
             component=<component.name>,
             stage="generate",
             sub_state="scaffold-linter",
             source="scaffold-linter",
             pr_number=null)
   ```
3. On failure, append a JSON line to `.shipboard/pending_events.log` and continue. Best-effort — never blocks.

## Step 1 — Detect project context

1. Detect project type using the same logic as other harness commands:
   - `pyproject.toml` contains `fastapi` → `python-fastapi`
   - `pyproject.toml` without fastapi but with `domain/` directory → `python-clean-arch`
   - `vite.config.*` exists → `vite-react`
   - `next.config.*` exists → `react-nextjs` (no recipe yet — error)
   - `pubspec.yaml` with flutter → `flutter` (no recipe yet — error)

2. Map project type to recipe directory:

   | Project type | Recipe directory |
   |---|---|
   | `python-fastapi` | `recipes/linters/python-fastapi-layered/` |
   | `python-clean-arch` | `recipes/linters/python-clean-arch/` |
   | `vite-react` | `recipes/linters/vite-react/` |
   | `react-nextjs` | (no recipe yet) |
   | `flutter` | (no recipe yet) |

   If no recipe directory exists for the detected type, stop with: `"No linter recipe for <type> yet. Either author the linter manually following recipes/linters/<closest>/, or contribute a new recipe."`

3. If `--recipe` was provided, use it instead of the auto-detected directory (the user knows what they want).

4. Detect package name and source layout:
   - **Python**: package name = the single dir under `src/` that contains `__init__.py` (or read `[project].name` from `pyproject.toml` and convert dashes to underscores).
   - **TypeScript**: source root is `src/` by convention; no package-name substitution needed (TS recipes don't reference a package name).

## Step 2 — Pick the reference recipe file

Two cases:

**Case A: `--recipe <name>/<file>` was specified.**
- Read `recipes/linters/<name>/<file>` directly. This is the exemplar.

**Case B: only the directory is known (auto-detected or `--recipe <name>` only).**
1. Read the recipe directory's `README.md` to inventory available checks.
2. Look for an exact filename match: `<rule-id>` should map to `check_<rule_id_underscored>.{py|ts}`. Example: `no-session-in-services` → `check_no_session_in_services.py`.
3. If exact match found → use it.
4. Otherwise → no exemplar exists for this rule. Tell the user:
   ```
   No exact recipe for `<rule-id>` in recipes/linters/<name>/.
   Available recipes:
   {list each check_*.{py|ts} from the directory README}

   Options:
   1. Re-run with --recipe <name>/<closest-file> to use that as inspiration
   2. Author the linter manually using the recipes as patterns
   3. Cancel
   ```
   Then stop. Do not invent a linter from scratch — ambiguity here costs more than it saves.

## Step 3 — Read project conventions (sanity gate)

Before adapting, confirm:
- Is `tools/pre_commit_checks/` already present? If yes, list its contents — we'll mirror the file naming.
- Is `_base.{py|ts}` already present in `tools/pre_commit_checks/`? If no, we'll copy the recipe's `_base` file alongside the new check.
- Is `.pre-commit-config.yaml` present? Is it valid YAML? If malformed, stop and tell the user to fix it first.
- For Python projects: read `ARCHITECTURE.md` (or fall back to a representative `services/` file) to confirm the package name and layer paths the recipe will be substituted with.
- For TypeScript projects: confirm `tsx` is in `devDependencies` of `package.json` — if not, warn the user that they'll need `pnpm add -D tsx` before pre-commit can run the hook.

## Step 4 — Adapt the recipe

### Python recipes

Substitutions to apply (all mechanical):

| Recipe original | Replace with |
|---|---|
| `shipboard.<x>` (in import paths and string literals) | `<project_package>.<x>` |
| `pharma_derive.<x>` (if pharma source) | `<project_package>.<x>` |
| `Path("src/shipboard/<layer>")` | `Path("src/<project_package>/<layer>")` |
| `Path("src/<layer>")` (clean-arch recipes use this directly) | leave unchanged unless the project's source root differs |
| Docstring lines that reference the source project | Update to reflect this project — use `--reason` if provided |

For `check_enum_discipline.py` specifically: the `KNOWN_ENUM_VALUES` dict is project-specific. Read the project's `enums/` directory, parse each StrEnum class, build a fresh dict mapping each member's value to `"<EnumName>.<MEMBER>"`, and replace the recipe's dict wholesale. If the project has no `enums/` yet, write the linter with an empty dict and a `# TODO: populate after enums/ exists` comment — `/scaffold-linter` is being run too early in this case; warn the user.

### TypeScript recipes

The vite-react recipes are written generically — minimal substitution needed.

Adjustments to consider:
- `ALLOWLIST_SUFFIXES` in `check_no_direct_env_access.ts` if `lib/env.ts` lives elsewhere.
- `API_CLIENT_RECEIVER_PATTERN` in `check_no_useeffect_for_fetching.ts` if the project uses non-default API client variable names — read a representative service file to detect.

### File output

Write the adapted file to:
```
tools/pre_commit_checks/check_<rule_id_underscored>.{py|ts}
```

Where `<rule_id_underscored>` = `<rule-id>` with hyphens replaced by underscores (so `no-direct-env-access` becomes `check_no_direct_env_access.ts`).

If `tools/pre_commit_checks/_base.{py|ts}` doesn't exist, copy the recipe's `_base` file there too.

## Step 5 — Append to `.pre-commit-config.yaml`

If `.pre-commit-config.yaml` doesn't exist, create it with this skeleton:

```yaml
repos:
  - repo: local
    hooks:
      # hooks added here by /scaffold-linter and manually
```

Then append the new hook entry under the existing `repo: local` `hooks:` list (find it with simple text scanning; if multiple `local` blocks exist, use the first).

**Python entry:**
```yaml
- id: check-<rule-id>
  name: <reason or recipe description>
  entry: python tools/pre_commit_checks/check_<rule_id_underscored>.py
  language: python
  pass_filenames: false
  always_run: true
  types: [python]
```

**TypeScript entry:**
```yaml
- id: check-<rule-id>
  name: <reason or recipe description>
  entry: pnpm tsx tools/pre_commit_checks/check_<rule_id_underscored>.ts
  language: system
  pass_filenames: false
  always_run: true
  types_or: [ts, tsx]
```

If a hook with the same `id` already exists, stop and tell the user — duplicate IDs cause silent skipping in pre-commit.

## Step 6 — Verify the linter executes

Run:
```bash
pre-commit run check-<rule-id> --all-files
```

Three possible outcomes:

| Exit | Meaning | Next |
|---|---|---|
| 0 — `OK: ...` | Linter executes, no current violations. The rule is now mechanically enforced. | Report success. |
| 1 — `Total: N violation(s)` listed | Linter executes, project has existing issues. | Report success — the linter works; the violations are real and need fixing. Suggest `/fix-check` or manual cleanup before next commit. |
| Other (syntax error, import error, missing dep, malformed YAML) | Linter is broken. | STOP. Report the exact error. Do not commit. Leave files in place for the user to inspect or for follow-up. |

If `pre-commit` itself isn't installed (`pre-commit: command not found`), warn the user to install it (`uv pip install pre-commit` or `pip install pre-commit`) and run `pre-commit install` to wire the hook into git, but treat the scaffolding step as complete — the linter file is ready, the hook is configured, the only missing piece is the runtime tool which the user adds globally.

## Step 7 — Report

Output:
```
## Linter Scaffolded — `check-<rule-id>`

Files written / modified:
- `tools/pre_commit_checks/check_<rule_id_underscored>.{py|ts}` (new)
{- `tools/pre_commit_checks/_base.{py|ts}` (new — created because it didn't exist) [only if applicable]}
- `.pre-commit-config.yaml` (hook entry appended)

Recipe used: `recipes/linters/<recipe-name>/check_X.<ext>`
Reason: <reason text>

Verification: `pre-commit run check-<rule-id> --all-files` → exit <0|1>
{- exit 0: clean — the rule is now enforced on every commit and during `/check`}
{- exit 1: <N> existing violations found:
   <list of file:line: message lines, max 10>
   ...
   Run `/fix-check` to auto-fix, or address manually before the next commit.}

Next steps:
1. Review the new linter file — adjust constants if your project differs from the recipe defaults
2. Commit the changes: `tools/pre_commit_checks/*` and `.pre-commit-config.yaml`
3. If exit was 1, fix the existing violations before the next commit (otherwise pre-commit will block it)
```

## Failure modes (summary)

| Condition | Response |
|---|---|
| `<rule-id>` missing | Print usage, stop. No files modified. |
| Project type detected has no recipe | Stop with "no recipe for `<type>` yet — author manually following the closest recipe in `recipes/linters/`". |
| `--recipe` references a nonexistent path | Stop with "recipe not found at `recipes/linters/<path>`". |
| No exact-match recipe file in directory + no `--recipe <file>` override | Stop and ask the user to choose an exemplar or cancel (Step 2). |
| `.pre-commit-config.yaml` malformed | Stop. Tell the user to fix it first. Do not modify it. |
| Hook with same `id` already exists | Stop. Duplicate IDs are silently dropped by pre-commit. |
| `pre-commit run` exits non-zero with non-violation error (syntax error, import error) | Stop. Report the error. Leave scaffolded files in place for inspection. |
| `pre-commit` itself not installed | Warn, suggest `uv pip install pre-commit && pre-commit install`. Treat scaffolding as complete. |

## When to invoke this command

Two natural entry points, both surfaced by other harness commands:

- **From `/plan-release`**: a rule listed in the plan's `## Mechanical Rules to Enforce` section is ready to lint (the prerequisite layer/file exists).
- **From `/plan-fix`**: a pattern flagged in `## Recurring Patterns Worth Promoting to Linters` should now be enforced (the existing violations are about to be fixed by the same plan, so the linter ships clean).

It's also fine to invoke directly when you notice a recurring issue and want to mechanize the rule on the spot.

## Why scaffolding (not subagent dispatch)

Recipe adaptation is mechanical: name substitution, path adjustment, occasional value-set update. The harness's "delegate to subagent" rule applies to *application* source code (where Sonnet's specialized agents shine on focused subsets) — tooling boilerplate scaffolding is the orchestrator's domain. Same reasoning as `/init-component` writing `.shipboard.yml`, `CLAUDE.md`, etc., directly.

If a future rule has no recipe match AND requires substantive AST authoring from scratch, that's the right time to dispatch — but for that case, the better answer is usually to first contribute a generalized recipe to `recipes/linters/<type>/` so the next project can scaffold it directly.
