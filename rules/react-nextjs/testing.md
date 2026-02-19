---
paths: "**/*.{ts,tsx}"
---

# React/Next.js Testing

## Test Naming — Tests Are Specs
- Test names describe user-visible behavior, not implementation.
- Pattern: `it("should <expected behavior> when <scenario>")`.

```typescript
// GOOD — behavior-focused
it("should display error message when login fails with invalid credentials");
it("should disable submit button while form is submitting");
it("should redirect to dashboard after successful login");
it("should show empty state when no orders exist");

// BAD — implementation-focused
it("should call setError with message");
it("should set isLoading to true");
it("should call router.push");
```

## Testing Library Principles
- **Test behavior, not implementation.** Query by role, label, text — not by class, id, or test-id (use `data-testid` as last resort).
- **User-centric queries** (priority order): `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- **Never test internal state** (don't assert on `useState` values or hook internals).
- **Never test styling** (don't assert on className or inline styles).

## What to Test

| Layer | What to test | Tool |
|---|---|---|
| Components | Rendering, user interactions, conditional display | React Testing Library + Vitest |
| Hooks | State changes, returned values, side effects | `renderHook` from RTL |
| Services | Request/response mapping, error handling | Vitest + MSW (Mock Service Worker) |
| Schemas | Validation rules, edge cases, transforms | Vitest (unit tests on Zod schemas) |
| FSMs | All valid transitions + all invalid transitions | Vitest (pure unit tests) |
| Pages (integration) | Full page render with mocked API, user flows | Playwright or Cypress |

## Test Structure — Arrange/Act/Assert

```typescript
it("should add item to cart when clicking add button", async () => {
  // Arrange
  const product = createMockProduct({ stock: 5 });
  render(<ProductCard product={product} />);

  // Act
  await userEvent.click(screen.getByRole("button", { name: /add to cart/i }));

  // Assert
  expect(screen.getByText(/added to cart/i)).toBeInTheDocument();
});
```

## Mocking Strategy
- Use MSW for API mocking — intercept at the network level, not at the function level.
- Mock at the boundary, not inside components. Prefer injecting mock services over `jest.mock()`.
- Never mock what you don't own unless behind an adapter.

## Test Organization
- Co-locate tests: `order-card.tsx` → `order-card.test.tsx` (same directory).
- Integration / E2E tests in `tests/` or `e2e/` at the project root.
- Shared test utilities in `tests/utils/` (render with providers, factories, etc.).
