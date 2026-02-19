---
paths: "**/*.py"
---

# Python Tooling & Package Management

## Package Manager — uv (mandatory)
- ALWAYS use `uv` as the package manager. Never pip, poetry, or pipenv.
- Use `uv add <package>` to add dependencies.
- Use `uv add --dev <package>` for dev dependencies.
- Use `uv run <command>` to execute tools and scripts.
- Use `uv sync` to install from lockfile.
- Use `uv lock` to regenerate lockfile.
- Maintain `pyproject.toml` as the single source of truth for project metadata.

## Code Quality Validation — Run Before Every Commit

Execute ALL of the following checks. Code must pass all of them:

```bash
# Type checking — strict mode
uv run pyright .

# Linting & auto-formatting
uv run ruff check . --fix
uv run ruff format .

# Security analysis
uv run bandit -r src/ -c pyproject.toml

# Type checking (alternative/complementary)
uv run ty check .

# Code complexity analysis — fail on high complexity
uv run radon cc src/ -a -nc

# Import linting
uv run lint-imports
```

### Tool Configuration (pyproject.toml)

```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "strict"
reportMissingTypeStubs = false

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "S",    # flake8-bandit (security)
    "A",    # flake8-builtins
    "C4",   # flake8-comprehensions
    "DTZ",  # flake8-datetimez
    "RET",  # flake8-return
    "PTH",  # flake8-use-pathlib
    "ERA",  # eradicate (dead code)
    "RUF",  # ruff-specific
    "ASYNC",# flake8-async
    "T20",  # flake8-print (no print statements)
]

[tool.ruff.lint.isort]
known-first-party = ["src"]

[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101"]  # allow assert in tests

[tool.importlinter]
root_packages = ["src"]

[[tool.importlinter.contracts]]
name = "Routers do not import repositories"
type = "forbidden"
source_modules = ["src.routers"]
forbidden_modules = ["src.repositories", "src.models"]

[[tool.importlinter.contracts]]
name = "Repositories do not import services"
type = "forbidden"
source_modules = ["src.repositories"]
forbidden_modules = ["src.services", "src.routers", "src.workflows"]
```

## Testing

- Use `pytest` with `pytest-asyncio` for async tests.
- Use `httpx.AsyncClient` with `app` transport for integration tests.
- Structure tests to mirror `src/` layout.
- Aim for service-layer unit tests + router-level integration tests.
- Use factories (e.g., `factory_boy` or custom fixtures) — never hardcode test data inline.
- Run tests via `uv run pytest`.
