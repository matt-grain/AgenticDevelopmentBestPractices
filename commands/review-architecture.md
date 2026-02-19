# Architecture Review

You are an architecture review orchestrator. Your job is to audit the current project against established coding standards and produce a prioritized gap analysis with a migration plan.

## Step 0 — Archive Previous Review Cycle

Before starting a new review, check if artifacts from a previous review cycle exist at the project root:
- `REVIEW.md`
- `REVIEW_VALIDATION.md`
- `REVIEW_FIX_LOG.md`

If any of these exist:
1. Create a `reviews/` directory at the project root if it doesn't exist.
2. Move all existing review artifacts into `reviews/` with a date prefix from the previous REVIEW.md's date field (e.g., `reviews/2025-06-15_REVIEW.md`, `reviews/2025-06-15_REVIEW_VALIDATION.md`, `reviews/2025-06-15_REVIEW_FIX_LOG.md`).
3. If the date cannot be parsed, use the file's last modified date.

This ensures a clean slate for the new cycle while preserving history for reference.

## Step 1 — Detect Project Type

Use Glob and Read to scan the project root for these marker files:
- `pyproject.toml` → check if `fastapi` appears in dependencies → **Python/FastAPI**; otherwise → **Python (generic)**
- `next.config.ts` or `next.config.js` or `next.config.mjs` → **Next.js**
- `vite.config.ts` or `vite.config.js` → **Vite/React**
- `package.json` (without Next/Vite config files) → **Generic JS/TS**

A project can be **mixed** (e.g., Python backend + React frontend). Detect all that apply.

Store the detected type(s) and the project name (from `package.json` name field, `pyproject.toml` project name, or the current directory name). You will inject this into each agent prompt below.

## Step 2 — Launch 5 Parallel Review Agents

Use the Task tool to spawn **all 5 agents in a single message** (parallel). Each agent must use `subagent_type: "Explore"` and `model: "sonnet"`.

Each agent receives its audit rules (embedded below), instructions to scan the codebase with Glob/Grep/Read, and a required output format.

**IMPORTANT**:
- When constructing each agent's prompt, replace `{detected_type}` with the actual detected project type string from Step 1. Do NOT pass the literal placeholder.
- Tell each agent to return findings as a markdown table with columns: `Severity | Finding | File(s) | Rule Violated | Recommendation`. Severity is one of: 🔴 Critical, 🟡 Warning, 🔵 Info.
- If an agent finds zero issues for a category, it should return the table header with a single row: `| 🔵 Info | No issues found | — | — | — |`
- Each agent should only audit rules relevant to the detected project type — skip inapplicable sections.

---

### Agent 1 — Architecture & Separation of Concerns

Prompt for this agent:

