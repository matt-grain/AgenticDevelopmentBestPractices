---
paths: "**/*.dart"
---

# Dart Typing & Style

## Type Annotations
- ALL function parameters and return types must be explicitly typed. No reliance on inference for public APIs.
- ALL class fields must be typed.
- Use `void` explicitly for functions that return nothing.
- Private helper functions may rely on inference for local variables, but public APIs must be fully typed.
- Never use `dynamic` — use `Object` and type-check, or use generics. If `dynamic` is truly unavoidable, add a comment explaining why.
- Use `typedef` for complex function signatures.

### DTO Nested Objects — No `Map<String, dynamic>`
- **NEVER use `Map<String, dynamic>` or `Map<String, dynamic>?` for nested objects in DTOs.** This defers type checking to runtime and causes fragile `json['key']` access patterns.
- Create dedicated DTOs for nested objects and compose them.
- Use `@JsonKey` with `fromJson`/`toJson` for complex mappings.

```dart
// BAD — fragile runtime access
@freezed
class AdjustmentDto with _$AdjustmentDto {
  const factory AdjustmentDto({
    required String id,
    Map<String, dynamic>? location,  // ❌ What fields does location have?
    Map<String, dynamic>? item,      // ❌ Runtime crash waiting to happen
  }) = _AdjustmentDto;
}

// GOOD — typed nested DTOs
@freezed
class AdjustmentDto with _$AdjustmentDto {
  const factory AdjustmentDto({
    required String id,
    LocationDto? location,  // ✅ Typed, IDE autocomplete, compile-time safety
    ItemDto? item,          // ✅ Clear contract
  }) = _AdjustmentDto;
}
```

```dart
// GOOD
Future<List<Order>> getOrders({required OrderFilter filter}) async { ... }
typedef OrderCallback = void Function(Order order);

// BAD
getOrders({filter}) async { ... }  // Missing types everywhere
```

## Null Safety
- Embrace sound null safety — never use `!` (bang operator) without a preceding null check or guarantee.
- Prefer `?.` (null-aware) and `??` (null coalescing) over explicit null checks when possible.
- Use `late` only when you can guarantee initialization before access. Prefer nullable + null check.
- Never use `as` for downcasting without checking `is` first.

```dart
// GOOD
final name = user?.name ?? 'Anonymous';
if (value is String) { print(value.length); }

// BAD
final name = user!.name;  // Crash if user is null
final name = value as String;  // Crash if not String
```

## Immutability
- Domain entities and value objects MUST be immutable — use `@freezed` or manual `final` fields + `const` constructor.
- Use `@freezed` (from `freezed` package) for entities, unions, and sealed classes.
- Use `const` wherever possible — constructors, lists, widgets.
- Prefer `final` for all local variables unless reassignment is needed.
- Use `unmodifiable` wrappers for collections exposed from classes.

```dart
@freezed
class Order with _$Order {
  const factory Order({
    required String id,
    required OrderStatus status,
    required List<OrderItem> items,
    required DateTime createdAt,
  }) = _Order;
}
```

## Naming Conventions
- `PascalCase`: classes, enums, typedefs, extensions, mixins.
- `camelCase`: variables, functions, methods, parameters, named constructors.
- `SCREAMING_SNAKE_CASE`: constants (`static const`, top-level `const`).
- `_camelCase`: private members (single underscore prefix).
- `snake_case`: file names and directory names (`order_card.dart`, not `OrderCard.dart`).
- Boolean variables/parameters: `is`, `has`, `can`, `should` prefix.
- Callback parameters: `on` prefix (`onTap`, `onOrderCreated`, `onDismiss`).

## Enums
- Use enhanced enums (Dart 3.0+) with fields and methods.
- Never use raw strings for statuses, roles, types, categories.
- Store enum values in JSON via `.name` or a dedicated `value` field.

```dart
enum OrderStatus {
  draft('Draft'),
  pending('Pending'),
  confirmed('Confirmed'),
  shipped('Shipped'),
  delivered('Delivered'),
  cancelled('Cancelled');

  const OrderStatus(this.label);
  final String label;

  bool get isTerminal => this == delivered || this == cancelled;
}
```

### Enum Parsing — No Silent Fallbacks

