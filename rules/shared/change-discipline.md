# Change Discipline & Cognitive Debt Prevention

## Before Writing Code — Understand First
- Before modifying an existing module, READ the related modules in the same layer and one layer above/below to understand context.
- Before adding a new pattern, CHECK if an existing pattern in the codebase already solves the problem.
- Before adding a dependency, CHECK if the existing stack already provides the capability.

## Structural Changes Require Explanation
When making changes that touch 3+ files or introduce a new pattern:
- Add a brief comment in the commit/PR explaining WHY, not just what.
- If the change introduces a pattern not yet in `ARCHITECTURE.md`, update the doc.
- If the change deviates from established patterns, document the reason as an ADR in `decisions.md`.

## No Black Boxes
- Every generated file must follow the project's established patterns. No "magic" modules that work but nobody understands.
- If generating boilerplate, follow the exact same structure as existing code in the project.
- When delegating work to an AI agent, the output must be reviewable: consistent style, clear naming, no unexplained cleverness.

## Dependency Hygiene
- Minimize external dependencies — each one is cognitive load for every future reader.
- Before adding a new package, evaluate: can the stdlib or an existing dependency handle this?
- Pin all dependencies via lockfile. No floating versions.
- Document non-obvious dependencies in `ARCHITECTURE.md` (why we use library X over library Y).

## Refactoring Discipline
- Refactor in dedicated commits/PRs — never mix refactoring with feature work.
- After refactoring, verify that test names and architecture docs still reflect reality.
- If a refactor changes the project structure, update `ARCHITECTURE.md` in the same commit.

## TODO / FIXME / HACK Comments
- Every `// TODO`, `// FIXME`, `// HACK` MUST include a tracker reference: `// TODO(#1234): reason`.
- TODOs without a reference are forbidden — they become invisible tech debt.
- If no issue tracker exists yet, create the issue first, then reference it.
- Agents generating code must NOT leave `// TODO` placeholders — either implement the feature or flag it as a gap in the implementation status.

## Code Review Signals (for Humans Reviewing Agent Output)
Flag for extra scrutiny:
- Any new catch-all utility file (`utils.ts`, `helpers.py`, etc.).
- Any function longer than 30 lines.
- Any file longer than 200 lines.
- Any `any`, `// @ts-ignore`, `# type: ignore` without justification.
- Any new dependency addition.
- Any deviation from the layered architecture.
- Any `// TODO` or `// FIXME` without a tracker reference.
