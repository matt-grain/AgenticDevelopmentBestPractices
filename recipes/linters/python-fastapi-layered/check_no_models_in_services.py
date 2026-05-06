"""Pre-commit check: services must not import from `shipboard.models`.

CLAUDE.md hard rule: services compose repositories, never the ORM. If a service
needs to read or write to the DB, it goes through a repository — and repositories
return Pydantic schemas or scalars, never bare ORM rows.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker


class ModelsInServicesChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module == "shipboard.models" or module.startswith("shipboard.models."):
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    f"Service imports `{module}` — services depend on repositories, never ORM models",
                )
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "shipboard.models" or alias.name.startswith("shipboard.models."):
                self.violations.append(
                    Violation(
                        self.file_path,
                        node.lineno,
                        f"Service imports `{alias.name}` — go through a repository instead",
                    )
                )
        self.generic_visit(node)


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = ModelsInServicesChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    services_dir = Path("src/shipboard/services")
    if not services_dir.exists():
        print("src/shipboard/services/ does not exist yet — skipping")
        return 0
    files = iter_python_files(services_dir)
    return run_checker(check_file, files, "Services must not import shipboard.models")


if __name__ == "__main__":
    sys.exit(main())
