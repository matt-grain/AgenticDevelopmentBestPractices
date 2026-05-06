"""Pre-commit check: services must not accept SQLAlchemy `Session` / `AsyncSession`.

CLAUDE.md hard rule: services accept repositories via `__init__`, never a session.
The session lifecycle is owned by FastAPI's request scope (`get_session`) and
flows through repositories, not services. This keeps services unit-testable
without an in-memory DB.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker

FORBIDDEN_TYPE_NAMES = frozenset({"Session", "AsyncSession", "AsyncSessionFactory"})


def _annotation_mentions_forbidden(node: ast.expr | None) -> str | None:
    """Return the forbidden type name if `node` references one, else None."""
    if node is None:
        return None
    if isinstance(node, ast.Name) and node.id in FORBIDDEN_TYPE_NAMES:
        return node.id
    if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_TYPE_NAMES:
        return node.attr
    if isinstance(node, ast.Subscript):
        return _annotation_mentions_forbidden(node.value) or _annotation_mentions_forbidden(node.slice)
    if isinstance(node, ast.BinOp):
        return _annotation_mentions_forbidden(node.left) or _annotation_mentions_forbidden(node.right)
    if isinstance(node, ast.Tuple):
        for elt in node.elts:
            hit = _annotation_mentions_forbidden(elt)
            if hit:
                return hit
    return None


class SessionInServicesChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        all_args = list(node.args.args) + list(node.args.kwonlyargs) + list(node.args.posonlyargs)
        for arg in all_args:
            hit = _annotation_mentions_forbidden(arg.annotation)
            if hit:
                self.violations.append(
                    Violation(
                        self.file_path,
                        arg.lineno,
                        f"Service param '{arg.arg}: {hit}' — services take repositories, not sessions",
                    )
                )


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = SessionInServicesChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    services_dir = Path("src/shipboard/services")
    if not services_dir.exists():
        print("src/shipboard/services/ does not exist yet — skipping")
        return 0
    files = iter_python_files(services_dir)
    return run_checker(check_file, files, "Services must not take Session/AsyncSession parameters")


if __name__ == "__main__":
    sys.exit(main())
