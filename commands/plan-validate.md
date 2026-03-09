# Validate Implementation Plan

You are an independent plan **validator**. Your job is to read `IMPLEMENTATION_PLAN.md` and verify it is detailed enough for subagents (especially Sonnet) to implement correctly — without shortcuts, missing types, or architectural violations.

**You are NOT the planner.** You are a 3rd-party reviewer. Do not assume the plan is correct — verify every claim against the codebase and rules.

## Why This Command Exists

Sonnet subagents follow instructions literally. When a plan says "add the data layer", Sonnet creates a minimal stub. When a plan says "create `order_dto.dart` with fields `id: int`, `status: OrderStatus`, `toEntity()` mapper returning `Order`", Sonnet produces exactly that. The quality of the implementation is bounded by the quality of the plan.

## Step 0 — Load Plan and Context

1. **Find the plan files.** Check for:
   - `IMPLEMENTATION_PLAN.md` (monolithic plan) — OR
   - `IMPLEMENTATION_PLAN_PHASE_*.md` (per-phase plan files, e.g., `IMPLEMENTATION_PLAN_PHASE_1.md`)
   - If neither exists, tell the user: "No implementation plan found. Run `/plan-release` first." and stop.
   - If only a monolithic `IMPLEMENTATION_PLAN.md` exists with 2+ phases, flag this in the report: "⚠️ Plan should be split into per-phase files to reduce subagent context noise. See Phase Structure section."
2. **Read all plan files.**
3. **Read `ARCHITECTURE.md`** — understand project structure, layers, patterns, existing entities.
4. **Read `CLAUDE.md`** (if exists) — project-specific rules.
5. **Detect project type** (pyproject.toml with fastapi, pubspec.yaml with flutter, next.config.*, vite.config.*).
6. **Quick codebase scan**: Glob for existing files in each layer to understand what patterns exist. Read 1-2 reference files per layer to know what "correct" looks like.

## Step 1 — Validate Plan Completeness

For EACH file listed in the plan (new or modified), check it against the **File Spec Checklist**:

### New Files — Required Fields

| Field | Required? | What to check |
|---|---|---|
| **Purpose** | REQUIRED | Is it a clear one-line description? Not just the filename restated? |
| **Fields / Methods** | REQUIRED | Are fields typed? Are method signatures complete (params + return types)? |
| **Constraints** | REQUIRED | Does it mention the critical rules for this file type? (see Per-Layer Rules below) |
| **Reference file** | REQUIRED | Does it point to an existing file in the project that follows the correct pattern? Verify the reference file exists. |
| **Pattern** | REQUIRED for domain entities | Does it specify `@freezed`, Pydantic BaseModel, or equivalent? |

**Flag as ❌ INCOMPLETE** if any required field is missing.

### Modified Files — Required Fields

| Field | Required? | What to check |
|---|---|---|
| **Exact change** | REQUIRED | Does it describe WHAT changes? Not just "update this file" — must say what specifically. |
| **Import updates** | IF APPLICABLE | If a new module is being created, do all files that need to import it get listed? |

### Test Files — Required Fields

| Field | Required? | What to check |
|---|---|---|
| **Test cases listed** | REQUIRED | Are specific test names listed? Not just "add tests". |
| **Happy + error paths** | REQUIRED | Is there at least 1 happy-path AND 1 error-path test per public method? |
| **Fixture strategy** | REQUIRED | Does it specify factories or mock setup? Not "add test data". |
| **Reference test file** | RECOMMENDED | Points to existing test file with correct pattern. |

## Step 2 — Validate Against Architecture Rules

### Per-Layer Rule Cross-Check

For each file in the plan, verify the spec doesn't violate or omit critical architecture rules:

**Python/FastAPI files:**

| File location | Rule to verify in spec |
|---|---|
| `services/*.py` | Spec lists constructor DI params (repos only, no other services). Return types are Pydantic schemas, not dicts. No `Session` params. |
| `schemas/*.py` | Spec separates Create/Update/Out. Status fields use StrEnum, not str. |
| `routers/*.py` | Spec includes `response_model` and `status_code` for each endpoint. Params from closed sets use StrEnum. |
| `enums/*.py` | All status/type fields referenced in entities are covered by an enum definition in the plan. |
| `state_machines/*.py` | Every entity with a `status` field has a corresponding FSM definition in the plan. |
| `repositories/*.py` | No business logic described — only data access. |
| `tests/*.py` | Test names follow `test_<action>_<scenario>_<expected>`. Factories referenced. |

**Flutter files:**

