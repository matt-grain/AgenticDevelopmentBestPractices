---
paths: "**/*.{ts,tsx}"
---

# Vite SPA Testing

## Same Principles as Next.js Testing
All rules from react-nextjs/testing.md apply. Key reminders:

- Test behavior, not implementation.
- Test names read as specs: `it("should display error when API call fails")`.
- Use React Testing Library with user-centric queries.
- MSW for API mocking at the network level.
- Vitest as test runner.

## Internal Tool Testing Priorities

Since internal tools are CRUD-heavy, focus testing effort here:

1. **Data tables**: Sorting, filtering, pagination, empty states, loading states.
2. **Forms**: Validation rules (from Zod), submission, error display, edit mode pre-fill.
3. **Auth guards**: Protected routes redirect unauthenticated users.
4. **Permission gates**: UI elements hidden/shown based on role.
5. **Critical workflows**: Multi-step operations (e.g., bulk actions, approval flows).

## What You Can Skip (for internal tools)
- Pixel-perfect visual regression tests (not worth the maintenance).
- Performance benchmarks (intranet, limited users).
- SEO testing (irrelevant).
- Exhaustive cross-browser testing (standardize on Chrome internally).
