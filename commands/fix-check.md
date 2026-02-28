# Fix Pre-Merge Check Violations

You are a check-fix **orchestrator**. Your job is to fix violations reported by `/check` — the lightweight pre-merge architecture gate. The key discipline: **parse the violation table, group into fix units, dispatch to correct subagents, then re-check to confirm no new violations were introduced.**

## CRITICAL — Delegation Rule

**You MUST NOT write, edit, or modify any source code yourself.** You are an orchestrator, not an implementer. ALL code changes MUST be delegated to a subagent via the `Agent` tool with the correct `subagent_type`.

Your only allowed actions:
- **Read** files (to understand context, verify fixes)
- **Grep/Glob** (to scan for patterns, verify results)
- **Bash** (to run tooling gates — linters, formatters, tests)
- **Agent** (to dispatch implementation work to subagents)
- **TaskCreate/TaskUpdate** (to track progress)

If you catch yourself about to use Edit/Write on a `.py`, `.ts`, `.tsx`, `.dart`, or any source file — STOP and dispatch a subagent instead.

## Step 0 — Parse Violations from Conversation

1. **Scan the conversation** for the `/check` output. Look for the violation table with this structure:
   ```
   | Severity | File | Issue | Rule |
   |----------|------|-------|------|
   | 🔴 | ... | ... | ... |
   | 🟡 | ... | ... | ... |
   ```

2. **If no violation table is found** in the conversation, tell the user: "No `/check` output found in this conversation. Run `/check` first, then ask me to fix the violations." and stop.

3. **Parse each row** into a structured list: `{ severity, file, issue, rule }`.

4. **Separate by severity:**
   - 🔴 Critical — will be fixed (default)
   - 🟡 Warning — will be fixed only if the user explicitly asks

5. **Present the parsed violations:**
   ```
   Found {N} violations from /check:
   - 🔴 Critical: {X}
   - 🟡 Warning: {Y}

   Default: fixing 🔴 Critical only.
   ```
   If there are 🟡 Warnings, ask: "Also fix 🟡 Warnings? (y/n)"

6. Also parse the **Tooling** section and **Missing Companions** section from the `/check` output if present — these inform Phase 0 micro-fixes and gap awareness.

## Step 1 — Group into Fix Units

### 1a — Detect Project Type and Subagent

Detect the project type and select subagent(s):

| Project Detection | subagent_type |
|---|---|
| `pyproject.toml` contains `fastapi` in dependencies | `python-fastapi` |
| `next.config.ts` / `next.config.js` / `next.config.mjs` exists | `react-nextjs` |
| `vite.config.ts` / `vite.config.js` exists | `vite-react` |
| `pubspec.yaml` contains `flutter` in dependencies | `flutter` |
| Python project with MCP server patterns | `python-mcp-expert` |
| Other Python project | `general-purpose` |
| Other JS/TS project | `general-purpose` |

**Mixed projects:** Tag each fix unit by file extension to route to the correct subagent. Never send `.dart` files to a Python agent or `.py` files to a React agent.

### 1b — Phase 0: Micro-fixes (Tooling-solvable)

Before grouping architectural fixes, extract violations that tooling can fix directly (no subagent needed):

| Violation Type | Fix Action |
|---|---|
| Linting errors (ruff, eslint, dart analyze) | Run `ruff check --fix` / `pnpm eslint --fix` / `dart fix --apply` |
| Formatting issues | Run `ruff format` / `pnpm prettier --write` / `dart format` |
| Import sorting | Run `ruff check --select I --fix` / auto-fix via eslint |

These run as **Phase 0** before any subagent work.

### 1c — Group Architectural Violations into Fix Units

Group the remaining violations:

| Grouping Logic | Example |
|---|---|
| Same violation type across multiple files | "Add return type annotations" → files A, B, C |
| Multiple violations in the same file (if fixes interact) | "Fix service X" → all issues in that file |
| Independent violations in the same file | Keep as separate fix units |

**Rules:**
- **Max 8 files per fix unit.** If more, split into batches.
- **One issue type per fix unit.** Don't bundle "add type annotations" with "move DB queries out of service" even if they touch the same file.
- **Tag each unit** with the `subagent_type` based on file extensions.

