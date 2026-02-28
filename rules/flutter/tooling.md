---
paths: "**/*.dart"
---

# Flutter Tooling & Quality

## Package Manager — pub (via flutter/dart CLI)
- Use `flutter pub add <package>` to add dependencies.
- Use `flutter pub add --dev <package>` for dev dependencies.
- Use `pubspec.yaml` as the single source of truth for project metadata.
- Pin dependency versions with `^` (compatible) — avoid unconstrained ranges.
- Always commit `pubspec.lock` to the repository.

## Code Quality Validation — Run Before Every Commit

Execute ALL of the following checks. Code must pass all of them:

```bash
# Static analysis — strict mode
dart analyze --fatal-infos

# Formatting — must be consistent
dart format --set-exit-if-changed .

# Run code generators (freezed, json_serializable, riverpod_generator, etc.)
dart run build_runner build --delete-conflicting-outputs

# Run all tests
flutter test

# Check for outdated dependencies
flutter pub outdated
```

### Analysis Options (`analysis_options.yaml`)

```yaml
include: package:flutter_lints/flutter.yaml
# Or for stricter: package:very_good_analysis/analysis_options.yaml

analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
  errors:
    missing_return: error
    todo: info
    dead_code: warning
  exclude:
    - "**/*.g.dart"
    - "**/*.freezed.dart"

linter:
  rules:
    # Error prevention
    - always_use_package_imports  # or prefer_relative_imports — pick ONE
    - avoid_dynamic_calls
    - avoid_type_to_string
    - cancel_subscriptions
    - close_sinks
    - discarded_futures
    - no_adjacent_strings_without_concatenation
    - unawaited_futures
    - unnecessary_statements

    # Style
    - always_declare_return_types
    - annotate_overrides
    - avoid_bool_literals_in_conditional_expressions
    - avoid_catching_errors
    - avoid_equals_and_hash_code_on_mutable_classes
    - avoid_positional_boolean_parameters
    - avoid_returning_this
    - cascade_invocations
    - directives_ordering
    - eol_at_end_of_file
    - noop_primitive_operations
    - omit_local_variable_types  # let inference work for locals
    - prefer_const_constructors
    - prefer_const_declarations
    - prefer_final_fields
    - prefer_final_locals
    - prefer_single_quotes
    - require_trailing_commas
    - sort_constructors_first
    - sort_unnamed_constructors_first
    - unnecessary_lambdas
    - use_enums
    - use_if_null_to_convert_nulls_to_bools
    - use_named_constants
    - use_super_parameters
```

## Code Generation
- Use `build_runner` for freezed, json_serializable, riverpod_generator, auto_route.
- Generated files use `.g.dart` (json) and `.freezed.dart` (freezed) suffixes.
- NEVER edit generated files. They are excluded from analysis.
- Run `build_runner` before committing if models changed.
- Add generated files to `.gitignore` if the team prefers (some prefer to commit them for CI speed).

## Recommended Stack

| Concern | Package |
|---|---|
| State management | `riverpod` (preferred) or `flutter_bloc` |
| Routing | `go_router` or `auto_route` |
| HTTP client | `dio` |
| JSON serialization | `json_serializable` + `json_annotation` |
| Immutable models | `freezed` + `freezed_annotation` |
| DI (if not Riverpod) | `get_it` + `injectable` |
| Local storage | `hive` or `drift` (SQLite) |
| Secure storage | `flutter_secure_storage` |
| Forms | Built-in `Form` or `reactive_forms` |
| Testing mocks | `mocktail` |
| Bloc testing | `bloc_test` |
| Linting | `very_good_analysis` or `flutter_lints` |
| Monitoring | `sentry_flutter` |
| Pagination | `infinite_scroll_pagination` |

## Testing
- Use `flutter test` for unit + widget tests.
- Use `flutter test --coverage` to generate coverage reports.
- Use `integration_test` package for E2E tests.
- Structure tests to mirror `lib/` layout.
- Use `mocktail` for mocks, factory classes for test data.

## Build & Deployment
- Use `flutter build apk --release` / `flutter build ios --release` for production.
- Use flavors for environment separation (dev, staging, prod).
- Use `--dart-define` for compile-time environment variables.
- CI must run `dart analyze`, `dart format --set-exit-if-changed`, and `flutter test` on every PR.

## Module Size Limits
- A Dart file SHOULD NOT exceed 200 lines (excluding imports and generated code).
- A single function SHOULD NOT exceed 30 lines.
- A single class SHOULD NOT exceed 150 lines.
- Maximum function parameters: 5 — beyond that, use a params class or record.
- Cyclomatic complexity per function: keep below 10.

## Debug Logging — Production Safety

**NEVER use `print()` or `debugPrint()` in production code without a debug guard.**

```dart
// ❌ BAD — logs in release builds, exposes sensitive data
debugPrint('User token: $token');
debugPrint('Request failed: $error');

// ✅ GOOD — guarded with kDebugMode
import 'package:flutter/foundation.dart';

if (kDebugMode) {
  debugPrint('Debug info: $data');
}

// ✅ BETTER — use a logger that respects build mode
Logger.d('Debug info: $data');  // Logger class checks kDebugMode internally
```

### Sensitive Data in Logs
Even in debug mode, NEVER log:
- Tokens, passwords, API keys
- Full user PII (email, phone)
- Full request/response bodies with sensitive fields

### Dio LogInterceptor
Gate verbose HTTP logging behind `kDebugMode`:

```dart
if (kDebugMode) {
  dio.interceptors.add(LogInterceptor(
    requestBody: true,
    responseBody: true,
  ));
}
```

## Dio Response Handling

When accessing `response.data`, add a one-time justification comment per data source:

```dart
// Dio populates `data` for all 2xx responses; null is impossible here.
final data = response.data!;
```

This documents the intentional use of `!` and satisfies null-safety audits.