| File location | Rule to verify in spec |
|---|---|
| `domain/entities/*.dart` | Spec says `@freezed`. Status fields typed as enum, not String. No `Map<String, dynamic>`. |
| `domain/enums/*.dart` | Enhanced enum with `fromString()` that throws on unknown (not silent fallback). |
| `data/models/*_dto.dart` | Has `toEntity()` mapper. No `Map<String, dynamic>` for nested objects — typed nested DTOs. |
| `presentation/providers/*.dart` | Uses `ref.watch` in build. State type specified. No business logic. |
| `presentation/pages/*.dart` | Under 200 lines. No direct data/ imports. No hardcoded colors. |
| `presentation/widgets/*.dart` | Props typed. No `setState` for server data. |
| `tests/**_test.dart` | Tests listed by name. Mock strategy specified. Happy + error paths. |

**React/Next.js files:**

| File location | Rule to verify in spec |
|---|---|
| `features/*/types.ts` | All types exported. No `any` or `Record<string, unknown>`. |
| `features/*/schemas/*.ts` | Zod schemas, not raw TypeScript types for runtime validation. |
| `features/*/hooks/*.ts` | TanStack Query wrapper. No raw `useEffect` fetch. |
| `components/*.tsx` | Named props type. Under 150 lines. |
| `app/**/*.tsx` | Pages under 50 lines. Error boundary exists for data-fetching routes. |

### Cross-File Consistency Check

| Check | What to verify |
|---|---|
| **Enum coverage** | Every `status` or `type` field in new entities → corresponding enum exists in plan |
| **FSM coverage** | Every entity with status → FSM definition exists in plan |
| **Test coverage** | Every new service/provider/hook → test file exists in plan with specific test cases |
| **Import chain** | New files are registered where needed (DI containers, routers, barrel files) |
| **Schema coverage** | Every new API endpoint → request/response schemas exist in plan |
| **Reference files exist** | Every "Reference: follow pattern in X" → verify X actually exists in codebase |

## Step 3 — Validate Phase Structure

### 3a — Phase Isolation (Per-Phase Files)

If the plan has **2 or more phases**, it MUST be split into separate files:

```
IMPLEMENTATION_PLAN.md              ← Overview: phases, dependencies, timeline
IMPLEMENTATION_PLAN_PHASE_1.md      ← Full specs for Phase 1 files only
IMPLEMENTATION_PLAN_PHASE_2.md      ← Full specs for Phase 2 files only
IMPLEMENTATION_PLAN_PHASE_3.md      ← Full specs for Phase 3 files only
```

**Why?** When `/implement-phase 2` runs, the subagent receives the phase file as context. A monolithic plan with all phases pollutes the context with irrelevant Phase 1/3/4 specs — Sonnet may confuse files across phases, or the context gets truncated and critical specs are lost.

**Each phase file MUST be self-contained:**
- All per-file specs for that phase's files
- Dependencies on earlier phases stated explicitly ("Phase 1 must be complete: `Order` entity and `OrderRepository` exist")
- Agent assignment for that phase
- No references to files from other phases without explicit "already exists from Phase N" context

**Flag as ❌ BLOCKER** if:
- A monolithic plan has 2+ phases and hasn't been split into per-phase files
- A phase file references specs from another phase file without restating them
- A phase file exceeds 300 lines (too large for effective subagent context)

### 3b — Phase Structure Checks

