# Validate Architecture Review Implementation

You are a review validation orchestrator. Your job is to verify that ALL findings and migration plan items from `REVIEW.md` were fully implemented — across every affected file, endpoint, and module — with zero gaps.

## Step 0 — Pre-flight Checks

1. Read `REVIEW.md` at the project root. If it doesn't exist, tell the user to run `/review-architecture` first and stop.
2. Check the `**Date:**` field in REVIEW.md. If it is older than 7 days, warn the user: "This review is from {date}. The codebase may have changed. Consider running `/review-architecture` for a fresh audit before validating." Wait for confirmation before proceeding.
3. Detect the project type using the same logic as `/review-architecture` (check for `pyproject.toml`, `next.config.*`, `vite.config.*`, `pubspec.yaml` with `flutter`, `package.json`).
3. **Parse the optional phase argument.** This command accepts an optional phase number: `/validate-review N` validates only the fix units from `FIX_PLAN_PHASE_{N}.md`. Without an argument, validate every actionable finding from `REVIEW.md` (the original behavior).
4. Parse the **Detailed Findings** tables and the **Migration Plan** checklist from REVIEW.md. Build an internal list of every actionable finding (🔴 Critical and 🟡 Warning severity) and every migration plan item. **If a phase number was supplied**, narrow this list to only the findings whose grep patterns appear in `FIX_PLAN_PHASE_{N}.md` — the user is asking "did THIS phase's PR actually resolve its scope?", not "is the whole audit clean?".
5. **Check for FIX_PLAN.md / FIX_PLAN_PHASE_*.md** at the project root.
   - If `FIX_PLAN.md` is single-phase, parse its **Deferred Items** section.
   - If multi-phase, parse the overview's deferred list AND the phase file (if a phase number was supplied — the per-phase file may have its own deferrals).
   Any finding or migration plan item that matches a deferred item will be marked `⏭️ DEFERRED` instead of `❌ FAIL`. Deferred items are **excluded from the completion percentage** — they were intentionally postponed, not forgotten. They are still listed in the report for visibility.

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

If `.shipboard.yml` exists in the repo root and `.mcp.json` registers `shipboard`:

1. Read `.shipboard.yml`; extract `component.name`.
2. Call:
   ```
   shipboard(action="report_lifecycle_stage",
             component=<component.name>,
             stage="verify_iterate",
             sub_state="verify-audit",
             source="validate-review",
             pr_number=<if known, else null>)
   ```
3. On failure (no MCP, server down, network error), append a one-line JSON entry to `.shipboard/pending_events.log` and continue. Reporting is best-effort — it MUST NOT block the actual command execution.

