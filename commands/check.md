# Pre-Merge Architecture Check

You are a lightweight architecture gate. Your job is to review ONLY the files changed since the base branch and flag any rule violations BEFORE they get merged. This is NOT a full review — it's a fast, focused check on the delta.

## Step 0 — Determine the Diff Scope

1. Detect the base branch: run `git rev-parse --verify main 2>/dev/null || git rev-parse --verify master` to find the main branch name.
2. Get the list of changed files: run `git diff --name-only --diff-filter=ACMR $(git merge-base HEAD <base-branch>)..HEAD` to find all Added, Copied, Modified, or Renamed files.
3. If there are no changed files, tell the user "No changes detected against the base branch" and stop.
4. Filter to only source files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.dart`) — ignore config files, docs, assets, lockfiles, generated files (`.g.dart`, `.freezed.dart`).
5. Detect the project type from the changed files' paths and extensions.

Report to the user: "Checking {N} changed files against architecture rules..."

## Step 0.5 — Report lifecycle stage to ShipBoard (if MCP available)

If `.shipboard.yml` exists in the repo root and `.mcp.json` registers `shipboard`:

1. Read `.shipboard.yml`; extract `component.name`.
2. Call:
   ```
   shipboard(action="report_lifecycle_stage",
             component=<component.name>,
             stage="verify_iterate",
             sub_state="verify",
             source="check",
             pr_number=<if known, else null>)
   ```
3. On failure (no MCP, server down, network error), append a one-line JSON entry to `.shipboard/pending_events.log` and continue. Reporting is best-effort — it MUST NOT block the actual command execution.

If `.shipboard.yml` does not exist, skip this step silently (the user hasn't run `/init-component` yet — fine; the harness still works).

## Step 1 — Run Tooling on Changed Files Only

Run the project's code quality tools scoped to the changed files where possible:

**Python/FastAPI:**
```bash
# Type check only changed files
uv run pyright <changed .py files>

# Lint only changed files
uv run ruff check <changed .py files>

# Import rules (must run on whole project — fast enough)
uv run lint-imports

# Run tests (full suite — changed code may break existing tests)
uv run pytest
```

**Next.js / Vite React:**
```bash
# Type check (must be whole project — TS is global)
pnpm tsc --noEmit

# Lint only changed files
pnpm eslint <changed .ts/.tsx files>

# Run tests
pnpm vitest run
```

**Flutter:**
```bash
# Static analysis (whole project — Dart analyzer is global)
dart analyze --fatal-infos

# Format check only changed files
dart format --set-exit-if-changed <changed .dart files>

# Run tests
flutter test
```

If any tool fails, report the errors but continue checking — don't stop at the first failure.

## Step 1.5 — Security Scanning (SAST + SCA)

Run security-focused analysis on changed files. These catch vulnerabilities that linters miss.

**Python/FastAPI:**
```bash
# SAST — Security linter (only changed files)
uv run bandit <changed .py files> -c pyproject.toml

# SCA — Dependency vulnerability check (if requirements changed)
# Only run if pyproject.toml, uv.lock, or requirements*.txt changed
uv run pip-audit
```

**Next.js / Vite React:**
```bash
# Dependency vulnerability check (if lockfile changed)
# Only run if package.json or pnpm-lock.yaml changed
pnpm audit --audit-level=moderate
```

**Flutter/Dart:**
```bash
# SAST — Dart analyzer already runs, but check security-specific rules
# The standard `dart analyze` catches some issues, but add explicit checks:
dart analyze --fatal-infos

# SCA — Dependency vulnerability check (if pubspec changed)
# Only run if pubspec.yaml or pubspec.lock changed
# Option 1: Google's OSV scanner (recommended)
osv-scanner --lockfile=pubspec.lock

