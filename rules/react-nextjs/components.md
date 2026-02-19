---
paths: "**/*.{ts,tsx}"
---

# React Component Patterns

## Component Structure & Size
- A component file SHOULD NOT exceed 150 lines. If it does, extract sub-components or hooks.
- A component function SHOULD NOT exceed 80 lines of JSX. Break large returns into composed sub-components.
- One exported component per file. Co-located helper components (non-exported) are fine if small.
- File name matches the component name: `OrderCard.tsx` exports `OrderCard`.

## Composition Over Configuration
- Prefer composable components with `children` and render props over components with 10+ boolean props.
- Use the compound component pattern for complex UI (Tabs, Accordion, Dropdown).
- Avoid prop drilling beyond 2 levels — use Context or composition.

```tsx
// GOOD — composable
<Card>
  <Card.Header>
    <Card.Title>Order #{order.id}</Card.Title>
  </Card.Header>
  <Card.Body>{children}</Card.Body>
</Card>

// BAD — prop explosion
<Card
  title={`Order #${order.id}`}
  showHeader={true}
  headerVariant="primary"
  bodyPadding="lg"
  footerActions={[...]}
/>
```

## Props
- Always define props as a named `type` or `interface` (not inline).
- Props type name: `<ComponentName>Props`.
- Use `Pick<>`, `Omit<>`, and intersection types to derive props from existing types.
- Destructure props in the function signature.
- Default values: use JS defaults in destructuring, not `defaultProps`.

```tsx
type OrderCardProps = {
  order: OrderOut;
  onCancel?: (orderId: string) => void;
  isCompact?: boolean;
};

export function OrderCard({ order, onCancel, isCompact = false }: OrderCardProps) { ... }
```

## Hooks Discipline
- Extract complex logic into custom hooks: `useOrderFilters()`, `useDebounce()`.
- A component with more than 3 `useState` calls likely needs a custom hook or reducer.
- Never call hooks conditionally.
- `useEffect` is a last resort — prefer derived state, event handlers, and TanStack Query.
- Every `useEffect` must have a comment explaining WHY it's needed. If you can't explain it, you probably don't need it.

## Conditional Rendering
- Use early returns for guard clauses (loading, error, empty states).
- Avoid nested ternaries in JSX — extract to variables or sub-components.

```tsx
// GOOD — early returns
if (isLoading) return <Skeleton />;
if (error) return <ErrorState error={error} />;
if (orders.length === 0) return <EmptyState />;

return <OrderList orders={orders} />;

// BAD — nested ternaries
return isLoading ? <Skeleton /> : error ? <ErrorState /> : orders.length === 0 ? <EmptyState /> : <OrderList />;
```

## Event Handlers
- Name handlers `handle<Event>` in the component, `on<Event>` in props.
- Define handlers with `useCallback` only when passed to memoized children.
- Never define arrow functions inline in JSX for non-trivial logic.

## Error Boundaries
- Wrap each feature route with an `error.tsx` (Next.js) or custom `ErrorBoundary`.
- Show user-friendly error states, not raw error messages.
- Log errors to a monitoring service in the boundary's `onError`.

## Performance
- Use `React.memo()` only for components proven to re-render unnecessarily (measure first).
- Use `useMemo` / `useCallback` only when there's a measured need — not by default.
- Lazy load heavy components with `React.lazy()` / `next/dynamic`.
- Images: always use `next/image` with explicit `width` and `height`.