If `.shipboard.yml` does not exist, skip this step silently (the user hasn't run `/init-component` yet — fine; the harness still works).

## Step 1 — Build the Verification Matrix

For each actionable finding from REVIEW.md, define a verification check:

| Finding Type | How to Verify Completeness |
|---|---|
| Missing type annotations | Grep for `def ` without `->` (Python) or `function` without `: ReturnType` (TS) in ALL source files, not just the ones listed in the finding |
| Services returning raw dicts | Grep for `-> dict`, `-> list[dict`, `-> dict[str` in ALL service files — services must return typed Pydantic schemas |
| Services receiving Session | Grep for `Session` in method signatures in services/ — `def .*Session` — services must not receive or import Session |
| Services managing transactions | Grep for `db.commit(`, `db.flush(`, `db.rollback(`, `db.add(` in services/ — transaction management belongs in repositories |
| Module-level service singletons | Grep for `= <ClassName>()` at module level in services/ — must use Depends() DI chain |
| Services missing DI constructor | Check if service classes have `__init__` accepting Protocol/ABC repository interfaces — no constructor = DIP violation |
| Raw strings in FSM transitions | Grep for `transition.*"` in services/ — FSM calls must use enum values, not string literals |
| Import violations | Re-run the same Grep patterns from the review (e.g., routers importing from repositories) across ALL files in the relevant directory |
| Missing layer/directory | Glob to confirm the directory exists AND contains the expected files |
| Raw string comparisons | Grep for string literal comparisons (`== "active"`, `=== "pending"`, etc.) in ALL source files |
| Missing tests | For each source module, verify a corresponding test file exists AND covers the required scenarios |
| Missing enums/FSMs | Verify enum files exist AND all previous raw-string usages now reference the enum |
| Missing docs | Verify ARCHITECTURE.md sections exist and decisions.md has entries |
| File too long | Re-check line counts of flagged files |
| Migration plan items | Each `- [ ]` item: verify the described change was made |

**CRITICAL**: Do not just check the specific files mentioned in the original finding. The original review may have only listed examples. You must scan ALL files in the relevant scope to catch anything that was missed.

## Step 2 — Launch Parallel Verification Agents

Use the Task tool to spawn verification agents in parallel (use `subagent_type: "Explore"` and `model: "sonnet"`).

Group checks by category (same 5 categories as the review). Each agent receives:
- The original findings for its category from REVIEW.md
- Instructions to re-scan the ENTIRE codebase for the same patterns
- The expected state after fixes (e.g., "zero routers should import from repositories")

Each agent must return results as:

```markdown
| Status | Original Finding | Scope Checked | Files Still Affected | Details |
|--------|-----------------|---------------|---------------------|---------|
| ✅ PASS | {finding} | {N files checked} | 0 | Fully resolved |
| ⚠️ PARTIAL | {finding} | {N files checked} | {list} | Fixed in some files but not all |
| ❌ FAIL | {finding} | {N files checked} | {list} | Not addressed |
| ⏭️ DEFERRED | {finding} | — | — | Explicitly deferred in FIX_PLAN.md (excluded from completion %) |
| ⏭️ SKIPPED | {finding} | — | — | Not applicable to this project |
```

## Step 3 — Run Tooling Verification

Run the project's code quality tools as an independent verification layer. These are the **source of truth** — they catch issues that Grep-based scanning misses (e.g., type errors across module boundaries, import cycle violations, security issues).

Detect which suite to run based on project type:

**Python/FastAPI:**
```bash
uv run pyright .          # Type checking — strict mode
uv run ruff check .       # Linting (do NOT --fix, just report)
uv run bandit -r src/ -c pyproject.toml  # Security
uv run lint-imports       # Architectural import rules
uv run radon cc src/ -a -nc  # Complexity
```

**Next.js:**
```bash
pnpm tsc --noEmit         # Type checking
pnpm eslint .             # Linting (do NOT --fix, just report)
pnpm vitest run           # Tests pass
```

**Vite/React:**
```bash
pnpm tsc --noEmit         # Type checking
pnpm eslint .             # Linting (do NOT --fix, just report)
pnpm vitest run           # Tests pass
```

**Flutter:**
```bash
dart analyze --fatal-infos          # Static analysis — strict mode
dart format --set-exit-if-changed . # Formatting (do NOT --fix, just report)
flutter test                        # Tests pass
```

**IMPORTANT:** Run tools in **report-only mode** (no `--fix`, no `--write`). This is validation, not fixing. We want to know the truth, not silently auto-fix.

For each tool, capture:
- Exit code (0 = pass, non-zero = issues found)
- Number of errors/warnings
- List of affected files

If a tool is not installed, note it as `⏭️ NOT INSTALLED` and move on.

Map tool results back to review categories:
| Tool | Maps to Category |
|---|---|
| pyright / tsc / dart analyze | Typing & Style |
| ruff / eslint / dart format | Typing & Style + Architecture (import rules) |
| lint-imports | Architecture & SoC |
| bandit | Documentation & Debt (security) |
| radon | Documentation & Debt (complexity) |
| vitest / pytest / flutter test | Testing |

Tool failures that correspond to review findings should be marked as ❌ FAIL in the validation table, even if the Grep-based check passed. **Tools override Grep.** A finding is only truly fixed when both Grep AND tooling confirm it.

### Test Completeness Audit

Beyond just running the test suite (pass/fail), perform a systematic coverage completeness check. This is critical because a test suite can pass with 100% green while covering only 30% of the behavior.

**Step 3a — Build the coverage matrix:**

1. **Enumerate source modules**: Glob for all service files, router files, FSM files, and schema files.
2. **Enumerate public methods**: For each service file, Grep for public method signatures (`async def ` / `def ` not starting with `_`).
3. **Enumerate test files**: Glob for corresponding test files (`tests/services/test_*.py`, `tests/routers/test_*.py`, etc.).
4. **Cross-reference**: For each public service method, check if at least one test function references it (by name or scenario).

**Step 3b — Check per the testing rules:**

| Requirement | How to Verify |
|---|---|
| Every public service method: 1 happy + 1 error test | Cross-reference method names against test function names; look for `raises` / `error` / `invalid` in test names for error paths |
| Every FSM transition tested (valid + invalid) | If `state_machines/` exists, enumerate transitions and check for corresponding `test_*_transition_*` functions |
| Every custom Pydantic validator tested | Grep for `@validator` / `@field_validator` in schemas, check for corresponding test functions |
| Test names follow spec pattern | Grep test files for `def test_` and verify names match `test_<action>_<scenario>_<expected>` — flag vague names like `test_create`, `test_1`, `test_it_works` |
| Test structure mirrors src/ | Compare directory trees: every `src/services/foo.py` should have `tests/services/test_foo.py` |
| Factories used (no hardcoded dicts) | Grep test files for raw dict literals in assertions (`{"id":`, `dict(`) and check if factory fixtures exist (`conftest.py`, `factories.py`) |

**Step 3c — For React/TS projects, additionally check:**

| Requirement | How to Verify |
|---|---|
| Components tested for rendering + interactions | Each component file has a co-located `.test.tsx`; tests use `render()` and user event queries |
| Queries use role/label/text (not test-id) | Grep test files for `getByTestId` — should be rare; `getByRole` / `getByLabelText` should dominate |
| No implementation testing | Grep for `useState` / `setState` / `className` in test files — these suggest testing internals |
| MSW used for API mocking | Grep for `msw` or `setupServer` in test utils; flag `jest.mock.*fetch` or `vi.mock.*axios` patterns |

**Step 3d — For Flutter projects, additionally check:**

| Requirement | How to Verify |
|---|---|
| Test structure mirrors lib/ | Compare `lib/features/` tree against `test/features/` tree — every source file should have a `_test.dart` counterpart |
| Widget tests use testWidgets | Grep test files for `testWidgets(` — widget tests should not use plain `test(` |
| Finder priority followed | Grep test files for `find.byKey` — should be rare; `find.text` / `find.byType` should dominate |
| Mocktail used for mocking | Grep for `mocktail` in test imports; flag manual mock classes without `Mock` mixin |
| Bloc/Cubit state transitions tested | For each Bloc/Cubit, check test files for both valid state transitions AND invalid transition attempts |
| Factories in test/helpers/ or test/factories/ | Check if shared test data factories exist — flag inline hardcoded values in test assertions |
| Group names match class under test | Grep for `group(` in test files — group name should match the class/widget being tested |

Report results as an additional table in the validation output:

```markdown
### Test Coverage Matrix
| Source Module | Public Methods | Tests Found | Happy Path | Error Path | Coverage |
|--------------|---------------|-------------|------------|------------|----------|
| services/order_service.py | 5 | 3 | 3 | 1 | ⚠️ 60% |
| services/user_service.py | 4 | 4 | 4 | 4 | ✅ 100% |
| routers/orders.py | 6 | 2 | 2 | 0 | ❌ 33% |
```

## Step 4 — Verify Migration Plan Completion

Separately, check each migration plan item from REVIEW.md:
- For each `- [ ]` item, determine if the described change was implemented
- Mark as ✅ done, ⚠️ partial, or ❌ not done
- For partial items, list specifically what was done and what remains

## Step 4.5 — Security Confidence Challenge (Devil's Advocate)

Research shows developers using AI assistants are **more confident** in their code despite it being **less secure** (Stanford/Boneh, ACM CCS 2023). This step explicitly challenges that false confidence.

For each "fixed" security-related finding, ask these adversarial questions:

### Injection Fixes
- If input validation was added: What if the attacker uses Unicode normalization tricks?
- If parameterized queries were added: Are ALL query entry points covered, including dynamic ORDER BY/LIMIT?
- If shell=False was set: Are there other subprocess calls that were missed?

### Auth/Authz Fixes
- If ownership checks were added: What about admin override paths? Batch operations?
- If rate limiting was added: Can an attacker use distributed IPs to bypass?
- If CSRF protection was added: Does it cover all state-changing endpoints including AJAX?

### Crypto Fixes
- If secrets.token was used: Is the token length sufficient? Is it stored securely?
- If password hashing was improved: Are existing weak hashes being migrated?

### General Challenge Questions
For EACH security fix, document answers to:
1. **Could this fix introduce a NEW vulnerability?** (e.g., fixing SQL injection but adding XSS in error messages)
2. **Does the fix handle edge cases?** (empty input, very long input, null bytes, unicode)
3. **Would a malicious input bypass this fix?** (think like an attacker)
4. **Is the fix applied consistently?** (all similar code paths, not just the reported one)

If ANY challenge question reveals a gap, mark the finding as ⚠️ Partial, not ✅ Pass.

Add a section to REVIEW_VALIDATION.md:
```markdown
### 8. Security Confidence Challenge
| Finding | Fix Applied | Challenge Question | Answer | Confidence |
|---------|-------------|-------------------|--------|------------|
| SQL injection in search | Parameterized query | Dynamic ORDER BY covered? | Yes, uses allowlist | ✅ High |
| Missing auth on /admin | Added role check | Batch endpoints covered? | No, /admin/bulk still open | ⚠️ Gap found |
```

## Step 5 — Consolidate into REVIEW_VALIDATION.md

After all agents complete, write `REVIEW_VALIDATION.md` at the project root with this format:

```markdown
# Review Validation Report — {project_name}

**Date:** {today's date YYYY-MM-DD}
**Review date:** {date from REVIEW.md}
**Project type:** {detected type(s)}

## Validation Summary

| Category | Findings Checked | ✅ Pass | ⚠️ Partial | ❌ Fail | ⏭️ Deferred | Completion* |
|----------|-----------------|---------|------------|---------|-------------|------------|
| Architecture & SoC | N | N | N | N | N | N% |
| Typing & Style | N | N | N | N | N | N% |
| State & Enums | N | N | N | N | N | N% |
| Testing | N | N | N | N | N | N% |
| Documentation & Debt | N | N | N | N | N | N% |
| Tooling Checks | N | N | N | N | N | N% |
| **Migration Plan** | N | N | N | N | N | N% |
| **TOTAL** | N | N | N | N | N | **N%** |

*Completion % = Pass / (Pass + Partial + Fail). Deferred items are excluded from the denominator.

## Overall Verdict

{One of:}
- ✅ **ALL CLEAR** — All findings addressed, migration plan complete. No action needed.
- ⚠️ **GAPS FOUND** — {N} findings partially or not addressed. Run `/heal-review` to fix remaining gaps.
- ❌ **SIGNIFICANT GAPS** — {N} critical findings unresolved. Run `/heal-review` to fix.

## Detailed Results

### 1. Architecture & Separation of Concerns
{Agent 1 validation table}

### 2. Typing & Style
{Agent 2 validation table}

### 3. State Management & Enums
{Agent 3 validation table}

### 4. Testing Quality
{Agent 4 validation table}

### 5. Documentation & Cognitive Debt
{Agent 5 validation table}

### 6. Tooling Verification
| Tool | Status | Errors | Warnings | Key Issues |
|------|--------|--------|----------|------------|
| pyright / tsc / dart analyze | ✅ Pass / ❌ {N} errors | N | N | {summary} |
| ruff / eslint / dart format | ✅ Pass / ❌ {N} errors | N | N | {summary} |
| lint-imports | ✅ Pass / ❌ {N} errors | N | N | {summary} |
| bandit | ✅ Pass / ❌ {N} errors | N | N | {summary} |
| vitest / pytest / flutter test | ✅ Pass / ❌ {N} failures | N | N | {summary} |
| radon | ✅ Pass / ⚠️ {N} complex | N | N | {summary} |

### 7. Migration Plan Items
| Status | Phase | Item | Details |
|--------|-------|------|---------|
| ✅/⚠️/❌ | Phase N | {item text} | {what was done / what remains} |

## Remaining Gaps (for /heal-review)

{List only ⚠️ PARTIAL and ❌ FAIL items, grouped by category, with enough context for the healing command to act on them. Do NOT include ⏭️ DEFERRED items here — they are listed separately below.}

### Gap 1: {short title}
- **Category:** {category name}
- **Original finding:** {from REVIEW.md}
- **Current state:** {what was done so far}
- **Remaining work:** {specific files and changes still needed}
- **Files affected:** {explicit list}

### Gap 2: ...

## Deferred Items (not in scope for /heal-review)

{List all ⏭️ DEFERRED items from FIX_PLAN.md. These are intentionally postponed and should NOT trigger `/heal-review`. They will be addressed in a future release cycle.}

| Item | Reason for Deferral |
|------|-------------------|
| {item} | {reason from FIX_PLAN.md} |
```

## Step 6 — Report to User

After writing the file, summarize:
1. Overall completion percentage
2. The verdict (ALL CLEAR / GAPS FOUND / SIGNIFICANT GAPS)
3. If gaps exist, recommend running `/heal-review` and list the top 3 most impactful gaps
