---
paths: "**/*.{ts,tsx}"
---

# Vite SPA Tooling & Quality

## Package Manager — pnpm (preferred) or bun
- Same as Next.js projects. Use `pnpm` or `bun`. Never npm or yarn.

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

# Build verification
pnpm vite build
```

## Vite Configuration
- Use `vite-tsconfig-paths` for `@/` alias support.
- Enable source maps in dev, disable in production builds.
- Use `vite-plugin-checker` for in-dev type checking overlay.

## Recommended Stack

| Concern | Library |
|---|---|
| Bundler | Vite |
| Styling | Tailwind CSS |
| UI primitives | shadcn/ui |
| Routing | TanStack Router (type-safe) or React Router |
| Tables | TanStack Table |
| Forms | React Hook Form + Zod |
| Server state | TanStack Query |
| Client state | Zustand |
| API mocking | MSW |
| Testing | Vitest + React Testing Library |
| E2E testing | Playwright |
| Date handling | date-fns |
| Icons | Lucide React |
| Toasts | sonner |

## ESLint Configuration
- Same strict configuration as Next.js projects.
- Extend: `plugin:@typescript-eslint/strict-type-checked`, `plugin:react-hooks/recommended`.
- `@typescript-eslint/no-explicit-any` as error.
- `import/order` for consistent imports.

## Environment Variables
- Prefix with `VITE_` for client exposure.
- Validate with Zod at startup, same pattern as Next.js.

```typescript
const envSchema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_APP_TITLE: z.string().default("Admin"),
});

export const env = envSchema.parse(import.meta.env);
```
