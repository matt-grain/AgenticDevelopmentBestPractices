---
paths: "**/*.{ts,tsx}"
---

# TypeScript Strict Typing & Style

## TypeScript Configuration
- `strict: true` in `tsconfig.json` — non-negotiable.
- `noUncheckedIndexedAccess: true` — array/object access returns `T | undefined`.
- `exactOptionalPropertyTypes: true` when possible.

## Type Annotations — Mandatory
- ALL function parameters and return types must be explicitly typed.
- ALL component props must have a named type/interface.
- Never use `any`. If truly unavoidable, use `unknown` and narrow with type guards.
- If `any` is absolutely necessary, add `// eslint-disable-next-line @typescript-eslint/no-explicit-any` with a comment explaining why.
- Use `as const` for literal types and readonly arrays.
- Use `satisfies` for type-safe object literals that preserve narrow types.

```typescript
// GOOD
const ORDER_STATUSES = ["draft", "pending", "confirmed"] as const;
type OrderStatus = (typeof ORDER_STATUSES)[number];

const config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
} satisfies AppConfig;

// BAD
const statuses: any = ["draft", "pending"];
```

## Enums & Constants
- Use `as const` objects or string union types instead of TypeScript `enum` (enums have runtime quirks).
- For shared constants with associated behavior, use a `Record` map.

```typescript
// Preferred — const object
const OrderStatus = {
  DRAFT: "draft",
  PENDING: "pending",
  CONFIRMED: "confirmed",
  SHIPPED: "shipped",
  DELIVERED: "delivered",
  CANCELLED: "cancelled",
} as const;

type OrderStatus = (typeof OrderStatus)[keyof typeof OrderStatus];

// Status display map
const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  [OrderStatus.DRAFT]: "Draft",
  [OrderStatus.PENDING]: "Pending",
  [OrderStatus.CONFIRMED]: "Confirmed",
  [OrderStatus.SHIPPED]: "Shipped",
  [OrderStatus.DELIVERED]: "Delivered",
  [OrderStatus.CANCELLED]: "Cancelled",
};
```

## Naming Conventions
- `PascalCase`: components, types, interfaces, enums.
- `camelCase`: functions, variables, hooks, props.
- `UPPER_SNAKE_CASE`: constants, enum-like const objects.
- `kebab-case`: file names and directory names.
- Prefix interfaces with nothing (no `I` prefix). Use `type` by default; `interface` only when extending is needed.
- Boolean props/variables: `is`, `has`, `can`, `should` prefix.

## Utility Types — Use Them
- `Partial<T>`, `Required<T>`, `Readonly<T>` for object manipulation.
- `Pick<T, K>`, `Omit<T, K>` for prop derivation.
- `Extract<T, U>`, `Exclude<T, U>` for union manipulation.
- `NonNullable<T>` to strip null/undefined.
- `ReturnType<T>`, `Parameters<T>` for function type extraction.
- Create custom utility types for project-specific patterns.

## Zod for Runtime Validation
- Use Zod schemas as the single source of truth for validation.
- Derive TypeScript types from Zod schemas with `z.infer<typeof schema>`.
- Validate at system boundaries: API responses, form inputs, URL params.

```typescript
import { z } from "zod";

const createOrderSchema = z.object({
  productId: z.string().uuid(),
  quantity: z.number().int().positive(),
  notes: z.string().max(500).optional(),
});

type CreateOrderInput = z.infer<typeof createOrderSchema>;
```

## Import Hygiene
- Use absolute imports with `@/` alias (maps to `src/`).
- Group imports: react/next → third-party → `@/lib` → `@/components` → `@/features` → relative.
- Use `type` imports for type-only imports: `import type { User } from "@/types"`.
- Never use `require()`.
