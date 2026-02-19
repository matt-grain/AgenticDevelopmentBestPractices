---
paths: "**/*.dart"
---

# Flutter Widget Patterns

## Widget Structure & Size
- A widget file SHOULD NOT exceed 200 lines. If it does, extract sub-widgets or mixins.
- A `build()` method SHOULD NOT exceed 80 lines of widget tree. Break into composed sub-widgets.
- One public widget per file. Co-located private helper widgets are fine if small.
- File name matches the widget: `order_card.dart` exports `OrderCard`.

## Composition Over Configuration
- Prefer composable widgets with `child` / `children` over widgets with 10+ boolean parameters.
- Use the "slot" pattern for customizable areas.
- Avoid deep nesting — extract sub-widgets when nesting exceeds 5 levels.

```dart
// GOOD — composable
class AppCard extends StatelessWidget {
  const AppCard({super.key, this.header, required this.child});
  final Widget? header;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          if (header != null) header!,
          child,
        ],
      ),
    );
  }
}

// BAD — prop explosion
class AppCard extends StatelessWidget {
  const AppCard({
    required this.title,
    this.showHeader = true,
    this.headerColor,
    this.bodyPadding = 16,
    this.footerActions,
    this.showDivider = true,
    this.elevation = 2,
    // ... 10 more params
  });
}
```

## Widget Types — Use the Right One

| Type | When to Use |
|---|---|
| `StatelessWidget` | No mutable state, pure function of props |
| `StatefulWidget` | Local ephemeral state (animations, form fields, focus) |
| `ConsumerWidget` / `BlocBuilder` | Reads external state (Riverpod / Bloc) |
| `HookWidget` | Multiple pieces of local state (flutter_hooks) |

### Rules
- Default to `StatelessWidget`. Only upgrade when needed.
- Never use `StatefulWidget` for server data — use Riverpod/Bloc.
- Keep `StatefulWidget` for truly local concerns: animation controllers, scroll controllers, text editing controllers, focus nodes.
- If a `StatefulWidget` has more than 3 fields in `State`, consider a dedicated controller or provider.

## Constructor & Parameters
- Always use `const` constructors when possible.
- Always include `{super.key}` as first parameter.
- Use `required` for non-optional parameters.
- Default values in the constructor, not in `build()`.
- Use named parameters for everything except single `child` widgets.

```dart
class OrderCard extends StatelessWidget {
  const OrderCard({
    super.key,
    required this.order,
    this.onTap,
    this.isCompact = false,
  });

  final Order order;
  final VoidCallback? onTap;
  final bool isCompact;

  @override
  Widget build(BuildContext context) { ... }
}
```

## Keys
- Use `ValueKey` on list items when the list is dynamic (reordered, filtered, items added/removed).
- Use `ObjectKey` when items don't have a unique ID.
- Never use `UniqueKey` unless you explicitly want to force rebuild.
- `GlobalKey` is a last resort — prefer callbacks and controllers.

## Spacing & Layout
- Use `const SizedBox(height: N)` or `const SizedBox(width: N)` for spacing — not `Padding` with only one side.
- Use `gap` parameter in `Column`/`Row` (Flutter 3.10+) or a `Gap` widget.
- Use `EdgeInsets.symmetric` or `EdgeInsets.only` — avoid `EdgeInsets.fromLTRB` for readability.

## Conditional Rendering
- Use early returns for guard clauses (loading, error, empty states).
- Use `if` in collections for conditional children — avoid ternaries in widget trees.

```dart
// GOOD — early returns
@override
Widget build(BuildContext context) {
  if (isLoading) return const OrderListSkeleton();
  if (error != null) return ErrorState(error: error!);
  if (orders.isEmpty) return const EmptyState(message: 'No orders');

  return ListView.builder(
    itemCount: orders.length,
    itemBuilder: (context, index) => OrderCard(order: orders[index]),
  );
}

// GOOD — if in collection
Column(
  children: [
    const Header(),
    if (showBanner) const PromoBanner(),
    const OrderList(),
  ],
)

// BAD — ternary soup in widget tree
return isLoading
    ? const Skeleton()
    : error != null
        ? ErrorWidget(error: error)
        : orders.isEmpty
            ? const EmptyState()
            : ListView(...);
```

## Performance
- Use `const` constructors wherever possible — this is the single biggest Flutter optimization.
- Use `ListView.builder` (not `ListView(children: [])`) for long or dynamic lists.
- Use `RepaintBoundary` around expensive subtrees that animate independently.
- Never call `setState` or trigger rebuilds from `build()`.
- Use `AutomaticKeepAliveClientMixin` sparingly — only for expensive tab content.
- Profile with DevTools before optimizing — don't guess.
