---
paths: "**/*.{ts,tsx}"
---

# Vite + React SPA — Architecture for Internal Tools

## Philosophy
Internal tools prioritize **developer speed, clarity, and maintainability** over SEO, performance optimization, or pixel-perfect design. Keep it simple. Ship fast. Make it obvious.

## Project Structure

```
src/
├── main.tsx                    # Entry point, router + providers
├── app.tsx                     # Root component (layout shell)
├── routes/                     # One file per route (page-level components)
│   ├── index.tsx               # Home / dashboard
│   ├── users.tsx
│   ├── users.$id.tsx           # Dynamic route param
│   └── settings.tsx
├── components/                 # Shared UI components
│   ├── ui/                     # Primitives (Button, Input, Table, Modal)
│   ├── layouts/                # Page shells, sidebars, navbars
│   └── data-display/           # Tables, cards, stat widgets
├── features/                   # Feature modules (self-contained slices)
│   ├── users/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── schemas/
│   │   └── types.ts
│   └── reports/
├── hooks/                      # Shared custom hooks
├── services/                   # API client layer
├── lib/                        # Config, auth, utilities
├── schemas/                    # Shared Zod schemas
├── types/                      # Shared TypeScript types
├── stores/                     # Zustand stores
├── enums/                      # Shared const objects / union types
└── utils/                      # Pure helpers
```

## Key Differences from Next.js

| Concern | Next.js (dynamic) | Vite SPA (internal tool) |
|---|---|---|
| Rendering | SSR + Server Components | Client-side only |
| Routing | File-based App Router | TanStack Router or React Router |
| Data fetching | Server fetch + TanStack Query | TanStack Query only |
| Auth | Middleware + server sessions | Client-side guards + token refresh |
| SEO | Important | Irrelevant (internal tool) |
| Bundle size | Critical | Less critical (intranet) |

## Routing
- Use TanStack Router (type-safe) or React Router.
- Define routes in a single `router.tsx` file or in `routes/` directory.
- Protect routes with auth guards at the router level.
- Use layout routes for shared shells (sidebar, navbar).

```tsx
// router.tsx — TanStack Router example
const routeTree = rootRoute.addChildren([
  indexRoute,
  usersRoute.addChildren([userDetailRoute]),
  settingsRoute,
]);
```

## Layer Rules (same SoC as backend)
- **Routes/Pages**: Thin — compose feature components, pass route params. No business logic.
- **Features**: Self-contained modules with their own components, hooks, services, types.
- **Components**: Stateless, reusable, presentational.
- **Services**: Typed API calls. Single shared API client.
- **Hooks**: Reusable stateful logic. Wrap TanStack Query in custom hooks.
- **Stores**: Zustand for shared client state only. Server state stays in TanStack Query.

## Internal Tool Specific Patterns

### Tables Are King
- Most internal tools are CRUD + data tables. Invest in a solid table setup.
- Use TanStack Table for complex tables (sorting, filtering, pagination, column visibility).
- Build a reusable `DataTable` component that accepts column definitions and data.
- Server-side pagination and filtering for large datasets. URL-synced params.

### Forms
- React Hook Form + Zod. Same as Next.js rules.
- For admin CRUD, generate forms from Zod schemas when possible.
- Always show form-level AND field-level errors.

### Optimistic UI — Keep It Simple
- For internal tools, prefer **invalidation after mutation** over optimistic updates.
- Optimistic updates add complexity. Only use for actions where latency hurts UX (e.g., toggling a switch).

### Toast Notifications
- Use a toast system for mutation feedback (success, error).
- Success: brief confirmation ("User created").
- Error: actionable message + retry option when possible.

### Role-Based Access
- Define roles and permissions as const objects.
- Gate UI elements with a `<Can>` component or `useCan()` hook.
- Always enforce permissions server-side too — client-side is UX only.

```tsx
const Permissions = {
  USERS_READ: "users:read",
  USERS_WRITE: "users:write",
  REPORTS_EXPORT: "reports:export",
} as const;

function Can({ permission, children }: { permission: Permission; children: ReactNode }) {
  const { hasPermission } = useAuth();
  return hasPermission(permission) ? <>{children}</> : null;
}
```
