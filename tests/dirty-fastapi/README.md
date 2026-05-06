# Dirty FastAPI — Harness Test Fixture

A deliberately broken FastAPI project with **27 intentional violations** across 7 categories. Used to validate that `/check`, `/fix-check`, and `/review-architecture` detect and fix real issues.

## Purpose

This project is a **test harness for the harness** — it lets you verify that the self-correcting loop pattern converges to clean code without manual intervention.

Think of it like a unit test: known violations in, clean code out, and we measure detection rate, fix rate, and iterations needed.

## Violations Baked In

See [VIOLATIONS.md](VIOLATIONS.md) for the full scorecard (27 violations).

| Category | Count | Examples |
|----------|-------|---------|
| Security | 4 | CORS wildcard, hardcoded secret, SQL injection, insecure random |
| Architecture | 10 | Session in service, HTTPException in service, no response_model, biz logic in router |
| State/Enum | 1 | Raw string statuses everywhere, no enum, no FSM |
| Typing | 3 | Missing annotations, bare except, unjustified Any |
| Schema | 1 | Single schema for all purposes |
| Cognitive debt | 5 | TODO/FIXME without refs, print(), catch-all utils.py |
| Documentation | 3 | No ARCHITECTURE.md, no decisions.md, no tests |

## Git Structure

```
master    ← empty scaffold (pyproject.toml only)
  └── feature/orders  ← all dirty code lives here (current branch)
```

The diff between `master` and `feature/orders` is the "change set" that `/check` evaluates.

## How to Run the Tests

### Prerequisites

Navigate to this directory:
```bash
cd tests/dirty-fastapi
```

Ensure you're on the dirty branch:
```bash
git checkout feature/orders
git reset --hard 0d8037d   # reset to original dirty state
git clean -fd              # remove any leftover files from previous runs
```

### Test 1: Validate `/check` Detection Rate

Run `/check` and compare against [VIOLATIONS.md](VIOLATIONS.md):

```
/check
```

**Expected**: Most of the 27 violations should be detected. Score = detected / 27.

### Test 2: Validate `/fix-check` Harness — Delta Entry Point

After `/check` reports violations, run the self-correcting harness directly on the diff:

```
/fix-check
```

**Expected output**: A loop summary table showing iterations and violation counts converging to zero:

```
| Iteration   | Violations |  Δ  |
|-------------|------------|-----|
| 0 (initial) | ~20        | —   |
| 1           | ~6         | -14 |
| 2           | ~3         | -3  |
| 3           | 0          | -3  |
```

**What to measure**:
- **Fix rate**: violations fixed / violations detected
- **Iterations**: how many loops before clean (target: ≤3)
- **Regressions**: new violations introduced by fixes (should be caught and fixed by the loop)
- **Cross-agent conflicts**: e.g., router agent and service agent producing incompatible interfaces

**Reset after test**:
```bash
git checkout feature/orders
git reset --hard 0d8037d
git clean -fd
```

### Test 3: Validate `/fix-check` Harness — Plan-Driven Entry Point

Run the complete release-gate pipeline (audit → plan → fix):

```
# Step 1: Full audit (5 parallel agents)
/review-architecture

# Step 2: Expand findings into a concrete fix plan
/plan-fix

# Step 3: Self-correcting fix harness, driven by FIX_PLAN.md
/fix-check
```

**Expected**: REVIEW.md is produced with findings, `/plan-fix` produces a single-phase `FIX_PLAN.md` (small audit), then `/fix-check` fixes everything in 1–2 iterations because the plan provides prescriptive HOW TO FIX instructions.

**What to measure**:
- **Detection coverage**: how many of the 27 violations appear in REVIEW.md
- **Fix convergence**: iterations needed (target: ≤2 — prescriptive prompts converge faster than delta-only)
- **Cross-phase interference**: did fixing Phase 2 undo Phase 1 fixes?
- **Evaluator accuracy**: did the grep patterns correctly identify remaining violations?

**Reset after test**:
```bash
git checkout feature/orders
git reset --hard 0d8037d
git clean -fd
```

### Test 4: Compare Old vs New

To compare the harness approach against a single-pass fix:

1. Reset to dirty state
2. Run `/check`
3. Run the old approach: manually ask Claude to "fix all violations" (no harness)
4. Run `/check` again — count remaining violations

Then reset and repeat with the harness:

1. Reset to dirty state
2. Run `/fix-check` (harness — includes its own evaluator)
3. Compare: how many violations remain?

## Test Results (Reference)

### Delta Entry Point — `/check` → `/fix-check` (2026-03-25)

| Iteration | Violations | Δ | Fix Units | Key Event |
|-----------|-----------|---|-----------|-----------|
| 0 | 20 | — | — | Initial scan |
| 1 | 6 | -14 | 4 parallel | Cross-agent conflict: router imported functions, service became a class |
| 2 | 3 | -3 | 2 parallel | Fixed wiring + utils.py warnings |
| 3 | 0 | -3 | 1 | Final stragglers (raw strings in utils, model default) |

**Result**: 20 → 0 in 3 iterations. Cross-agent wiring break caught by evaluator in iteration 1.

### Plan-Driven Entry Point — `/review-architecture` → `/plan-fix` → `/fix-check` (2026-03-25)

| Iteration | Violations | Δ | Fix Units | Key Event |
|-----------|-----------|---|-----------|-----------|
| 0 | 20 grep patterns failing | — | — | Full review (5 agents) + plan |
| 1 | 0 | -20 | 5 parallel | Prescriptive code in prompts → converged in 1 iteration |

**Result**: 20 → 0 in 1 iteration. Prescriptive HOW TO FIX instructions (exact target code) eliminated cross-agent conflicts.

### Key Insight

The delta entry point (high-level instructions from `/check` violations) needed 3 iterations. The plan-driven entry point (prescriptive code from `FIX_PLAN.md`) needed 1. **The more concrete the HOW TO FIX, the fewer loops needed.** This validates the Anthropic harness insight: sprint contracts reduce iteration count — and motivates `/plan-fix` as the high-leverage step before `/fix-check` whenever an audit produces a fix plan.

## Project Structure

```
tests/dirty-fastapi/
├── README.md              # This file
├── VIOLATIONS.md          # Scorecard of all intentional violations
├── pyproject.toml         # Project config
└── app/
    ├── main.py            # CORS wildcard
    ├── config.py          # Hardcoded secret, os.getenv
    ├── utils.py           # Catch-all, bare except, Any, random
    ├── models/
    │   └── order.py       # String status, no enum
    ├── schemas/
    │   └── order.py       # No Create/Update/Out separation
    ├── repositories/
    │   └── order_repo.py  # session.query(), f-string SQL, biz logic
    ├── services/
    │   └── order_service.py  # Session, HTTPException, raw strings, print, TODO
    └── routers/
        └── orders.py      # No response_model, biz logic, raw Depends
```
