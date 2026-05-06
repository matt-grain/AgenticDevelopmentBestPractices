"""Pre-commit check: HTTPException must stay in main.py / exception handlers.

ARCHITECTURE.md "Error translation" — services raise domain exceptions
(`NotFoundError`, `DuplicateError`, etc.); `main.py` registers handlers that
translate to HTTP status codes. Routers may raise HTTPException for HTTP-layer
concerns (path/query validation, auth gates) but services and repositories
must NOT.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker

ALLOWLISTED_FILE_NAMES = frozenset({"main.py", "exception_handlers.py", "exceptions.py"})
ALLOWLISTED_LAYER_PARTS = frozenset({"routers"})


def _is_allowlisted(file_path: Path) -> bool:
    if file_path.name in ALLOWLISTED_FILE_NAMES:
        return True
    return any(part in ALLOWLISTED_LAYER_PARTS for part in file_path.parts)


class HTTPExceptionChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module in {"fastapi", "fastapi.exceptions"}:
            for alias in node.names:
                if alias.name == "HTTPException":
                    self.violations.append(
                        Violation(
                            self.file_path,
                            node.lineno,
                            "HTTPException is only allowed in main.py / exception handlers / routers",
                        )
                    )
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is not None:
            name: str | None = None
            exc = node.exc
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Attribute):
                name = exc.func.attr
            if name == "HTTPException":
                self.violations.append(
                    Violation(
                        self.file_path,
                        node.lineno,
                        "raise HTTPException is only allowed in main.py / handlers / routers",
                    )
                )
        self.generic_visit(node)


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    if _is_allowlisted(file_path):
        return []
    checker = HTTPExceptionChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    src_dir = Path("src")
    if not src_dir.exists():
        print("src/ directory not found")
        return 1
    files = iter_python_files(src_dir)
    return run_checker(check_file, files, "HTTPException only in HTTP layer")


if __name__ == "__main__":
    sys.exit(main())