### 1d — Build Fix Unit Table

```
| # | Fix Unit | Files | Subagent | Source Violations |
|---|----------|-------|----------|-------------------|
| 0 | Phase 0: Tooling auto-fix | (all) | (direct) | Linting/formatting from tooling section |
| 1 | Add return type annotations | [file list] | python-fastapi | 🔴 rows 2, 5, 8 |
| 2 | Move DB queries from services | [file list] | python-fastapi | 🔴 rows 3, 7 |
| 3 | Extract large component | [file list] | react-nextjs | 🟡 row 12 |
```

### 1e — Gather Context for Each Fix Unit (MANDATORY)

Before building HOW TO FIX instructions, the orchestrator MUST read the violation files and their context. For each fix unit:

1. **Read the violating file** at the exact lines from the `/check` output
2. **Search for existing enums/types** that the fix should use:
   - Grep for `StrEnum`, `enum class`, `enum ` in the project to find what already exists
   - If the violation says "should use enum", find the SPECIFIC enum (e.g., `ScanEntityType` in `schemas/`) — don't tell the subagent to "create an enum" if one already exists
3. **Check adjacent code** for the correct pattern:
   - If the fix is "use enum instead of raw string", find a file that already does it correctly and include it as a reference example
4. **Check behavioral context** for behavioral violations (silent no-ops, placeholder UI):
   - Read the surrounding code to understand what the case SHOULD do (is the backend endpoint implemented? does a repository method exist?)
   - If the fix requires a backend endpoint that doesn't exist yet, the fix is "throw UnimplementedError with a real tracker ref" — NOT "add a placeholder"

This step prevents the most common failure: subagents receiving vague instructions and introducing new violations while fixing old ones.

## Step 2 — Present Fix Plan

Show the fix plan to the user:

```
## Fix Plan — {N} violations across {M} fix units

### Phase 0 — Tooling Auto-fix
{List auto-fixable items}

### Phase 1 — Architectural Fixes
| # | Fix Unit | Files | Agent |
|---|----------|-------|-------|
| 1 | ... | ... | ... |
| 2 | ... | ... | ... |

Total files affected: {N}

Proceed with fixes?
```

**Wait for user confirmation before executing.**

## Step 3 — Execute Fixes

### 3a — Phase 0: Run Tooling Auto-fixes

Run the relevant tooling directly (no subagent):

**Python/FastAPI:**
```bash
uv run ruff check <changed files> --fix
uv run ruff format <changed files>
```

**Next.js / Vite React:**
```bash
pnpm eslint <changed files> --fix
pnpm prettier --write <changed files>
```

**Flutter:**
```bash
dart fix --apply <changed files>
dart format <changed files>
```

If tooling is not installed, skip and note it.

### 3b — Build Concrete HOW TO FIX Instructions (MANDATORY)

**Before dispatching ANY subagent, you MUST build concrete fix instructions.** Vague prompts like "fix the raw strings" produce bad fixes. For each violation:

1. **Read the violating file** at the exact lines mentioned in the `/check` output
2. **Identify the existing enum/type** that should be used — search the codebase for it (e.g., `ScanEntityType` already exists in schemas)
3. **Write the exact transformation** as a before/after or numbered steps

**Examples of BAD vs GOOD HOW TO FIX instructions:**

| BAD (vague) | GOOD (concrete) |
|---|---|
| "Use enums instead of raw strings" | "Replace raw string keys `"purchase_order"`, `"serial_number"` in the `loaders` dict (line 180) with `ScanEntityType.PURCHASE_ORDER`, `ScanEntityType.SERIAL_NUMBER` etc. Import `ScanEntityType` from `schemas.operator_workflow`." |
| "Fix the silent no-op" | "The `qualityCheck` case (line 117-119) sets `isComplete=true` without calling any repository method. Either: (a) add `await repository.submitQualityCheck(...)` if the endpoint exists, or (b) throw `UnimplementedError('QC endpoint not available')` so the operator sees a clear error — never silently pretend success." |
| "Use domain enum for quality" | "Create `QualityAssessment` enum in `domain/enums/` with values `clean`, `contaminated`, `mixed` matching the closed set in `quality_dropdown.dart`. Change `qualityAssessment: String?` to `QualityAssessment?` in `receive_goods_request.dart`." |
| "Fix the TODO" | "Line 58: `TODO(tech-debt)` references `#123` — verify this is a real issue in the tracker. If not, create a real issue and update the reference, or remove the TODO entirely." |

