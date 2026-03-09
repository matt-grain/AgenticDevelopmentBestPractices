# Security Rules

These rules are injected into all agents to prevent common AI-generated security vulnerabilities.

**Context:** Research shows 25-30% of AI-generated code contains CWEs (Common Weakness Enumerations). AI assistants optimize for "code that runs," not "code that's secure."

---

## Injection Prevention (CWE-89, CWE-78, CWE-94)

### SQL Injection
- **NEVER** use f-strings, `.format()`, or `%` for SQL queries
- **ALWAYS** use parameterized queries or ORM methods

```python
# BAD — SQL injection vulnerability
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# GOOD — parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# GOOD — ORM (SQLAlchemy)
session.query(User).filter(User.id == user_id).first()
```

### Command Injection
- **NEVER** use `shell=True` with `subprocess`
- **NEVER** use `os.system()` — use `subprocess.run()` with list args
- **NEVER** use `eval()` or `exec()` on user input

```python
# BAD — command injection
os.system(f"grep {user_input} file.txt")
subprocess.run(f"ls {path}", shell=True)

# GOOD — no shell, list args
subprocess.run(["grep", user_input, "file.txt"], check=True)
```

### Code Injection
- **NEVER** use `eval()`, `exec()`, `compile()` with external input
- **NEVER** use `pickle.loads()` on untrusted data
- **NEVER** use `yaml.load()` — use `yaml.safe_load()`

---

## Secrets Management (CWE-798, CWE-259)

### Hardcoded Credentials
- **NEVER** hardcode passwords, API keys, tokens, or secrets in code
- **ALWAYS** use environment variables via `pydantic-settings`
- **ALWAYS** add secret patterns to `.gitignore`

```python
# BAD — hardcoded secret
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgres://user:password@host/db"

# GOOD — environment variables
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str

    model_config = ConfigDict(env_file=".env")
```

### Secret Detection Patterns
Flag any variable/string matching these patterns for review:
- `password`, `passwd`, `pwd`
- `secret`, `api_key`, `apikey`
- `token`, `auth`, `credential`
- `private_key`, `ssh_key`
- Base64-encoded strings > 20 chars
- Strings matching `sk-`, `pk_`, `ghp_`, `aws_`

---

## Input Validation (CWE-20)

### Boundary Validation
- **ALWAYS** validate user input at system boundaries (API endpoints, CLI args, file uploads)
- **ALWAYS** use Pydantic models with `Field()` constraints for API input
- **NEVER** trust client-side validation alone

```python
# GOOD — Pydantic validation at boundary
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    age: int = Field(..., ge=0, le=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower()
```

### Path Traversal (CWE-22)
- **NEVER** use user input directly in file paths
- **ALWAYS** use `pathlib` and validate against base directory

```python
# BAD — path traversal
filename = request.query_params["file"]
with open(f"/data/{filename}") as f:
    return f.read()

# GOOD — validated path
from pathlib import Path

BASE_DIR = Path("/data")
filename = request.query_params["file"]
filepath = (BASE_DIR / filename).resolve()

if not filepath.is_relative_to(BASE_DIR):
    raise ValueError("Invalid path")
```

---

## Authentication & Authorization (CWE-287, CWE-862)

### Authentication
- **ALWAYS** use established libraries (passlib, argon2, bcrypt) for password hashing
- **NEVER** implement custom crypto or hashing
- **ALWAYS** use constant-time comparison for secrets (`hmac.compare_digest`)

```python
# BAD — timing attack vulnerable
if user_token == stored_token:
    return True

# GOOD — constant-time comparison
import hmac
if hmac.compare_digest(user_token, stored_token):
    return True
```

### Authorization
- **ALWAYS** check authorization on every protected endpoint
- **NEVER** rely on obscurity (hidden URLs, unpredictable IDs)
- **ALWAYS** validate resource ownership before access

```python
# BAD — IDOR vulnerability (CWE-639)
@router.get("/orders/{order_id}")
async def get_order(order_id: int):
    return await order_repo.get(order_id)  # Anyone can access any order!

# GOOD — ownership check
@router.get("/orders/{order_id}")
async def get_order(order_id: int, current_user: User = Depends(get_current_user)):
    order = await order_repo.get(order_id)
    if order.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    return order
```

---

## Cryptography (CWE-327, CWE-328)

### Secure Defaults
- **NEVER** use MD5 or SHA1 for security purposes (only checksums)
- **ALWAYS** use SHA-256+ for hashing, AES-256 for encryption
- **NEVER** implement custom encryption — use `cryptography` library

### Random Number Generation
- **NEVER** use `random` module for security (predictable)
- **ALWAYS** use `secrets` module for tokens, keys, passwords

```python
# BAD — predictable
import random
token = ''.join(random.choices('abcdef0123456789', k=32))

# GOOD — cryptographically secure
import secrets
token = secrets.token_hex(16)
```

---

## Dependency Security