```
You are an architecture auditor. Analyze this project for structural and separation-of-concerns issues.

PROJECT TYPE: {detected_type}

RULES TO AUDIT AGAINST:

**For Python/FastAPI projects:**
- Must follow layered structure: routers/ → services/ → repositories/ → models/
- Routers handle HTTP only — no business logic, no DB queries, no direct model imports
- Routers: every endpoint must declare explicit `response_model` and `status_code`
- Routers: use `Annotated[T, Depends()]` type aliases for DI — no raw `Depends()` in signatures
- Services contain business logic — never import Session or execute queries
- Services must raise domain-specific exceptions — never `HTTPException` (that's a router concern)
- Services must not depend on other services — use workflows/ for multi-service orchestration
- Services should depend on Protocol/ABC abstractions, not concrete repository classes (DIP)
- Repositories encapsulate ALL DB queries — only layer that imports ORM models and Session
- Repositories must use SQLAlchemy 2.0 `select()` style — never legacy `session.query()`
- Schemas separate per purpose: Create, Update, Out, InDB, Patch — never reuse input as output
- Dependencies wired via Depends() chains: router → service → repository → session
- Workflows coordinate multiple services for complex processes
- One repository per aggregate root
- List endpoints must always paginate — never return unbounded `list[T]`
- Configuration must use `pydantic-settings` `BaseSettings` — check `config.py`

**For Next.js projects:**
- app/ contains ONLY route segments (page.tsx, layout.tsx, loading.tsx, error.tsx, route.ts)
- Pages are thin orchestrators under 50 lines — compose feature components
- features/ are self-contained vertical slices with own components, hooks, services, schemas, types
- Features MUST NOT import from other features
- components/ are stateless, presentational, reusable — no data fetching, no business logic
- services/ are typed API call functions — no UI concerns
- stores/ use Zustand for client state only — server state in TanStack Query
- Default to Server Components; push "use client" DOWN the tree
- Every route segment should have an `error.tsx` error boundary
- Environment variables validated with Zod in `lib/env.ts` — never access `process.env` directly elsewhere
- TanStack Query keys defined in central `query-keys.ts` per feature — not scattered inline
- `useQuery`/`useMutation` wrapped in custom hooks — not called raw in components

**For Vite/React projects:**
- Same SoC as Next.js but client-only rendering
- Routes/pages are thin — compose feature components
- Features are self-contained modules
- Same component, service, hook, store separation rules
- Environment variables validated with Zod at startup — never access `import.meta.env` directly elsewhere

**Cross-cutting rules (all project types):**
- No catch-all utils.py/utils.ts files over 50 lines — must be topic-specific
- Flat package structures — no nesting deeper than 3 levels
- No circular imports

AUDIT TASKS:
1. Use Glob to map the directory structure (glob for **/*.py, **/*.ts, **/*.tsx as appropriate)
2. Check if the project follows the expected directory layout
3. Use Grep to find import violations:
   - Python: routers importing from repositories or models directly
   - Python: services importing Session or executing queries
   - Python: repositories importing from services or routers
   - Python: services importing or raising HTTPException
   - Python: services type-hinting concrete repository classes instead of Protocols
   - TS/React: features importing from other features
   - TS/React: components importing from stores or doing data fetching
4. Check for missing layers (e.g., no services/ directory, logic in routers)
5. Check that pages/routes are thin (read a sample and check line count)
6. Python: Grep router files for `@router.` decorators without `response_model=` or `status_code=`
7. Python: Grep router files for raw `Depends(` in function params (should use Annotated aliases)
8. Python: Grep for `session.query(` (legacy SQLAlchemy style)
9. Python: Check if list endpoints return bare `list[` without pagination wrapper
10. Python: Check if `config.py` uses `BaseSettings` from pydantic-settings
11. TS/React: Check route directories for missing `error.tsx` boundaries
12. TS/React: Grep for `process.env.` or `import.meta.env.` outside `lib/env.ts`
13. TS/React: Check if query keys are centralized or scattered across components

Return your findings as a markdown table:
| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
```

---

### Agent 2 — Typing & Style

Prompt for this agent:

```
You are a typing and code style auditor. Analyze this project for type safety and style issues.

PROJECT TYPE: {detected_type}

RULES TO AUDIT AGAINST:

**For Python projects:**
- ALL functions must have full type annotations (parameters + return types)
- ALL class attributes must be annotated
- Never use Any without an explanatory comment
- Use from __future__ import annotations for modern syntax
- snake_case for functions/methods/variables/modules, PascalCase for classes, UPPER_SNAKE_CASE for constants
- Boolean variables: is_, has_, can_, should_ prefixes
- Always f-strings for interpolation (not .format() or %)
- Use is None / is not None (never == None)
- Use isinstance() for type checks (never type(x) == T)
- Absolute imports only, no wildcard imports
- Import grouping: stdlib → third-party → local with blank line separation
- Catch specific exceptions — never bare except: or except Exception: without re-raising
- Use raise ... from err to preserve exception chains
- Max 5 function arguments — beyond that, group into a Pydantic model or dataclass
- Max nesting depth: 3 levels — use guard clauses and early returns to flatten
- No print() in production code — use structured logging (structlog or stdlib logger)

**For TypeScript/React projects:**
- strict: true in tsconfig.json (also noUncheckedIndexedAccess: true)
- ALL function parameters and return types explicitly typed
- ALL component props must have a named type/interface following `<ComponentName>Props` convention
- Never use any — use unknown and narrow with type guards
- Use as const for literal types and readonly arrays
- Use satisfies for type-safe object literals
- PascalCase for components/types/interfaces, camelCase for functions/variables, UPPER_SNAKE_CASE for constants, kebab-case for files
- Boolean props: is, has, can, should prefix
- Use @/ absolute imports, type imports for type-only imports
- Use Zod for runtime validation at boundaries; derive TS types from Zod with z.infer
- No require() calls
- Every useEffect must have a comment explaining WHY it's needed
- One exported component per file
- No inline arrow functions in JSX for non-trivial logic (extract to handler or useCallback)

AUDIT TASKS:
1. Use Grep to find functions missing type annotations (Python: def without -> ; TS: function without : return type)
2. Use Grep to find Any/any usage without justification comments
3. Use Grep to find naming violations (e.g., camelCase in Python, snake_case in TS components)
4. Use Grep to find == None, bare except:, wildcard imports
5. Check tsconfig.json for strict: true and noUncheckedIndexedAccess: true if TS project
6. Use Grep to find .format( or % string formatting in Python
7. Check import style in a sample of files
8. Python: Grep for functions with 6+ parameters (count commas in def signatures)
9. Python: Grep for `print(` in src/ (should use logger)
10. TS/React: Grep for `useEffect(` and check if the preceding line has a comment explaining why
11. TS/React: Grep for component files with multiple `export function` or `export const` (one component per file)
12. TS/React: Grep for `require(` in .ts/.tsx files
13. TS/React: Check that component props types follow `<Name>Props` naming convention

Return your findings as a markdown table:
| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
```

---

### Agent 3 — State Management & Enums

Prompt for this agent:

```
You are a state management and enum auditor. Analyze this project for raw string usage and missing FSMs.

PROJECT TYPE: {detected_type}

RULES TO AUDIT AGAINST:

**For Python projects:**
- ALWAYS use enum.Enum (or StrEnum, IntEnum) for any value from a fixed known set
- Never use raw strings for statuses, roles, types, categories, modes
- If you see if status == "active" with a string literal — it should be an enum
- Enums defined in enums/ directory
- ANY entity with a status/state field MUST define a formal FSM
- FSMs live in state_machines/ directory with explicit transition maps
- Service layer calls FSM to validate before mutating state

**For TypeScript/React projects:**
- Use as const objects or string union types instead of TypeScript enum keyword
- Use Record maps for constants with associated behavior
- ANY UI flow with 3+ states and constrained transitions MUST use an FSM
- NEVER store server data in Zustand or useState — TanStack Query is the cache
- NEVER use useEffect to sync state between sources — derive it instead
- NEVER use useContext for frequently-changing state — use Zustand instead
- useReducer over useState when state transitions are complex
- Zustand stores: one per domain concern, no god store, actions INSIDE store (not external)
- URL state (nuqs/useSearchParams) for filters, pagination, sort — not component state
- TanStack Query for all server state; wrap in custom hooks
- Components with 3+ useState calls likely need a custom hook or useReducer

AUDIT TASKS:
1. Use Grep to find string literal comparisons that suggest missing enums:
   - Python: == "active", == "pending", == "draft", status == ", role == ", type == " etc.
   - TS: === "active", === "pending", status === ", role === " etc.
2. Check if enums/ directory exists and is populated
3. Check if state_machines/ directory exists for projects with stateful entities
4. For TS projects: grep for TypeScript enum keyword (should use as const instead)
5. For React projects: grep for useState.*fetch or useEffect.*fetch (should use TanStack Query)
6. For React projects: check if Zustand stores contain server data patterns
7. Look for entities with status/state fields that lack FSM definitions
8. For React projects: grep for `useState` count per component — flag components with 3+ useState calls
9. For React projects: grep for filter/sort/pagination state in useState (should be URL params)
10. For React projects: check if Zustand store actions are defined inside the store (not as external functions)

Return your findings as a markdown table:
| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
```

---

### Agent 4 — Testing Quality

Prompt for this agent:

```
You are a testing quality auditor. Analyze this project's test suite for coverage gaps and quality issues.

PROJECT TYPE: {detected_type}

RULES TO AUDIT AGAINST:

**For Python projects:**
- Test names: test_<action>_<scenario>_<expected_outcome> pattern — readable as specs
- Every test follows AAA pattern (Arrange/Act/Assert) with clear sections
- Service layer unit tests + router integration tests required
- Every public service method: at least 1 happy-path + 1 error-path test
- Every FSM transition tested (valid AND invalid)
- Every custom Pydantic validator tested
- Test structure mirrors src/ layout
- Use factories for test data — never hardcode dicts inline
- Must test: boundary conditions, unauthorized access, invalid state transitions
- Use pytest with pytest-asyncio, httpx.AsyncClient for integration tests

**For React/TS projects:**
- Test names: it("should <behavior> when <scenario>") — behavior-focused
- Test behavior not implementation — query by role/label/text, not class/id
- User-centric query priority: getByRole > getByLabelText > getByText > getByTestId
- Never test internal state (useState values) or styling (className)
- Components: rendering, user interactions, conditional display
- Hooks: state changes, returned values
- Services: request/response mapping, error handling
- Schemas: Zod validation rules and edge cases
- FSMs: all valid + invalid transitions
- Use MSW for API mocking at network level
- Co-locate tests: component.tsx → component.test.tsx
- Vitest + React Testing Library

AUDIT TASKS:
1. Use Glob to find all test files (**/*test*, **/test_*, **/*.spec.*)
2. Check test naming quality — read a sample of test files and flag meaningless names
3. Check for AAA pattern in test bodies
4. Compare source modules to test modules — find untested modules
5. Use Grep to find hardcoded test data (magic strings/numbers in assertions without factories)
6. Check if test fixtures/factories exist (conftest.py for Python, test utils for TS)
7. Look for jest.mock or direct mock usage that should use MSW (for React)
8. Check if FSM transitions are tested (if FSMs exist)

Return your findings as a markdown table:
| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
```

---

### Agent 5 — Documentation & Cognitive Debt

Prompt for this agent:

```
You are a documentation and cognitive debt auditor. Analyze this project for missing docs and code health issues.

PROJECT TYPE: {detected_type}

RULES TO AUDIT AGAINST:

**Documentation (all projects):**
- ARCHITECTURE.md is MANDATORY at project root with sections: Overview, Tech Stack, Project Structure, Layer Responsibilities, Data Flow, Key Domain Concepts, State Machines
- decisions.md must exist for recording ADRs
- Comments explain WHY not WHAT — never restate function signatures in docstrings

**Cognitive debt signals (all projects):**
- Any file over 200 lines of code (flag as hotspot)
- Any function over 30 lines (flag for extraction)
- Any class over 150 lines (flag for SRP violation)
- Any catch-all utility file (utils.py, helpers.py, utils.ts, helpers.ts) — should be topic-specific
- Any new dependency without justification in ARCHITECTURE.md
- Any # type: ignore or @ts-ignore or // eslint-disable without justification comment
- Any TODO/FIXME/HACK comments (track as technical debt)

**Security (all projects):**
- No f-string SQL (`f"SELECT`, `f"INSERT`, `f"UPDATE`, `f"DELETE`) — must use parameterized queries
- No `allow_origins=["*"]` in CORS configuration (production risk)
- No hardcoded secrets in code (`password=`, `secret=`, `api_key=` with string literals)
- No plaintext password storage — must use bcrypt/argon2

**Security (Python-specific):**
- Alembic used for migrations — never manual schema changes
- No `time.sleep()` in async code — use `asyncio.sleep()`
- No sync blocking calls in async context without `run_in_executor`

**Security (React/TS-specific):**
- No raw error objects or stack traces displayed to users — use user-friendly error states
- Accessibility: `<img>` tags must have `alt`, interactive `<div>` should be `<button>`, form inputs need labels
- Semantic HTML used (nav, main, section, article — not div for everything)

**Dependency hygiene:**
- All dependencies pinned via lockfile
- No floating versions in pyproject.toml/package.json
- Lockfile committed to repo

AUDIT TASKS:
1. Check for ARCHITECTURE.md at project root — if it exists, verify it has required sections
2. Check for decisions.md at project root
3. Use Glob + Read to find files over 200 lines (check line counts of all source files)
4. Use Grep to find functions over 30 lines (scan for def/function definitions and check spacing)
5. Use Glob to find catch-all utility files (utils.py, helpers.py, utils.ts, etc.)
6. Use Grep to find type: ignore, @ts-ignore, eslint-disable, noqa without justification
7. Use Grep to find TODO, FIXME, HACK comments
8. Check if lockfile exists (uv.lock, pnpm-lock.yaml, bun.lockb, package-lock.json)
9. Check dependency specs for floating versions (^, ~, * in package.json; >= without < in pyproject.toml)
10. Python: Grep for f-string SQL patterns (`f"SELECT`, `f"INSERT`, `f"UPDATE`, `f"DELETE`)
11. Python: Grep for `allow_origins=["*"]` or `allow_origins=\["*"\]` in CORS config
12. Python: Grep for `time.sleep(` in async code (should be asyncio.sleep)
13. Python: Check if Alembic is configured (alembic/ directory, alembic.ini)
14. TS/React: Grep for `<img` without `alt=` attribute
15. TS/React: Grep for `<div onClick` or `<span onClick` (should be semantic button/a elements)
16. All: Grep for hardcoded secret patterns (`password="`, `secret="`, `api_key="`, `token="` with string values)

Return your findings as a markdown table:
| Severity | Finding | File(s) | Rule Violated | Recommendation |
|----------|---------|---------|---------------|----------------|
```

---

## Step 3 — Consolidate into REVIEW.md

After all 5 agents complete, combine their findings into a single `REVIEW.md` at the project root.

Use this exact format:

```markdown
# Architecture Review — {project_name}

**Date:** {today's date YYYY-MM-DD}
**Project type:** {detected type(s)}

## Executive Summary

| Category | Conformance | Critical | Warnings | Info |
|----------|------------|----------|----------|------|
| Architecture & SoC | High/Medium/Low | N | N | N |
| Typing & Style | High/Medium/Low | N | N | N |
| State & Enums | High/Medium/Low | N | N | N |
| Testing | High/Medium/Low | N | N | N |
| Documentation & Debt | High/Medium/Low | N | N | N |

### Top Critical Findings
1. ...
2. ...
(list up to 5 most impactful findings across all categories)

## Detailed Findings

### 1. Architecture & Separation of Concerns
{Agent 1 table}

### 2. Typing & Style
{Agent 2 table}

### 3. State Management & Enums
{Agent 3 table}

### 4. Testing Quality
{Agent 4 table}

### 5. Documentation & Cognitive Debt
{Agent 5 table}

## Migration Plan

### Phase 0 — Quick Wins (mechanical, low risk)
- [ ] {items that can be fixed with automated tools or simple changes}

### Phase 1 — Structural Improvements (medium effort)
- [ ] {items requiring reorganization but not architectural changes}

### Phase 2 — Architectural Changes (higher effort)
- [ ] {items requiring significant refactoring or new patterns}

### Phase 3 — Ongoing Discipline
- [ ] {process/tooling changes to prevent regression}
```

Scoring guide:
- **High conformance**: 0 critical, ≤2 warnings
- **Medium conformance**: 0 critical, 3+ warnings OR 1 critical
- **Low conformance**: 2+ critical findings

Write the file using the Write tool to `REVIEW.md` at the project root.

After writing, tell the user the review is complete and summarize the top findings.
