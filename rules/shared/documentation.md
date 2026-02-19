# Architecture Documentation & Decision Records

## ARCHITECTURE.md — Mandatory, Living Document

Every project MUST have an `ARCHITECTURE.md` at the root. When creating or modifying code that affects the project structure, update this document.

### Required Sections

```markdown
# Architecture

## Overview
One-paragraph summary of what the system does and the high-level approach.

## Tech Stack
- Language, framework, DB, cache, message broker, etc.

## Project Structure
Tree view of directories with one-line descriptions.

## Layer Responsibilities
For each layer in the project:
- What it does
- What it must NOT do
- A short real code extract showing the pattern

## Data Flow
Describe a typical request/interaction lifecycle through the layers with a concrete example.

## Key Domain Concepts
List the core domain entities and their relationships.

## State Machines
For each stateful entity, document the states and valid transitions.
```

### Update Triggers
Update `ARCHITECTURE.md` when any of the following happens:
- A new domain entity or module is added.
- A new layer or pattern is introduced.
- A dependency is added or replaced.
- A state machine is created or modified.
- The data flow changes significantly.

### Code Extracts
Include short, real code snippets (not pseudo-code) showing the canonical pattern for each layer. These serve as copy-paste templates for developers (and agents) extending the system.

## decisions.md — Architecture Decision Records

Maintain a `decisions.md` file at the project root. Append a new entry when a non-trivial technical choice is made.

### ADR Format

```markdown
## YYYY-MM-DD — <Title>

**Status:** accepted | superseded by ADR-<N> | deprecated
**Context:** What situation or problem prompted this decision?
**Decision:** What did we choose and why?
**Alternatives considered:** What else was on the table?
**Consequences:** What are the trade-offs and implications?
```

### When to Write an ADR
- Choosing or replacing a library/framework.
- Adopting a new pattern (e.g., introducing FSMs, switching pagination strategy).
- Structural decisions (e.g., monorepo vs polyrepo, sync vs async).
- Security decisions (auth strategy, encryption approach).
- Decisions that future developers will wonder "why did they do it this way?"

### When NOT to Write an ADR
- Routine implementation choices that follow established patterns.
- Bug fixes that don't change architecture.
- Minor refactors within an existing pattern.

## Comments & Documentation — Sparingly, for the "Why"

- Do NOT add comments/docstrings to every function — only when the purpose or behavior is non-obvious.
- Comments explain **why** and **when to use**, not **what** (the code shows what).
- Never restate the function signature in the docstring/JSDoc.