### 3c — Dispatch Subagents

For each fix unit, create a tracking task (TaskCreate) and dispatch to the correct subagent via the Agent tool.

The subagent prompt MUST include:

```
You are fixing specific architecture violations found by a pre-merge check.

PROJECT CONTEXT:
{Paste relevant sections from ARCHITECTURE.md — tech stack, layer responsibilities}
{Paste any relevant project-specific instructions from CLAUDE.md}

FIX UNIT: {title}
VIOLATIONS TO FIX:
{For each violation in this unit:}
- File: {file path}
  Issue: {issue description}
  Rule: {rule being violated}

FILES TO MODIFY (you MUST modify ALL of these — do not skip any):
{complete file list, one per line}

HOW TO FIX (step-by-step — follow this exactly):
{The concrete instructions you built in Step 3b — with exact enum names,
import paths, line numbers, and before/after examples.}

INSTRUCTIONS:
1. Read each file in the list above
2. Apply the fix using the HOW TO FIX steps above — follow them exactly
3. After modifying each file, confirm it follows the expected pattern
4. Report back which files you modified and any files you could NOT modify (with reason)

IMPORTANT:
- Do NOT skip files. Every file in the list needs the fix.
- Follow the project's existing code style and patterns exactly.
- If a file doesn't actually have the violation (false positive), note it but move on.
- NEVER add wrapper code or extra abstractions to "solve" the issue — apply the direct fix.
- Do NOT introduce new violations while fixing. Specifically:
  - No new raw string literals for values from a closed set — always use existing enums
  - No new `Any` / `any` type annotations — use Protocol, Union, or concrete types
  - No new untyped dict returns — use Pydantic schemas or typed data classes
  - No new `# type: ignore` / `@ts-ignore` without justification
  - No silent no-ops (empty switch cases, bare `break`/`pass` that hide failures)
  - No placeholder text visible to end users without a tracker reference
  - No hardcoded color/style literals — use theme tokens

BEFORE returning your result, verify EVERY file you created/modified against this checklist. Fix any violations inline — do NOT leave them for a later pass.