# Option 2: If osv-scanner not available, check pub.dev advisories manually
dart pub outdated --mode=security
```

**Flutter-specific security checks during code review:**
- Hardcoded API keys in Dart code (check for strings matching `sk-*`, `api_*`, etc.)
- Insecure HTTP (non-HTTPS) URLs in API clients
- Missing certificate pinning for sensitive endpoints
- Sensitive data stored in SharedPreferences without encryption
- Debug flags left enabled (`kDebugMode` checks missing)
- Platform channel data not validated

**All projects (if any files changed):**
```bash
# Secrets detection — check for accidentally committed secrets
# Only run on changed files to keep it fast
git diff --name-only $(git merge-base HEAD <base-branch>)..HEAD | xargs gitleaks detect --no-git --source
```

**Security findings classification:**
- 🔴 **CRITICAL**: Hardcoded secrets, SQL injection, command injection, known CVE in dependency
- 🟡 **WARNING**: Weak crypto, missing input validation, medium-severity CVE
- 🔵 **NOTE**: Informational findings, low-severity issues

If CRITICAL security findings are found, the verdict MUST be "DO NOT MERGE" regardless of other results.

## Step 2 — Architecture Check on Changed Files

Read each changed source file and check against the rules. This is NOT a full Grep-over-everything scan — only read and analyze the changed files.

Group checks by what's relevant to each file's location:

### For files in `routers/` or `app/` (routing layer):
- Does the router/page exceed line limits? (50 lines for pages, 200 for routers)
- Does the router have `response_model` and `status_code` on every endpoint?
- Does the router use `Annotated` type aliases for DI (not raw `Depends()`)?
- Does the router contain business logic or DB queries? (should delegate to services)
- Does the page import directly from other features? (should not)
- Does the router raise domain exceptions instead of HTTPException? (router CAN use HTTPException)

### For files in `services/`:
- Does the service import `Session`, `HTTPException`, or ORM models directly?
- Does any method (including private `_foo` methods) receive `Session` or `db` as a parameter? (Session belongs in repositories via DI — not even in private methods)
- Does the service call `self._uow.commit()`, `db.commit()`, `db.flush()`, `db.rollback()`, or `db.add()`? (transaction management belongs in repositories)
- Does the service mutate ORM model attributes directly? (should delegate to repository methods)
- Does the service depend on other services? (should use workflows)
- Are all methods fully typed (params + return)?
- Does any method return `dict`, `list[dict]`, or `dict[str, Any]`? (must return typed Pydantic schemas)
- Does it pass raw dicts to repository calls? (should pass typed schemas or params objects)
- Does it use raw string comparisons or raw strings in FSM `transition()` calls? (must use enums)
- Does the class have an `__init__` accepting repository interfaces? (no constructor = DIP violation)
- Is there a module-level `service = ServiceClass()` singleton? (must use Depends() DI)
- Does it use inline imports to access repository singletons? (e.g., `from ..repositories.foo import foo_repo` inside a method — must use DI)
- Does it have more than 12 public methods? (god service — split by responsibility)
- Are there `Any` type hints without justification comments?
- Does any method eagerly load/call multiple repositories when only one branch is used? (use strategy/dispatch pattern — don't evaluate all branches)
- Are there hardcoded `limit=N` values without proper pagination? (should use paginated query pattern)
- Do parameters use `str` or `str | None` for values from a fixed set? (should use `StrEnum`)

### For files in `repositories/`:
- Does the repository contain business logic?
- Does it use `session.query()` instead of `select()`?
- Does it import from services or routers?

### For files in `schemas/`:
- Are schemas separated by purpose (Create/Update/Out)?
- Do custom validators exist and are they tested? (check if corresponding test file exists)

### For files in `components/` or `features/` (React/Next.js/Vite):
- Does the component exceed 150 lines?
- Does it have named props type (`<Name>Props`)?
- Does it have `useEffect` without a WHY comment?
- Does it have 3+ `useState` calls? (suggest custom hook)
- Does it use `getByTestId` heavily in co-located tests? (suggest better queries)
- Does a feature import from another feature?
- Does it use `Record<string, unknown>`, `Record<string, any>`, `{ [key: string]: any }`, or plain untyped objects for form data, wizard step results, or callback payloads? (must use Zod schema or typed interface)
- Does it compare status/state values using raw strings (e.g., `status === 'pending'`, `case 'active':`)? (must use const objects or string union types)

### For files in `features/*/` (Flutter — all layers):
- Does the file import from another feature? (e.g., `import 'package:app/features/items/...'` in a transfers feature file — cross-feature import violation)
- Does it use `print()` or `debugPrint()` without `kDebugMode` guard? (debug logging in production)

### For files in `features/*/presentation/` (Flutter):
- Does the widget import from `data/` directly? (should go through domain/)
- Does it call a repository provider directly? (e.g., `ref.read(fooRepositoryProvider)` — should go through a use case or dedicated provider)
- Does it contain HTTP/API calls? (should be in data layer)
- Does it use `setState` for server data? (should use Riverpod/Bloc)
- Does it use `ChangeNotifier`? (should use Riverpod/Bloc)
- Does it use `StateNotifierProvider`? (legacy — use `NotifierProvider` or `AsyncNotifierProvider`)
- Does it have `ref.read` in `build()` method? (should be `ref.watch`)
- Does a detail page mutate a list provider? (e.g., `ref.read(ordersListProvider.notifier)` in a detail page — cross-mutation violation)
- Does it use `Map<String, Object?>` or `Map<String, dynamic>` for form data, wizard results, or summary fields? (must use typed data class — `@freezed` or plain class)
- Does it compare status/state values using raw strings (e.g., `== 'received'`, `case 'partially_received':`)? (must use enum-backed comparisons — parse to enum at data layer boundary)
- Does it contain domain object construction logic (e.g., `_buildCreateRequest()` in a provider/widget)? (domain construction belongs in use cases or domain layer)
- Does it use `?? 0`, `?? ''`, or `?? defaultValue` on required domain fields? (silent fallback — validate before constructing domain objects)
- Does it hardcode `Color(0xFF...)` literals? (must use Theme tokens or named colors from `core/theme/`)
- Are the same string literals (wizard types, entity types) scattered across 3+ files? (consolidate into a single enum or constants file)

### For files in `features/*/domain/` (Flutter):
- Does it import Flutter packages (`package:flutter/...`)? (domain must be pure Dart — move IconData/Color to presentation extension)
- Does it import from `data/`? (dependency inversion violation)
- Are models using `@freezed`? (domain models should be immutable)
- Do entities have `status` fields typed as `String`? (should be enum)
- Do enums have `.fromString()` with silent fallback? (should throw on unknown values)

### For files in `features/*/data/` (Flutter):
- Do DTOs map to domain entities? (never expose DTOs above data layer)
- Does it use raw string comparisons instead of enums?
- Do DTOs have `Map<String, dynamic>?` fields for nested objects? (should use typed nested DTOs)
- Does it import from `presentation/`? (circular dependency — data must not import from presentation)

### For files in `router/` or `*_router.dart` (Flutter):
- Does it use unguarded `!` on `state.pathParameters['id']`? (should use `tryParse` with fallback)
- Are all navigation targets (from UI files with `context.push`/`context.go`) defined as routes?
- Is there a fallback 404 route?

### For files in `state_machines/` or `enums/`:
- Are all transitions tested? (check for corresponding test file)

### For test files:
- Do test names follow the spec pattern? (`test_<action>_<scenario>_<expected>` or `it("should ... when ...")`)
- Is AAA structure visible?
- Are there hardcoded dicts/values instead of factories?
- Does the test file exceed 300 lines? (split by concern into multiple test files)
- Does the test file mirror the source structure?

### For ALL changed files:
- Does the file exceed 200 lines?
- Are there functions over 30 lines?
- Are there functions with 6+ parameters?
- Are there `# type: ignore` / `@ts-ignore` / `eslint-disable` without justification?
- Are there `TODO` / `FIXME` / `HACK` comments without a tracker reference? (must be `// TODO(#1234): reason`)
- Are there `print()` / `debugPrint()` calls in production code?
- Is `Any` / `any` used without justification?
- Are type annotations complete?

