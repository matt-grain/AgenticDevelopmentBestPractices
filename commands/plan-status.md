# Project Status Dashboard

You are a status reporter. Your job is to scan all workflow artifacts and produce a single dashboard showing where the project stands — what's done, what's in progress, and what's next.

## Step 0 — Detect Project Context

1. **Read project identity**: Check for `CLAUDE.md`, `ARCHITECTURE.md`, `package.json`, `pubspec.yaml`, or `pyproject.toml` to identify the project name and type.
2. **Detect if in a subdirectory**: If the current working directory has a parent with these files, note the subproject context (e.g., `GRAIN_Inventory/mobile`).

## Step 1 — Scan Implementation Artifacts

Check for these files at the project root (and parent if in subproject):

### IMPLEMENTATION_PLAN.md
If exists:
- Extract creation/update date
- Count total phases and tasks per phase
- Identify current phase (first incomplete phase, or one marked "in progress")
- List phase titles and their status markers (`✅`, `🔄`, `⏳`)

### IMPLEMENTATION_STATUS.md
If exists:
- Extract last updated date
- Parse the progress summary table
- Get overall completion percentage
- List any gaps or partial items from the last phase

### If neither exists:
Report: "No implementation plan found. Use `/plan-release` to create one."

## Step 2 — Scan Review Cycle Artifacts

### REVIEW.md
If exists:
- Extract date
- Extract project scope (what was reviewed — backend, frontend, both?)
- Extract executive summary conformance levels
- Count findings by severity (🔴 Critical, 🟡 Warning)

### FIX_PLAN.md
If exists:
- Extract date and base review date
- Count total fix units and phases
- Count deferred items
- Check if it's been executed (look for completion markers)

### REVIEW_FIX_LOG.md
If exists:
- Extract date
- Parse completion summary (fully fixed vs partial)
- Note any files that were skipped

### REVIEW_VALIDATION.md
If exists:
- Extract date
- Extract overall completion percentage
- Extract verdict (ALL CLEAR / GAPS FOUND / SIGNIFICANT GAPS)
- Count remaining gaps
- List top 3 gaps if any

### If no review artifacts exist:
Report: "No architecture review found. Use `/review-architecture` to audit the codebase."

## Step 3 — Check Recent Activity

### Git status
Run `git log -1 --format="%ar — %s"` to get the last commit time and message.

### Last /check inference
Look for patterns in recent commits or check if there are uncommitted changes:
- `git status --porcelain` — are there uncommitted changes?
- `git diff --name-only HEAD~5..HEAD` — what files changed recently?

## Step 4 — Determine Recommended Next Action

Based on the state, recommend the logical next step:

| State | Recommendation |
|-------|----------------|
| No IMPLEMENTATION_PLAN.md | "Run `/plan-release` to create an implementation plan" |
| Plan exists, Phase N incomplete | "Continue `/implement-phase {N}` — {X} tasks remaining" |
| Phase complete, uncommitted changes | "Run `/check` then commit Phase {N}" |
| All phases complete | "Implementation done. Run `/review-architecture` before release" |
| REVIEW.md exists, no FIX_PLAN.md | "Run `/plan-fix` to create a fix plan" |
| FIX_PLAN.md exists, not executed | "Review FIX_PLAN.md, then run `/fix-check` to execute" |
| REVIEW_FIX_LOG.md exists, no validation | "Run `/validate-review` to verify fixes" |
| REVIEW_VALIDATION.md shows gaps | "Run `/heal-review` to fix {N} remaining gaps" |
| REVIEW_VALIDATION.md ALL CLEAR | "Ready for release" |

## Step 5 — Output Dashboard

Output directly to the user (no file — this is a quick status check):

```
## Project Status — {project_name}

### Implementation Progress
{If IMPLEMENTATION_PLAN.md exists:}
**Plan:** IMPLEMENTATION_PLAN.md (created {date})
**Current Phase:** Phase {N} of {total} ({status})
**Overall:** {X}/{Y} tasks complete ({Z}%)

| Phase | Status | Tasks | Completion |
|-------|--------|-------|------------|
| Phase 1: {title} | ✅ Complete | {n}/{n} | 100% |
| Phase 2: {title} | 🔄 In Progress | {x}/{y} | {z}% |
| Phase 3: {title} | ⏳ Pending | 0/{n} | 0% |

{If IMPLEMENTATION_STATUS.md exists and has gaps:}
**Phase {N} gaps:** {list any ⚠️ or ❌ items}

{If no plan:}
**No implementation plan found.**

---

### Architecture Review Cycle
{If REVIEW.md exists:}
**Last review:** {date}
**Scope:** {backend/frontend/mixed}
**Findings:** {N} critical, {M} warnings

{If FIX_PLAN.md exists:}
**Fix plan:** {date} — {N} fix units, {M} deferred

{If REVIEW_VALIDATION.md exists:}
**Validation:** {date} — {X}% complete
**Verdict:** {verdict}
{If gaps:} **Gaps remaining:** {N}

{If no review artifacts:}
**No architecture review found.**

---

### Git Status
**Last commit:** {time ago} — "{message}"
**Working tree:** {clean / N uncommitted changes}

---

### Recommended Next Action
→ {Primary recommendation based on state}
{If secondary action relevant:} → {Secondary recommendation}
```

## Design Principles

- **Speed**: Just read files and summarize. No heavy scans.
- **No file output**: Report inline — this is a dashboard, not an artifact.
- **Actionable**: Always end with a clear "do this next" recommendation.
- **Context-aware**: If in a subproject (e.g., `mobile/`), check both local and parent directories for artifacts.