FLUTTER:
- [ ] No Map<String, Object?> or Map<String, dynamic> in presentation — use typed data classes
- [ ] No raw string comparisons for state/status — use enum values everywhere
- [ ] No raw string keys in dispatch maps (switch/case, Map literals) — use enum members
- [ ] No ref.read() inside build() — use ref.watch (ref.read only in callbacks)
- [ ] No business logic in presentation (no domain object construction in providers/widgets)
- [ ] No hardcoded Color(0xFF...) or Color(0x66...) — use Theme tokens or named colors from core/theme/
- [ ] No silent no-ops in switch cases — every case either does real work or throws
- [ ] No placeholder/stub text visible to end users without a TODO(#issue) reference
- [ ] Enum serialization uses .name (stable identifier), NOT .label/.displayName (fragile, locale-dependent)
- [ ] Domain entity fields for values from a closed set use enum types, not String
- [ ] Entity ID fields are semantically correct — don't store a PO ID in a field named poItemId
- [ ] No // TODO without a REAL tracker reference (not placeholder #123)
- [ ] Test helper files respect 200-line limit — split per feature domain if oversized
- [ ] Run dart analyze --fatal-infos and fix before returning

PYTHON/FASTAPI:
- [ ] Services depend on repositories only — never on other services (use workflows)
- [ ] No Session parameter in services — not even private methods
- [ ] All status/type fields use StrEnum — never raw str, including in Protocol definitions
- [ ] Dict dispatch keys (e.g., `loaders = {"key": ...}`) use enum members, not raw strings
- [ ] Router params from a closed set use StrEnum type annotation, not bare `str`
- [ ] No dict[str, Any] or untyped dict returns — use Pydantic schemas or typed sub-models
- [ ] `Any` type hints have a justification comment AND a suggestion of Protocol/Union alternative
- [ ] No // TODO without a REAL tracker reference (not placeholder #123)
- [ ] Run ruff check and ruff format before returning

REACT/NEXT.JS/VITE:
- [ ] No Record<string, unknown> or { [key: string]: any } — use Zod schemas
- [ ] No raw string status comparisons — use const objects or string unions
- [ ] No dispatch keys as raw strings — use const object keys
- [ ] No placeholder/stub UI text without a TODO(#issue) reference
- [ ] No // TODO without a REAL tracker reference
- [ ] Run tsc --noEmit and eslint before returning

ALL STACKS:
- [ ] Files under 200 lines, test files under 300 lines, test helpers under 200 lines per domain
- [ ] Functions under 30 lines
- [ ] No // TODO, // FIXME, // HACK without a REAL tracker reference — placeholder refs like #123 don't count
- [ ] No silent no-ops (switch case / if branch that sets success state without doing work)
- [ ] No fragile serialization (using display labels for round-trip instead of stable identifiers)
```

### 3d — Verify Each Fix Unit

After each subagent completes, immediately verify — do NOT trust the subagent's self-report:

1. **File count check**: Did the subagent modify all files listed in the unit?
2. **Read the modified files**: Read every modified file (not just 1-2). Check:
   - The fix actually addresses the violation (not a cosmetic change that leaves the real issue)
   - No silent no-ops: if a switch/case/if-branch was the violation, verify it now does real work or throws — not just `break`/`pass`/empty body
   - No placeholder text visible to users without a tracker ref
3. **Regression Grep**: Run these patterns on ALL modified files to catch common fix-introduced violations:

   **Python files:**
   ```
   Grep: `\bdict\[str,` → new untyped dict signatures
   Grep: `-> Any\b` → new Any returns without justification
   Grep: `"[a-z_]+".*:.*lambda` → raw string keys in dispatch dicts
   Grep: `status: str\b` → raw str for status fields
   Grep: `# TODO` → verify each has a REAL tracker ref (not #123 placeholder)
   ```

   **Dart files:**
   ```
   Grep: `Color\(0x` → hardcoded color literals
   Grep: `\.label\b` in context of serialization/storage → fragile enum round-trip
   Grep: `'[a-z_]+'` as map keys in dispatch → raw string dispatch
   Grep: `String\?` on domain entity fields for closed sets → should be enum
   Grep: `break;` after setting success state → silent no-op
   Grep: `placeholder\b|pending\b|TBD\b|stub\b` in user-visible strings → unfinished feature
   ```

   **All files:**
   ```
   Grep: `TODO|FIXME|HACK` → verify each references a real issue, not a placeholder
   wc -l → verify file length limits (200 source, 300 test, 200 test helpers)
   ```

4. If the subagent missed files or introduced new violations, re-dispatch once for ONLY the missed/broken files with explicit correction instructions.

### 3e — Update Task Status

Mark each tracking task as completed (or partial with notes).

## Step 4 — Verify (Re-check)

This is the critical differentiator from ad-hoc "fix them" requests.

### 4a — Run Tooling Gate on Touched Files

Run the project's tooling scoped to all files modified during this fix cycle:

**Python/FastAPI:**
```bash
uv run pyright <all modified files>
uv run ruff check <all modified files>
```

**Next.js / Vite React:**
```bash
pnpm tsc --noEmit
pnpm eslint <all modified files>
```

**Flutter:**
```bash
dart analyze --fatal-infos
dart format --set-exit-if-changed <all modified files>
```

### 4b — Re-run Architecture Check on Touched Files

Re-read each modified file and re-apply the same `/check` rules (from Step 2 of `/check`) scoped to only those files. Build a new violation table.

**Pay special attention to these fix-introduced regression patterns:**

| Pattern | What to check | Why fixes introduce this |
|---|---|---|
| Silent no-op | Switch cases that set success state (`isComplete=true`, return success) without doing real work | Subagent removes the violation text but leaves the empty case body |
| Fragile serialization | Enums round-tripped via `.label`/`.displayName` instead of `.name` | Subagent adds an enum but serializes via the display string |
| Placeholder text in UI | Strings like "pending", "TBD", "placeholder" visible to users | Subagent adds TODO comment but leaves the UI text |
| Entity ID conflation | Field named `fooId` storing a `bar` entity's ID | Subagent renames one field but not the call sites |
| Raw string in new code | Fix adds new enum but other code paths still use raw strings | Subagent fixes the flagged line but not adjacent code using the same pattern |
| Fake tracker refs | `TODO(#123)` or `TODO(tech-debt)` without a real issue number | Subagent adds a TODO to satisfy the "must have ref" rule but uses a placeholder |
| File length after split | Original file still over limit, or split target over limit | Subagent creates the new file but doesn't move enough code out |

### 4c — Compare Results

Categorize each violation from the re-check:

| Category | Meaning | Action |
|---|---|---|
| ✅ Resolved | Was in original `/check`, now gone | Count as fixed |
| ⚠️ Remaining | Was in original `/check`, still present | Report as unfixed |
| 🆕 New | Was NOT in original `/check`, appeared after fix | Trigger retry |

### 4d — Retry for New Violations (max 1)

If 🆕 New violations were introduced:
1. Group the new violations into fix units (same logic as Step 1)
2. Dispatch ONE targeted retry to fix ONLY the new violations
3. Re-verify after retry (no further retries — report final state)

If no new violations, skip to Step 5.

## Step 5 — Report

Output a concise summary directly to the user (no file output — this is a fast gate):

```
## Fix Check Results

### Tooling
- ruff/eslint/dart analyze: ✅ Pass / ❌ {N} errors remaining
- Type check: ✅ Pass / ❌ {N} errors remaining

### Violations Fixed
| File | Issue | Status |
|------|-------|--------|
| services/foo.py | Missing return type | ✅ Fixed |
| services/bar.py | DB query in service | ✅ Fixed |
| components/Baz.tsx | File over 200 lines | ⚠️ Remaining (now 195 lines but has new issue) |

### Summary
- ✅ Fixed: {X}/{N}
- ⚠️ Remaining: {Y}/{N}
- 🆕 New (after retry): {Z}

### Verdict
✅ ALL CLEAR — all violations resolved. Ready for `/check` re-run to confirm.
⚠️ PARTIAL — {Y} violations remain. Manual attention needed.
❌ REGRESSIONS — {Z} new violations introduced. Review before proceeding.
```

If the verdict is not ✅, list the specific remaining/new issues with file paths.

## Design Principles

- **Scoped, not full**: Only fix what `/check` flagged. Don't expand scope.
- **Right agent for right stack**: Route `.dart` to flutter, `.py` to python-fastapi, `.tsx` to the correct React agent. Never mix.
- **Context before dispatch**: The orchestrator reads violating files and searches for existing enums/types BEFORE writing fix instructions. Vague prompts produce bad fixes.
- **Concrete HOW TO FIX**: Every subagent prompt includes exact enum names, import paths, and before/after transformations. "Fix the raw strings" is forbidden — "Replace `"purchase_order"` with `ScanEntityType.PURCHASE_ORDER`" is required.
- **Self-verification**: Every subagent gets the per-stack checklist covering: raw strings in dispatch, silent no-ops, fragile serialization, placeholder UI text, fake tracker refs, entity ID conflation, hardcoded colors, and file length.
- **Verify, don't trust**: After each subagent, READ modified files and run regression Greps. Don't trust the subagent's "all done" report.
- **One retry max**: After fixes, re-check once. If new violations, retry once. Then report. No infinite loops.
- **No file output**: Report in conversation. This is a fast gate companion to `/check`, not an audit artifact.
- **Tooling first**: Let formatters and linters handle what they can (Phase 0) before dispatching subagents for architectural fixes.