When parsing enums from strings (e.g., from API), **NEVER silently fall back to a default value**. This hides bugs.

```dart
// ❌ BAD — silent fallback hides API contract violations
static ScanEntityType fromString(String value) {
  return ScanEntityType.values.firstWhere(
    (e) => e.name == value,
    orElse: () => ScanEntityType.item,  // Bug becomes invisible!
  );
}

// ✅ GOOD — throw on unknown value (fail fast)
static ScanEntityType fromString(String value) {
  return ScanEntityType.values.firstWhere(
    (e) => e.name == value,
    orElse: () => throw ArgumentError('Unknown ScanEntityType: $value'),
  );
}

// ✅ ALSO GOOD — return nullable and handle at call site
static ScanEntityType? tryFromString(String value) {
  return ScanEntityType.values.cast<ScanEntityType?>().firstWhere(
    (e) => e?.name == value,
    orElse: () => null,
  );
}
```

### Domain Enums — No Flutter Imports

Domain enums must be pure Dart. If you need icons, colors, or other Flutter types:
1. Keep the domain enum pure (no `IconData`, no `Color`)
2. Create a presentation-layer extension or mapper

```dart
// ❌ BAD — domain enum imports Flutter
// In features/foo/domain/enums/task_type.dart:
import 'package:flutter/material.dart';  // FORBIDDEN in domain!

enum TaskType {
  pickup(Icons.inventory),  // IconData in domain = layer violation
  delivery(Icons.local_shipping);

  const TaskType(this.icon);
  final IconData icon;
}

// ✅ GOOD — pure domain enum + presentation extension
// In features/foo/domain/enums/task_type.dart:
enum TaskType { pickup, delivery }

// In features/foo/presentation/extensions/task_type_ui.dart:
import 'package:flutter/material.dart';

extension TaskTypeUI on TaskType {
  IconData get icon => switch (this) {
    TaskType.pickup => Icons.inventory,
    TaskType.delivery => Icons.local_shipping,
  };

  Color get color => switch (this) {
    TaskType.pickup => Colors.blue,
    TaskType.delivery => Colors.green,
  };
}
```

## Collections & Patterns
- Use collection-`if` and collection-`for` in list/map literals.
- Use pattern matching (Dart 3.0+) for type checks and destructuring.
- Use `switch` expressions for exhaustive enum handling.
- Use records for lightweight multi-value returns.
- Prefer `Iterable` methods (`where`, `map`, `fold`) over manual loops for transformations.

```dart
// Switch expression — exhaustive
String statusLabel(OrderStatus status) => switch (status) {
  OrderStatus.draft => 'Draft',
  OrderStatus.pending => 'Pending Review',
  OrderStatus.confirmed => 'Confirmed',
  OrderStatus.shipped => 'In Transit',
  OrderStatus.delivered => 'Delivered',
  OrderStatus.cancelled => 'Cancelled',
};

// Pattern matching
if (result case Ok(value: final order)) {
  showOrder(order);
} else if (result case Err(error: final failure)) {
  showError(failure);
}
```

## Imports
- Use relative imports within the same package (`import '../models/order.dart';`).
- Use package imports for cross-package references (`import 'package:my_app/core/errors.dart';`).
- Group imports: dart → package → relative, separated by blank lines.
- Never use `show` / `hide` unless resolving name conflicts.
- Use `part` / `part of` ONLY for code generation (freezed, json_serializable). Never for manual code splitting.

## Error Handling
- Use typed Failure/Exception classes — never throw raw `Exception('message')`.
- Use `Either<Failure, T>` (from `dartz` or `fpdart`) or sealed Result types for expected failures.
- Reserve `try/catch` for unexpected errors at boundaries (API calls, DB operations).
- Create a failure hierarchy per feature.

```dart
sealed class OrderFailure {
  const OrderFailure();
}

class OrderNotFound extends OrderFailure {
  const OrderNotFound(this.orderId);
  final String orderId;
}

class InsufficientStock extends OrderFailure {
  const InsufficientStock(this.itemId, this.requested, this.available);
  final String itemId;
  final int requested;
  final int available;
}
```

## String Formatting
- Use string interpolation (`'Order $id'`) — never string concatenation for display strings.
- Use multi-line strings with triple quotes for long text.
- Use `raw` strings for regex patterns.
