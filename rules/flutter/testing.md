---
paths: "**/*.dart"
---

# Flutter Testing

## Test Naming — Tests Are Specs
- Test names MUST read as behavior specifications.
- Pattern: `'should <expected behavior> when <scenario>'` inside `test()` or `testWidgets()`.
- Group related tests with `group()` named after the class/widget under test.

```dart
// GOOD — readable specifications
group('OrderService', () {
  test('should return pending status when order is created with valid items', () { ... });
  test('should throw InsufficientStock when requested quantity exceeds available', () { ... });
  test('should transition to shipped when order is confirmed and dispatched', () { ... });
});

group('OrderCard', () {
  testWidgets('should display order total formatted as currency', (tester) async { ... });
  testWidgets('should show cancel button only for pending orders', (tester) async { ... });
});

// BAD — meaningless names
test('test order 1', () { ... });
test('create works', () { ... });
test('error case', () { ... });
```

## Test Structure — Arrange/Act/Assert
- Every test follows the AAA pattern with clear visual separation.
- Each section should be identifiable at a glance.

```dart
test('should apply discount when promo code is valid', () {
  // Arrange
  final order = OrderFactory.create(total: 100.0);
  final promoCode = PromoCode(code: 'SAVE20', discount: 0.2);

  // Act
  final result = order.applyPromo(promoCode);

  // Assert
  expect(result.total, equals(80.0));
  expect(result.appliedPromo, equals(promoCode));
});
```

## What to Test and Where

| Layer | What to Test | Tool |
|---|---|---|
| Domain entities | Business rules, validation, computed properties | `flutter_test` (unit) |
| Use cases | Orchestration logic, error mapping | `flutter_test` + `mockito`/`mocktail` |
| Repositories | Remote/local coordination, caching fallback | `flutter_test` + `mockito`/`mocktail` |
| Blocs/Cubits/Providers | State transitions, event handling | `bloc_test` / `riverpod` testing utils |
| Widgets | Rendering, interactions, conditional display | `flutter_test` (`testWidgets`) |
| Integration | Full feature flows with mocked API | `integration_test` package |

## Test Coverage Expectations
- Every public use case method: at least 1 happy-path + 1 error-path test.
- Every Bloc/Cubit: test all state transitions (valid AND invalid).
- Every FSM transition tested explicitly.
- Every custom validator/entity business rule tested.
- Widgets: test rendering, user interactions, conditional display.

## Widget Testing Principles
- **Test behavior, not implementation.** Find widgets by type, text, icon, or semantics — not by key (use Key as last resort).
- **Finder priority:** `find.text` > `find.byType` > `find.byIcon` > `find.bySemanticsLabel` > `find.byKey`.
- **Never test widget tree structure** — don't assert that a `Column` contains a `Text`. Assert what the user sees.
- **Pump correctly:** use `tester.pumpAndSettle()` for animations, `tester.pump()` for single frame.

```dart
testWidgets('should show error snackbar when order creation fails', (tester) async {
  // Arrange
  final mockOrderService = MockOrderService();
  when(() => mockOrderService.createOrder(any()))
      .thenThrow(const ServerFailure('Network error'));

  await tester.pumpWidget(
    createTestApp(
      overrides: [orderServiceProvider.overrideWithValue(mockOrderService)],
      child: const CreateOrderPage(),
    ),
  );

  // Act
  await tester.tap(find.text('Create Order'));
  await tester.pumpAndSettle();

  // Assert
  expect(find.text('Network error'), findsOneWidget);
  expect(find.byType(SnackBar), findsOneWidget);
});
```

## Mocking Strategy
- Use `mocktail` (preferred) or `mockito` for mocking.
- Mock at the repository/data source boundary — never mock Flutter framework internals.
- Use `ProviderScope overrides` (Riverpod) or `BlocProvider.value` (Bloc) to inject mocks in widget tests.
- Create reusable test helpers in `test/helpers/`.

## Test Organization
- Mirror `lib/` structure: `lib/features/orders/domain/` → `test/features/orders/domain/`.
- Integration tests in `integration_test/` at project root.
- Shared test utilities in `test/helpers/` (pump app, factories, mocks).
- Golden tests in `test/goldens/` if using visual regression.

## Test Factories
- Use factory functions or classes for test data — never hardcode values inline.
- Factories live in `test/factories/` or `test/helpers/`.

```dart
class OrderFactory {
  static Order create({
    String? id,
    OrderStatus status = OrderStatus.pending,
    double total = 100.0,
    List<OrderItem>? items,
  }) {
    return Order(
      id: id ?? const Uuid().v4(),
      status: status,
      total: total,
      items: items ?? [OrderItemFactory.create()],
      createdAt: DateTime.now(),
    );
  }
}
```

## Tests You Must NOT Skip
- Boundary conditions (empty list, zero quantity, max length, null values).
- Error states and failure paths for every async operation.
- Invalid FSM transitions (assert they throw or are rejected).
- Navigation guards (unauthenticated user accessing protected route).
- Loading and empty states for every async widget.
