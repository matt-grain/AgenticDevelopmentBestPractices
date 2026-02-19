---
paths: "**/*.{ts,tsx}"
---

# Next.js Tooling & Quality

## Package Manager — pnpm (preferred) or bun
- Use `pnpm` or `bun` for package management. Never npm or yarn.
- Use lockfile. Commit it to the repository.
- Use `pnpm dlx` / `bunx` for one-off commands.

## Code Quality — Run Before Every Commit

```bash
# Type checking
pnpm tsc --noEmit

# Linting
pnpm eslint . --fix

# Formatting
pnpm prettier --write .

# Unit tests
pnpm vitest run

# Build verification (catches SSR issues)
pnpm next build
```

## ESLint Configuration
- Extend: `next/core-web-vitals`, `next/typescript`, `plugin:@typescript-eslint/strict-type-checked`.
- Enable `@typescript-eslint/no-explicit-any` as error.
- Enable `@typescript-eslint/no-unused-vars` as error.
- Enable `import/order` for consistent import grouping.
- Enable `react-hooks/exhaustive-deps` as error.

## Recommended Stack

| Concern | Library |
|---|---|
| Framework | Next.js (App Router) |
| Styling | Tailwind CSS |
| UI primitives | shadcn/ui (copy-paste, not a dependency) |
| Forms | React Hook Form + Zod |
| Server state | TanStack Query |
| Client state | Zustand |
| API mocking | MSW |
| Testing | Vitest + React Testing Library |
| E2E testing | Playwright |
| FSM (if complex) | XState |
| Date handling | date-fns |
| URL state | nuqs |
| Icons | Lucide React |
