---
paths: "**/*.{ts,tsx}"
---

# Next.js App Router — Architecture & Separation of Concerns

## Project Structure

```
src/
├── app/                        # Next.js App Router (routes & layouts ONLY)
│   ├── layout.tsx              # Root layout (providers, global styles)
│   ├── page.tsx                # Home page
│   ├── (auth)/                 # Route group for auth pages
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── dashboard/
│   │   ├── layout.tsx          # Dashboard-specific layout
│   │   ├── page.tsx
│   │   └── settings/page.tsx
│   └── api/                    # Route handlers (BFF / edge functions)
│       └── webhooks/route.ts
├── components/                 # Reusable UI components
│   ├── ui/                     # Primitives (Button, Input, Modal, etc.)
│   ├── forms/                  # Form-specific components
│   ├── layouts/                # Layout shells, sidebars, navbars
│   └── [domain]/              # Domain-grouped composites (e.g., orders/)
├── features/                   # Feature modules (self-contained slices)
│   ├── auth/
│   │   ├── components/         # Feature-specific components
│   │   ├── hooks/              # Feature-specific hooks
│   │   ├── services/           # API calls for this feature
│   │   ├── schemas/            # Zod schemas for this feature
│   │   └── types.ts            # Feature-specific types
│   └── orders/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── schemas/
│       └── types.ts
├── hooks/                      # Shared custom hooks
├── services/                   # API client layer (fetch/axios wrappers)
├── lib/                        # Framework utilities (auth config, db client, etc.)
├── schemas/                    # Shared Zod validation schemas
├── types/                      # Shared TypeScript types & interfaces
├── stores/                     # Client state (Zustand stores)
├── enums/                      # Shared enum definitions
├── state-machines/             # XState or custom FSM definitions
└── utils/                      # Pure helper functions (no side effects)
```

## Layer Responsibilities

### `app/` — Routing Layer
- Contains ONLY route segments (`page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `route.ts`).
- Pages are thin orchestrators: fetch data (server) or mount feature components (client).
- NO business logic, NO direct API calls (except in `route.ts` handlers), NO complex JSX.
- Keep pages under 50 lines — they compose feature components, nothing more.

```tsx
// GOOD — thin page, delegates to feature component
import { OrderList } from "@/features/orders/components/order-list";
import { getOrders } from "@/features/orders/services/get-orders";

export default async function OrdersPage() {
  const orders = await getOrders();
  return <OrderList initialOrders={orders} />;
}

// BAD — page doing too much
export default async function OrdersPage() {
  const res = await fetch("...");
  const data = await res.json();
  const filtered = data.filter(o => o.status !== "cancelled");
  return (
    <div className="grid grid-cols-3 gap-4">
      {filtered.map(order => (
        <div key={order.id} className="p-4 border rounded">
          {/* 80 lines of JSX */}
        </div>
      ))}
    </div>
  );
}
```

### `features/` — Feature Modules
- Self-contained vertical slices: each feature owns its components, hooks, services, schemas, types.
- Features may import from `components/`, `hooks/`, `services/`, `lib/`, `types/`, `enums/` (shared).
- Features MUST NOT import from other features. Cross-feature logic goes in a shared service or a new shared hook.

### `components/` — Shared UI Components
- Stateless, presentational, reusable.
- Accept data via props. No data fetching. No business logic.
- `components/ui/` contains design system primitives (Button, Input, Card, Dialog, etc.).
- Domain-grouped composites live in `components/[domain]/` for cross-feature reuse.

### `services/` — API Client Layer
- Typed functions that call external APIs and return typed data.
- Handle request/response transformation. No UI concerns.
- Use a shared API client instance (`lib/api-client.ts`) with base URL, interceptors, auth headers.

### `hooks/` — Shared Custom Hooks
- Reusable stateful logic.
- Follow the `use<Name>` naming convention.
- Must be pure React hooks — no direct API calls (delegate to services).

### `stores/` — Client State
- Zustand stores for client-only state that spans components.
- Keep stores small and domain-specific. No god store.
- Server state belongs in TanStack Query, NOT in stores.

## Server vs Client Components

- Default to Server Components. Only add `"use client"` when the component needs interactivity (event handlers, hooks, browser APIs).
- Push `"use client"` boundaries DOWN the tree — wrap the smallest interactive piece, not the whole page.
- Never pass functions as props from Server to Client components.
- Use the "donut pattern": server component wraps client component, passing data via props or children.

## Data Fetching Patterns

- **Server Components**: `fetch()` directly or call service functions. Use `cache()` for deduplication.
- **Client Components**: TanStack Query (`useQuery`, `useMutation`) for server state. Never `useEffect` + `useState` for data fetching.
- **Mutations**: TanStack Query `useMutation` with `onSuccess` cache invalidation.
- **Forms**: React Hook Form + Zod schema validation. Or Next.js Server Actions for simple forms.
