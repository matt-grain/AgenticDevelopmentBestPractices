---
paths: "**/*.dart"
---

# Flutter — Layered Architecture & Separation of Concerns

## Project Structure

```
lib/
├── main.dart                       # App entry point, ProviderScope/BlocProviders, router
├── app.dart                        # MaterialApp/CupertinoApp configuration
├── router/                         # Routing configuration (GoRouter / auto_route)
│   ├── app_router.dart
│   └── guards/                     # Route guards (auth, role-based)
├── features/                       # Feature modules (self-contained vertical slices)
│   ├── auth/
│   │   ├── data/                   # Data layer: repositories, data sources, DTOs
│   │   │   ├── repositories/
│   │   │   ├── data_sources/       # Remote (API) and local (cache/DB) sources
│   │   │   └── models/             # DTOs / API response models (JSON serializable)
│   │   ├── domain/                 # Domain layer: entities, repository contracts, use cases
│   │   │   ├── entities/
│   │   │   ├── repositories/       # Abstract repository interfaces
│   │   │   └── use_cases/
│   │   └── presentation/           # UI layer: pages, widgets, state management
│   │       ├── pages/
│   │       ├── widgets/
│   │       └── providers/          # Riverpod providers / Bloc cubits
│   └── orders/
│       ├── data/
│       ├── domain/
│       └── presentation/
├── core/                           # Shared infrastructure
│   ├── config/                     # App configuration, environment
│   ├── constants/                  # App-wide constants
│   ├── errors/                     # Exception & failure classes
│   ├── network/                    # API client, interceptors, connectivity
│   ├── storage/                    # Local storage (Hive, SharedPreferences, Drift)
│   ├── theme/                      # ThemeData, colors, text styles
│   └── utils/                      # Pure helper functions (no business logic)
├── shared/                         # Shared UI components used across features
│   ├── widgets/                    # Reusable widgets (buttons, cards, inputs)
│   └── extensions/                 # Dart extension methods
└── l10n/                           # Localization (ARB files)
```

## Layer Responsibilities — Clean Architecture

### Presentation Layer (`presentation/`)
- Pages and widgets — UI only, no business logic.
- Pages are thin orchestrators: read state, render widgets, dispatch events.
- State management (Riverpod providers / Bloc) lives here but delegates to use cases.
- Never import from `data/` directly — always go through `domain/`.

```dart
// GOOD — thin page, delegates to provider/bloc
class OrdersPage extends ConsumerWidget {
  const OrdersPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(ordersProvider);
    return ordersAsync.when(
      data: (orders) => OrderList(orders: orders),
      loading: () => const OrderListSkeleton(),
      error: (error, _) => ErrorState(error: error),
    );
  }
}

// BAD — page doing data fetching and business logic
class OrdersPage extends StatefulWidget { ... }
// ... with http.get() calls, JSON parsing, filtering in setState
```

### Domain Layer (`domain/`)
- Pure Dart — no Flutter imports, no external packages.
- Entities are immutable domain objects (not DTOs).
- Repository interfaces (abstract classes) define data contracts.
- Use cases encapsulate single business operations.
- This layer has ZERO dependencies on `data/` or `presentation/`.

```dart
// domain/repositories/order_repository.dart
abstract class OrderRepository {
  Future<List<Order>> getOrders(OrderFilter filter);
  Future<Order> getOrder(String id);
  Future<Order> createOrder(CreateOrderParams params);
}

// domain/use_cases/create_order.dart
class CreateOrder {
  const CreateOrder(this._repository);
  final OrderRepository _repository;

  Future<Order> call(CreateOrderParams params) async {
    // Business validation here
    if (params.items.isEmpty) {
      throw const ValidationFailure('Order must have at least one item');
    }
    return _repository.createOrder(params);
  }
}
```

### Data Layer (`data/`)
- Implements domain repository interfaces with concrete data sources.
- DTOs (models) handle JSON serialization/deserialization.
- Data sources: remote (API calls) and local (cache, DB).
- Repository implementations coordinate between remote and local sources.
- Never expose DTOs above this layer — map to domain entities.

```dart
// data/repositories/order_repository_impl.dart
class OrderRepositoryImpl implements OrderRepository {
  const OrderRepositoryImpl(this._remoteSource, this._localSource);
  final OrderRemoteDataSource _remoteSource;
  final OrderLocalDataSource _localSource;

  @override
  Future<List<Order>> getOrders(OrderFilter filter) async {
    try {
      final dtos = await _remoteSource.getOrders(filter);
      await _localSource.cacheOrders(dtos);
      return dtos.map((dto) => dto.toEntity()).toList();
    } on NetworkException {
      final cached = await _localSource.getCachedOrders();
      return cached.map((dto) => dto.toEntity()).toList();
    }
  }
}
```

## Feature Module Rules

- Features are **self-contained vertical slices** — each owns its data, domain, and presentation.
- Features MUST NOT import from other features directly. Cross-feature communication goes through:
  - Shared domain contracts in `core/`
  - Navigation (passing IDs, not objects)
  - Shared state (if absolutely necessary)
- Keep features independent so they can be developed and tested in isolation.

## Dependency Rule

Dependencies point INWARD only:
```
presentation/ → domain/ ← data/
```
- `presentation/` depends on `domain/` (use cases, entities)
- `data/` depends on `domain/` (implements repository interfaces)
- `domain/` depends on NOTHING (pure Dart)
- `core/` is shared infrastructure — any layer can use it
- `shared/` is shared UI — only `presentation/` uses it
