---
paths: "**/*.{ts,tsx}"
---

# State Management & FSMs in React

## State Categorization — Use the Right Tool

| State Type | Tool | Example |
|---|---|---|
| Server/async state | TanStack Query | User data, orders list, API responses |
| Client UI state (local) | `useState` / `useReducer` | Modal open/close, active tab, form input |
| Client UI state (shared) | Zustand store | Sidebar collapsed, theme, notification queue |
| Form state | React Hook Form + Zod | Multi-step forms, validation |
| URL state | `nuqs` or `useSearchParams` | Filters, pagination, sort params |
| Complex state with transitions | Finite State Machine | Multi-step wizard, order lifecycle UI |

### Rules
- NEVER store server data in Zustand or `useState`. TanStack Query is the cache.
- NEVER use `useEffect` to sync state between sources — derive it instead.
- NEVER use `useContext` for frequently-changing state (causes full tree re-renders). Use Zustand.
- `useReducer` over `useState` when state transitions are complex or interdependent.

## Zustand Stores
- One store per domain concern. No god store.
- Keep stores minimal — only state that genuinely needs to be shared across distant components.
- Use slices pattern for organization if a store grows.
- Always define actions inside the store, not outside.

```typescript
import { create } from "zustand";

type NotificationStore = {
  notifications: Notification[];
  add: (notification: Notification) => void;
  dismiss: (id: string) => void;
  clear: () => void;
};

const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  add: (notification) =>
    set((state) => ({ notifications: [...state.notifications, notification] })),
  dismiss: (id) =>
    set((state) => ({ notifications: state.notifications.filter((n) => n.id !== id) })),
  clear: () => set({ notifications: [] }),
}));
```

## TanStack Query Conventions
- Define query keys as const arrays in a central `query-keys.ts` per feature.
- Wrap `useQuery` / `useMutation` in custom hooks: `useOrders()`, `useCreateOrder()`.
- Always handle loading, error, and empty states.
- Use `queryClient.invalidateQueries()` after mutations — don't manually update cache unless needed for optimistic UI.

```typescript
// features/orders/hooks/use-orders.ts
const orderKeys = {
  all: ["orders"] as const,
  list: (filters: OrderFilters) => [...orderKeys.all, "list", filters] as const,
  detail: (id: string) => [...orderKeys.all, "detail", id] as const,
};

export function useOrders(filters: OrderFilters) {
  return useQuery({
    queryKey: orderKeys.list(filters),
    queryFn: () => getOrders(filters),
  });
}
```

## Finite State Machines — Mandatory for Multi-State UI

ANY UI flow with 3+ states and constrained transitions MUST use an FSM.

### When to Use FSMs
- Multi-step wizards / onboarding flows.
- Complex form states (idle → validating → submitting → success/error).
- Entity lifecycle displayed in UI (matching backend FSM).
- Authentication flows (unauthenticated → loading → authenticated → expired).
- Async operations with retry logic.

### Implementation
Use XState or a lightweight custom FSM. Define states and transitions explicitly.

```typescript
const OrderStatusMachine = {
  DRAFT: { transitions: { SUBMIT: "PENDING", DELETE: "CANCELLED" } },
  PENDING: { transitions: { CONFIRM: "CONFIRMED", CANCEL: "CANCELLED" } },
  CONFIRMED: { transitions: { SHIP: "SHIPPED", CANCEL: "CANCELLED" } },
  SHIPPED: { transitions: { DELIVER: "DELIVERED" } },
  DELIVERED: { transitions: { REFUND: "REFUNDED" } },
  CANCELLED: { transitions: {} },
  REFUNDED: { transitions: {} },
} as const;

function canTransition(current: OrderStatus, action: string): boolean {
  const state = OrderStatusMachine[current];
  return action in state.transitions;
}
```

## URL State for Filters & Pagination
- Persist filter/sort/pagination state in URL search params — not in component state.
- Use `nuqs` (type-safe search params) or `useSearchParams`.
- This ensures shareable/bookmarkable URLs and survives page refreshes.