### Pinning
- **ALWAYS** pin all dependencies in lockfile (`uv.lock`, `pnpm-lock.yaml`)
- **NEVER** use floating versions (`>=`, `^`, `~`) for production

### Vulnerability Scanning
Run before every merge:
```bash
# Python
uv run pip-audit              # Check for known CVEs
uv run safety check           # Alternative CVE scanner

# JavaScript
npm audit --audit-level=moderate
pnpm audit --audit-level=moderate
```

### Supply Chain
- **PREFER** well-maintained packages (recent commits, multiple maintainers)
- **AVOID** packages with < 1000 weekly downloads
- **VERIFY** package name carefully (typosquatting attacks)

---

## Error Handling

### Information Disclosure (CWE-209)
- **NEVER** expose stack traces, SQL queries, or internal paths in API responses
- **ALWAYS** use generic error messages for clients, detailed logs for debugging

```python
# BAD — information disclosure
@router.get("/users/{id}")
async def get_user(id: int):
    try:
        return await repo.get(id)
    except Exception as e:
        raise HTTPException(500, str(e))  # Exposes internals!

# GOOD — safe error handling
@router.get("/users/{id}")
async def get_user(id: int):
    try:
        return await repo.get(id)
    except UserNotFoundError:
        raise HTTPException(404, "User not found")
    except Exception:
        logger.exception("Failed to get user %s", id)
        raise HTTPException(500, "Internal server error")
```

---

## OWASP Top 10 Quick Reference

| Risk | Prevention | Check |
|------|------------|-------|
| A01 Broken Access Control | Auth on every endpoint, ownership checks | Code review |
| A02 Cryptographic Failures | Use `secrets`, `cryptography`, no custom crypto | SAST |
| A03 Injection | Parameterized queries, no `eval`/`shell=True` | SAST + review |
| A04 Insecure Design | Threat modeling, security requirements | Architecture review |
| A05 Security Misconfiguration | Secure defaults, no debug in prod | Config audit |
| A06 Vulnerable Components | `pip-audit`, `npm audit`, pinned deps | SCA |
| A07 Auth Failures | Rate limiting, MFA, secure session | Penetration test |
| A08 Data Integrity Failures | Signed updates, CI/CD security | Pipeline review |
| A09 Logging Failures | Structured logging, no secrets in logs | Log audit |
| A10 SSRF | Validate URLs, allowlist domains | Code review |

---

---

## Flutter/Dart Specific Security

### Secure Storage
- **NEVER** store sensitive data in `SharedPreferences` without encryption
- **ALWAYS** use `flutter_secure_storage` for tokens, credentials, PII

```dart
// BAD — plaintext storage
final prefs = await SharedPreferences.getInstance();
await prefs.setString('auth_token', token);

// GOOD — encrypted storage
final storage = FlutterSecureStorage();
await storage.write(key: 'auth_token', value: token);
```

### Network Security
- **ALWAYS** use HTTPS, never HTTP for API calls
- **CONSIDER** certificate pinning for high-security apps
- **VALIDATE** SSL certificates (don't disable checks)

```dart
// BAD — disabled certificate verification
HttpClient client = HttpClient()
  ..badCertificateCallback = (cert, host, port) => true;  // DANGEROUS!

// GOOD — proper HTTPS
final response = await http.get(Uri.parse('https://api.example.com/data'));
```

### Platform Channels
- **VALIDATE** all data received from platform channels
- **NEVER** trust data from native code without validation
- **SANITIZE** strings passed to native evaluators

### Debug Code
- **ALWAYS** guard debug code with `kDebugMode`
- **NEVER** leave `print()` statements in production
- **REMOVE** debug flags before release

```dart
// BAD — debug code in production
print('User token: $token');

// GOOD — guarded debug
if (kDebugMode) {
  print('Debug: token loaded');
}
```

### Obfuscation
- **ENABLE** code obfuscation for release builds
- **USE** `--obfuscate --split-debug-info` flags

```bash
flutter build apk --obfuscate --split-debug-info=build/symbols
```

### Sensitive Data in Code
- **NEVER** hardcode API keys, secrets, or credentials
- **USE** `--dart-define` or environment config for secrets
- **EXCLUDE** `.env` files from version control

```dart
// BAD — hardcoded key
const apiKey = 'sk-1234567890abcdef';

// GOOD — build-time injection
const apiKey = String.fromEnvironment('API_KEY');
```

---

## Tooling Integration

These tools should be integrated into `/check` and CI pipelines:

```bash
# Python SAST
uv run bandit -r src/ -c pyproject.toml    # Security linter
uv run semgrep --config auto src/          # Pattern-based security

# Python SCA (dependency vulnerabilities)
uv run pip-audit                           # CVE database check
uv run safety check                        # Alternative scanner

# JavaScript
npx eslint --plugin security src/          # JS security rules
npm audit --audit-level=moderate           # Dependency CVEs

# Secrets detection
gitleaks detect --source .                 # Pre-commit secret scan
trufflehog filesystem .                    # Deep secret scan
```