1. **Dependency order**: Can Phase N be implemented without depending on Phase N+1? Flag circular dependencies.
2. **Phase size**: Is any phase too large (>10 files)? Recommend splitting.
3. **Agent assignment**: Does each phase have a clear `subagent_type`? Is it correct for the file types?
4. **Test placement**: Are tests in the same phase as the code they test? (Don't defer tests to a later phase.)
5. **Phase self-sufficiency**: Can each phase be compiled/analyzed independently after implementation? (e.g., don't create a service in Phase 1 that references a repository defined in Phase 2.)

### 3c — Sonnet Readability Test

For each phase file, apply this mental test: **"If I gave this spec to a Sonnet agent with no prior conversation context, would it produce correct code?"**

Specifically check:

| Test | Pass criteria | Common failure |
|---|---|---|
| **Can Sonnet find the reference file?** | Reference is an exact path: `services/purchase_order_service.py` | Vague: "follow existing patterns" |
| **Can Sonnet determine the exact fields?** | All fields listed with types: `status: OrderStatus` | Missing: "add appropriate fields" |
| **Can Sonnet determine the method signatures?** | Full signature: `create(data: InvoiceCreate, tenant_id: int) -> InvoiceOut` | Partial: "add a create method" |
| **Can Sonnet determine what imports to add?** | Imports listed or derivable from field types | Missing: "add necessary imports" |
| **Can Sonnet determine the test cases?** | Test names listed: `test_create_invoice_with_valid_po_returns_invoice` | Vague: "add unit tests" |
| **Can Sonnet determine the error handling?** | Error types and conditions specified: "raise NotFoundError if PO doesn't exist" | Missing: "handle errors appropriately" |
| **Is the constraint list specific enough?** | Stack-specific rules stated: "use `@freezed`, no `Map<String, dynamic>`" | Generic: "follow best practices" |

**Flag as ⚠️ NEEDS REFINEMENT** any file spec where 2+ tests fail.

## Step 4 — Scan for Common Plan Gaps

These are the patterns most commonly missed by plans:

| Gap | How to detect | Fix suggestion |
|---|---|---|
| **Vague file spec** | File listed without method signatures or field list | "Add per-file spec with Fields/Methods/Constraints" |
| **Missing enum** | Entity has `status: String` or `type: str` in field list | "Add enum definition and change field type to enum" |
| **Missing FSM** | Entity with status field but no state machine in plan | "Add FSM definition with states and valid transitions" |
| **No error-path tests** | Test file only lists happy-path tests | "Add error-path test: `test_<action>_with_invalid_<input>_raises_<error>`" |
| **Stub reference** | "Reference: follow existing pattern" without naming a specific file | "Name the specific reference file, e.g., `services/purchase_order_service.py`" |
| **Dict return type** | Service method spec says `-> dict` or no return type | "Specify Pydantic schema / typed data class return" |
| **Missing DI registration** | New service/repository but no mention of `dependencies.py` / provider registration | "Add modification spec for DI registration file" |
| **Placeholder plan items** | "Add data layer files" or "Implement the feature" without breakdown | "Break down into specific file specs" |
| **No constructor params** | Service spec without listing repository dependencies | "List constructor params (which repos does this service depend on?)" |
| **Missing import updates** | New module created but existing files that need to import it aren't listed | "Add modification specs for files that need to import the new module" |
| **Silent no-op cases** | Switch/case in plan that says "placeholder" or "TBD" | "Either implement or throw UnimplementedError with tracker ref — no silent no-ops" |
| **Raw string dispatch** | Plan describes dispatch logic without specifying enum keys | "Specify enum members as dispatch keys, not raw strings" |

## Step 5 — Report

Output the validation results directly in conversation (no file output):

```
## Plan Validation — IMPLEMENTATION_PLAN.md

### File Spec Completeness
| Status | Count | Details |
|--------|-------|---------|
| ✅ Complete | {N} | Files with full spec (purpose, fields/methods, constraints, reference) |
| ⚠️ Partial | {N} | Files missing some required fields |
| ❌ Incomplete | {N} | Files with no spec or just a name |

### Incomplete File Specs
| File | Missing |
|------|---------|
| `services/foo_service.py` | No method signatures, no return types |
| `domain/entities/bar.dart` | No field list, no @freezed annotation specified |
| `tests/test_foo.py` | No test cases listed, no fixture strategy |

### Architecture Rule Violations in Plan
| File | Issue |
|------|-------|
| `domain/entities/order.dart` | `status` field typed as `String` — should be enum |
| `services/invoice_service.py` | No constructor params listed — DI violation |
| Phase 2 | Tests deferred to Phase 3 — should be in same phase as code |

### Cross-File Gaps
| Gap | Action Needed |
|-----|---------------|
| No FSM for `Invoice.status` | Add `state_machines/invoice_fsm.py` to plan |
| No DI registration for `InvoiceService` | Add `dependencies.py` modification spec |
| Reference file `services/billing_service.py` does not exist | Update reference to existing file |

### Summary
- Total files in plan: {N}
- ✅ Complete specs: {X}/{N}
- ⚠️ Gaps found: {Y}
- ❌ Blockers (must fix before implementing): {Z}

### Verdict
✅ READY TO IMPLEMENT — plan is detailed enough for subagents.
⚠️ NEEDS REFINEMENT — {Y} gaps found. Fix these in the plan before running `/implement-phase`.
❌ NOT READY — {Z} critical gaps. Plan needs significant detail before implementation.
```

If the verdict is not ✅, list the specific fixes needed in priority order (blockers first, then warnings).

## Design Principles

- **Independent validation**: You are NOT the planner. Question everything. Verify references exist.
- **Sonnet-calibrated**: The bar is "would Sonnet produce correct code from this spec alone?" If not, it's incomplete.
- **No code changes**: This is a read-only command. You validate the plan, you don't fix it.
- **Fast**: This should take 2-5 minutes. Read the plan, scan the codebase for references, report gaps.
- **Actionable**: Every gap must have a concrete fix suggestion. "Incomplete spec" is not actionable — "Add method signatures with param types and return type" is.
