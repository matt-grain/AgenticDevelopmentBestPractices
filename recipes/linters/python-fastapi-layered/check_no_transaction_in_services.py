"""Pre-commit check: services must not call `.commit()` / `.flush()` / `.rollback()`.

CLAUDE.md hard rule: transaction boundaries belong to the request scope (router DI)
or to a unit-of-work helper, never to the service layer.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker

FORBIDDEN_METHODS = frozenset({"commit", "flush", "rollback"})


class TransactionCallChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_Call(self, node: ast.Call) -> None:
        method_name: str | None = None
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
        if method_name in FORBIDDEN_METHODS:
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    f"Service calls `.{method_name}()` — transactions belong to the router/UoW layer",
                )
            )
        self.generic_visit(node)


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = TransactionCallChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    services_dir = Path("src/shipboard/services")
    if not services_dir.exists():
        print("src/shipboard/services/ does not exist yet — skipping")
        return 0
    files = iter_python_files(services_dir)
    return run_checker(check_file, files, "Services must not call .commit/.flush/.rollback")


if __name__ == "__main__":
    sys.exit(main())
