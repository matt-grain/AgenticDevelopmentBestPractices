---
paths: "**/*.{ts,tsx}"
---

# React/Next.js Patterns & Best Practices

## Error Handling
- Use `error.tsx` at each route segment for granular error boundaries.
- Display user-friendly messages. Never show raw error objects or stack traces.
- Provide actionable recovery (retry button, navigate back, contact support).
- Log errors to a monitoring service (Sentry, etc.) in the error boundary.
- API services should throw typed error classes, not raw `Error`.

```typescript
class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
```

## Loading States
- Use `loading.tsx` for route-level Suspense boundaries.
- Use skeleton components that match the shape of the loaded content.
- Never show a blank page — always provide visual feedback.
- Use `Suspense` boundaries to stream server components progressively.

## Form Patterns
- React Hook Form + Zod for validation. One schema shared between frontend and API.
- Show validation errors inline, next to the relevant field.
- Disable submit during submission. Show loading indicator.
- Handle server-side validation errors by mapping them to form fields.
- Multi-step forms: use a wizard FSM to manage step transitions.

## Pagination, Filtering, Sorting
- Always store these in URL search params (not component state).
- Use server-side pagination for large datasets.
- Provide loading states during page transitions.
- Debounce search/filter inputs (300ms default).

## Authentication Pattern
- Auth state managed in `lib/auth.ts` (NextAuth.js / custom).
- Protect routes with middleware (`middleware.ts`) — not with client-side checks.
- Use server-side session validation in Server Components.
- Client components access auth via a `useAuth()` hook backed by Context.

## API Client Pattern
- Single shared API client configured in `lib/api-client.ts`.
- Centralized error handling, auth header injection, base URL.
- Type-safe: every endpoint function has typed input and output.
- Feature services import the client and add domain-specific logic.

```typescript
// lib/api-client.ts
async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${env.API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }

  return response.json() as Promise<T>;
}

// features/orders/services/get-orders.ts
export async function getOrders(filters: OrderFilters): Promise<PaginatedResponse<OrderOut>> {
  const params = new URLSearchParams(filters as Record<string, string>);
  return apiClient<PaginatedResponse<OrderOut>>(`/orders?${params}`);
}
```

## Environment Variables
- Validate with Zod at startup in `lib/env.ts`. Fail fast on missing vars.
- Prefix client-exposed vars with `NEXT_PUBLIC_`.
- Never access `process.env` directly — always go through the typed `env` object.

```typescript
import { z } from "zod";

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  API_URL: z.string().url(),
  NEXT_PUBLIC_APP_URL: z.string().url(),
});

export const env = envSchema.parse(process.env);
```

## Accessibility
- All interactive elements must be keyboard-accessible.
- Use semantic HTML (`button`, `nav`, `main`, `section`, `article`).
- All images must have `alt` text.
- Form inputs must have associated labels (`<label>` or `aria-label`).
- Color is never the only indicator — use icons, text, or patterns alongside color.
- Test with a screen reader at least once per major feature.
