---
paths: "**/*.dart"
---

# Flutter State Management

## State Categorization — Use the Right Tool

| State Type | Tool | Example |
|---|---|---|
| Server/async state | Riverpod `AsyncValue` / Bloc | User data, orders list, API responses |
| Local ephemeral UI state | `StatefulWidget` / `ValueNotifier` | Animation, focus, scroll position, text input |
| Shared client state | Riverpod `StateProvider` / Cubit | Theme mode, selected tab, sidebar collapsed |
| Form state | `Form` + `TextEditingController` or reactive_forms | Multi-field forms, validation |
| Navigation state | GoRouter / auto_route | Current route, deep links, query params |
| Complex state with transitions | Finite State Machine (Bloc, freezed union) | Multi-step wizard, order lifecycle |

### Rules
- NEVER store server data in `StatefulWidget` `setState`. Use Riverpod or Bloc.
- NEVER fetch data in `initState` with manual `setState`. Use providers or `FutureBuilder` backed by a provider.
- NEVER use `ChangeNotifier` for new code — use Riverpod or Bloc instead (ChangeNotifier doesn't scale).
- Default to Riverpod for state management. Use Bloc when the team prefers or for complex event-driven state.

## Riverpod Patterns (Preferred)

### Provider Types — Use the Right One

| Provider | When to Use |
|---|---|
| `Provider` | Computed/derived values, DI registration |
| `FutureProvider` | Single async fetch (no refresh logic) |
| `StreamProvider` | Real-time data (WebSocket, Firestore) |
| `NotifierProvider` | Mutable state with methods |
| `AsyncNotifierProvider` | Mutable async state with methods (the workhorse) |

### Conventions
- Define providers at the top of the file or in a dedicated `providers/` directory per feature.
- Use `ref.watch` in `build()` — never `ref.read` (use `ref.read` only in callbacks/event handlers).
- Use `ref.invalidate` to force refresh — don't manually reset state.
- Use `autoDispose` by default — only omit when state must survive navigation.
- Family providers for parameterized queries (e.g., `orderProvider(orderId)`).

```dart
// features/orders/presentation/providers/orders_provider.dart
@riverpod
class Orders extends _$Orders {
  @override
  Future<List<Order>> build() async {
    final repository = ref.watch(orderRepositoryProvider);
    return repository.getOrders(const OrderFilter());
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => build());
  }

  Future<void> createOrder(CreateOrderParams params) async {
    final repository = ref.read(orderRepositoryProvider);
    await repository.createOrder(params);
    ref.invalidateSelf();
  }
}
```

## Bloc Patterns (Alternative)

### Conventions
- One Bloc/Cubit per feature concern. No god Bloc.
- Use `Cubit` for simple state (counter, toggle). Use `Bloc` for event-driven state with complex transitions.
- Events are past-tense (`OrderCreated`, `OrderStatusChanged`) — not imperative.
- States use `freezed` sealed classes for exhaustive pattern matching.
- Blocs never call other Blocs — use a shared use case or repository.

```dart
// States — freezed sealed class
@freezed
sealed class OrderState with _$OrderState {
  const factory OrderState.initial() = _Initial;
  const factory OrderState.loading() = _Loading;
  const factory OrderState.loaded(List<Order> orders) = _Loaded;
  const factory OrderState.error(String message) = _Error;
}

// Cubit
class OrdersCubit extends Cubit<OrderState> {
  OrdersCubit(this._getOrders) : super(const OrderState.initial());
  final GetOrders _getOrders;

  Future<void> loadOrders() async {
    emit(const OrderState.loading());
    final result = await _getOrders();
    result.fold(
      (failure) => emit(OrderState.error(failure.message)),
      (orders) => emit(OrderState.loaded(orders)),
    );
  }
}
```

## Finite State Machines — Mandatory for Multi-State Flows

ANY flow with 3+ states and constrained transitions MUST use an FSM.

### When to Use
- Multi-step wizards / onboarding flows.
- Order lifecycle displayed in UI (matching backend FSM).
- Authentication flows (unauthenticated → loading → authenticated → expired).
- Form submission states (idle → validating → submitting → success/error).
- Timer/countdown states.

### Implementation
Use `freezed` sealed classes + Bloc, or a dedicated FSM:

```dart
@freezed
sealed class CheckoutState with _$CheckoutState {
  const factory CheckoutState.cart(List<CartItem> items) = _Cart;
  const factory CheckoutState.shipping(ShippingForm form) = _Shipping;
  const factory CheckoutState.payment(PaymentForm form) = _Payment;
  const factory CheckoutState.processing() = _Processing;
  const factory CheckoutState.confirmed(Order order) = _Confirmed;
  const factory CheckoutState.failed(String reason) = _Failed;
}
```

## State Persistence
- Use `hydrated_bloc` or Riverpod persistence for state that survives app restart.
- Persist to `shared_preferences` for simple values, `Hive` for structured data.
- Never persist sensitive data unencrypted — use `flutter_secure_storage`.
