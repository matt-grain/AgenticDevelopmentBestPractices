"""Shared utilities for pre-commit check scripts."""

import ast
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """A single code violation to report."""

    file: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.message}"


def iter_python_files(directory: Path, exclude_patterns: list[str] | None = None) -> list[Path]:
    """Iterate Python files under `directory`, skipping anything matching the exclusion patterns."""
    exclude = exclude_patterns or ["__pycache__", ".venv", "tests"]
    files: list[Path] = []
    for path in directory.rglob("*.py"):
        if not any(excl in str(path) for excl in exclude):
            files.append(path)
    return sorted(files)


def parse_file(file_path: Path) -> ast.AST | None:
    """Parse a Python file. Returns `None` (after printing) on syntax error."""
    try:
        return ast.parse(file_path.read_text(encoding="utf-8"), str(file_path))
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return None


def run_checker(
    checker_func: Callable[[Path, ast.AST], list[Violation]],
    files: list[Path],
    description: str,
) -> int:
    """Apply `checker_func` to each file and report. Returns shell-exit-style int."""
    violations: list[Violation] = []
    for file_path in files:
        tree = parse_file(file_path)
        if tree is not None:
            violations.extend(checker_func(file_path, tree))

    if violations:
        print("=" * 70)
        print(f"VIOLATION: {description}")
        print("=" * 70)
        print()
        for v in violations:
            print(f"  {v}")
        print()
        print(f"Total: {len(violations)} violation(s)")
        return 1

    print(f"OK: {description} - checked {len(files)} file(s)")
    return 0