### Security checks for ALL changed files (see `rules/shared/security.md`):
- **Injection risks**:
  - Are there f-string/format SQL patterns? (must use parameterized queries)
  - Is `eval()`, `exec()`, or `subprocess.Popen(shell=True)` used?
  - Is `yaml.load()` used instead of `yaml.safe_load()`?
- **Secrets**:
  - Are there hardcoded strings matching: password, secret, api_key, token, credential?
  - Are there strings matching patterns: `sk-*`, `pk_*`, `ghp_*`, `aws_*`?
- **Crypto**:
  - Is `random` module used for security purposes? (must use `secrets`)
  - Is MD5/SHA1 used for security? (must use SHA-256+)
- **Auth**:
  - Do new endpoints have auth checks?
  - Are there direct object references without ownership checks?
- **Error handling**:
  - Do except blocks expose internal details in responses?

### Dead code and bloat checks:
- Are there unused imports? (ruff/pyflakes will catch these)
- Are there unreachable code paths after return/raise?
- Are there duplicated code blocks (>10 lines appearing 2+ times)?
- Are there commented-out code blocks >5 lines? (delete or restore, don't leave zombie code)

## Step 3 — Plan Gap Analysis (if implementation in progress)

If `IMPLEMENTATION_PLAN.md` exists at the project root, check for drift between the plan and reality:

1. **Read `IMPLEMENTATION_PLAN.md`** — parse the phases and their expected files/tasks
2. **Read `IMPLEMENTATION_STATUS.md`** (if it exists) — parse current completion status
3. **Identify the current phase** — look at which phase is marked in-progress or find the first incomplete phase
4. **For the current phase, check**:
   - Are all expected files from the plan present in the changed files or already committed?
   - Are there changed files NOT mentioned in the plan? (scope creep)
   - Are there plan items marked complete that don't match the actual file state?

Report as a dedicated section:

```
### Plan Alignment (Phase {N})
| Status | Plan Item | Actual State |
|--------|-----------|--------------|
| ✅ | Create `features/orders/domain/entities/order.dart` | File exists, 45 lines |
| ⚠️ | Create `features/orders/data/models/order_dto.dart` | File exists but missing toEntity() |
| ❌ | Create `features/orders/presentation/pages/order_page.dart` | Not found |
| ➕ | (not in plan) | `features/orders/utils/helpers.dart` was added — scope creep? |
```

If there are ❌ missing items or ➕ scope creep, flag in the verdict:
- Missing plan items → "Phase {N} incomplete: {list}"
- Scope creep → "Files added outside plan: {list} — intentional?"

**Skip this step** if no `IMPLEMENTATION_PLAN.md` exists — this is optional context for in-progress implementations.

## Step 4 — Cross-File Consistency Check

Some violations only appear when looking at relationships between changed files:

1. **New endpoints without tests**: If a new router/endpoint was added, does a corresponding test file exist?
2. **New service methods without tests**: Same check for services.
3. **New stateful entity without FSM**: If a new model with a `status` field was added, is there a state machine?
4. **New enum values without FSM update**: If an enum was extended, was the FSM transition map updated too?
5. **New feature without schema separation**: If a new domain was added, does it have separate Create/Update/Out schemas?
6. **Missing ARCHITECTURE.md update**: If a new module/directory was added, was ARCHITECTURE.md updated?

## Step 5 — Report

Output a concise report directly to the user (do NOT write a file — this is a quick check, not an audit artifact):

```
## Pre-Merge Check — {N} files analyzed

### Tooling
- pyright/tsc: ✅ Pass / ❌ {N} errors
- ruff/eslint: ✅ Pass / ❌ {N} errors
- lint-imports: ✅ Pass / ❌ {N} violations
- tests: ✅ Pass / ❌ {N} failures

### Architecture Violations
| Severity | File | Issue | Rule |
|----------|------|-------|------|
| 🔴 | ... | ... | ... |
| 🟡 | ... | ... | ... |

### Missing Companions
| Source File | Missing |
|------------|---------|
| routers/orders.py (new) | No test file found |
| services/payment_service.py (new method: charge) | No error-path test |
| models/invoice.py (has status field) | No FSM definition |

### Plan Alignment (if IMPLEMENTATION_PLAN.md exists)
**Phase {N}: {title}**
| Status | Plan Item | Actual State |
|--------|-----------|--------------|
| ✅ | ... | ... |
| ⚠️ | ... | ... |
| ❌ | ... | Not found |
| ➕ | (not in plan) | Scope creep: {file} |

### Verdict
✅ READY TO MERGE — no violations found.
⚠️ REVIEW BEFORE MERGING — {N} warnings found. Consider fixing before merge.
❌ DO NOT MERGE — {N} critical violations found. Fix these first.

{If plan gaps exist:}
⚠️ PLAN DRIFT — Phase {N} has {X} missing items and {Y} files outside plan scope.

### Next action

Detect the current branch via `git rev-parse --abbrev-ref HEAD` and propose accordingly. Only emit a proposal if the verdict is ✅ or ⚠️ — for ❌ verdicts, instead say "fix the critical issues first; do not commit or PR yet."

**On a feature / phase branch (formal mode — recommended):**
```bash
git push -u origin <current-branch>
gh pr create \
  --title "feat: <one-line summary derived from the diff or current phase>" \
  --body "$(cat <<'EOF'
## Summary
<bullet points from the diff>

## Phases inside this PR (if from /implement-phase)
- [x] Plan
- [x] Implement
- [x] Test
- [x] Review (this /check)
- [ ] Deploy
EOF
)"
```
After CI is green and a reviewer approves, merge with `gh pr merge --auto --squash`.

**On main / master (fast mode — solo prototypes only):**
```bash
git add . && git commit -m "<feat|fix|chore>: <summary>"
```
Note this skips code review and per-change CI; only suitable for one-shot prototype work. See `docs/USERGUIDE.md` if the project has one for the formal-vs-fast mode discussion.

If the verdict is ❌, briefly list the top 3 most critical issues and what to fix — do NOT include a "next action" proposal in that case.

## Design Principles

- **Speed over thoroughness**: This is not a full review. Check only changed files. Skip anything that would take more than a few minutes.
- **No file output**: Report directly in the conversation. This is a gate, not an audit.
- **Err toward warnings**: If unsure whether something is a violation, flag as 🟡 Warning, not 🔴 Critical. The full review pipeline catches what this misses.
- **Don't block on Info**: Only 🔴 Critical findings should produce a "DO NOT MERGE" verdict. Warnings are advisory.
