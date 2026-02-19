---
paths: "**/*.dart"
---

# Flutter Patterns & Best Practices

## Error Handling
- Define a typed `Failure` hierarchy per feature (or shared in `core/errors/`).
- Use `Either<Failure, T>` or sealed `Result` types for expected business failures.
- Never show raw exceptions or stack traces to users — always map to user-friendly messages.
- Use `ErrorWidget.builder` to customize the red error screen in production.
- Implement a global error handler with `FlutterError.onError` and `PlatformDispatcher.instance.onError`.
- Log errors to a monitoring service (Sentry, Crashlytics) — never just `print`.

```dart
// core/errors/failures.dart
sealed class Failure {
  const Failure(this.message);
  final String message;
}

class ServerFailure extends Failure {
  const ServerFailure([super.message = 'Server error']);
  final int? statusCode;
}

class CacheFailure extends Failure {
  const CacheFailure([super.message = 'Cache error']);
}

class NetworkFailure extends Failure {
  const NetworkFailure([super.message = 'No internet connection']);
}
```

## Loading & Empty States
- Always show loading indicators during async operations — never a blank screen.
- Use skeleton/shimmer placeholders that match the shape of loaded content.
- Handle all 4 async states: initial, loading, data, error.
- Use `Riverpod AsyncValue.when()` or `BlocBuilder` for exhaustive state handling.

## Navigation
- Use declarative routing (GoRouter or auto_route) — not imperative `Navigator.push`.
- Define routes as constants or generated types — never hardcode path strings in multiple places.
- Use typed route parameters — not raw `Map<String, String>`.
- Protect routes with redirect guards (auth, role-based), not widget-level checks.
- Pass IDs as route params, not full objects — fetch fresh data on the destination page.

```dart
// router/app_router.dart (GoRouter)
final appRouter = GoRouter(
  redirect: (context, state) {
    final isAuthenticated = /* check auth */;
    if (!isAuthenticated && !state.matchedLocation.startsWith('/login')) {
      return '/login';
    }
    return null;
  },
  routes: [
    GoRoute(path: '/', builder: (_, __) => const HomePage()),
    GoRoute(
      path: '/orders/:id',
      builder: (_, state) => OrderDetailPage(
        orderId: state.pathParameters['id']!,
      ),
    ),
  ],
);
```

## Form Patterns
- Use `Form` widget with `GlobalKey<FormState>` for validation.
- Or use `reactive_forms` for complex forms with cross-field validation.
- Show validation errors inline, below the relevant field.
- Disable submit button during submission. Show loading indicator.
- Handle server-side validation errors by mapping them to form fields.
- Multi-step forms: use an FSM (Bloc/Cubit) to manage step transitions.

## API Client Pattern
- Single shared API client configured in `core/network/`.
- Use `dio` with interceptors for auth, logging, error mapping, retry.
- Type-safe: every endpoint function has typed input and output.
- Never call HTTP methods directly in features — always go through data sources.

```dart
// core/network/api_client.dart
class ApiClient {
  ApiClient(this._dio);
  final Dio _dio;

  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParams,
    required T Function(Map<String, dynamic>) fromJson,
  }) async {
    try {
      final response = await _dio.get(path, queryParameters: queryParams);
      return fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw _mapException(e);
    }
  }
}
```

## Dependency Injection
- Use Riverpod providers or `get_it` for DI. Never manually instantiate services in widgets.
- Register dependencies at app startup.
- Use abstract classes (interfaces) in domain, inject concrete implementations from data.
- Configuration and wiring happen in providers/modules, not inside business logic.

```dart
// With Riverpod
final orderRepositoryProvider = Provider<OrderRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final localDb = ref.watch(localDatabaseProvider);
  return OrderRepositoryImpl(
    OrderRemoteDataSource(apiClient),
    OrderLocalDataSource(localDb),
  );
});
```

## Pagination
- Always paginate list endpoints — never load unbounded collections.
- Use cursor-based pagination for infinite scroll, offset-based for page navigation.
- Implement with `infinite_scroll_pagination` package or custom Riverpod/Bloc logic.
- Show loading indicator at the bottom during next-page fetch.

## Localization
- Use `flutter_localizations` + ARB files for all user-visible strings.
- Never hardcode user-visible strings in widget code.
- Access via `AppLocalizations.of(context)` or generated `context.l10n`.
- Include plural forms and parameterized messages.

## Configuration & Environment
- Use `--dart-define` or `.env` files with `envied` package for environment config.
- Validate config at startup — fail fast on missing values.
- Never hardcode API URLs, keys, or environment-specific values.
- Separate config per environment: dev, staging, production.

## Security
- Store tokens in `flutter_secure_storage` — never `SharedPreferences`.
- Use HTTPS for all API calls — pin certificates for sensitive apps.
- Validate and sanitize all user input at the form/schema layer.
- Never log sensitive data (tokens, passwords, PII).
- Use `ProGuard`/`R8` (Android) and bitcode (iOS) for release builds.

## Accessibility
- All interactive elements must be accessible — use `Semantics` widget where needed.
- All images must have `semanticLabel`.
- Sufficient color contrast (WCAG AA minimum).
- Support dynamic type sizes (`MediaQuery.textScaleFactor`).
- Test with TalkBack (Android) and VoiceOver (iOS) at least once per major feature.

## Platform Adaptiveness
- Use `Platform.isIOS` / `Platform.isAndroid` sparingly — prefer `adaptive` widgets.
- Use Material 3 widgets with platform-adaptive behavior.
- Respect platform conventions (back gesture on iOS, material transitions on Android).
