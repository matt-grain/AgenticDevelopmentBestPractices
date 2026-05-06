"""Pre-commit check: workflows must not import from `shipboard.repositories`.

Workflows compose services — never repositories. All data access flows through
service methods. If a workflow needs data that no service exposes, ADD the
service method first (single responsibility), then call it from the workflow.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker


class ReposInWorkflowsChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module == "shipboard.repositories" or module.startswith("shipboard.repositories."):
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    f"Workflow imports `{module}` — workflows compose services, not repositories",
                )
            )
        if module == "shipboard.models" or module.startswith("shipboard.models."):
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    f"Workflow imports `{module}` — go through a service",
                )
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.startswith("shipboard.repositories"):
                self.violations.append(
                    Violation(
                        self.file_path,
                        node.lineno,
                        f"Workflow imports `{alias.name}` — go through a service",
                    )
                )
            if alias.name.startswith("shipboard.models"):
                self.violations.append(
                    Violation(
                        self.file_path,
                        node.lineno,
                        f"Workflow imports `{alias.name}` — go through a service",
                    )
                )
        self.generic_visit(node)


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = ReposInWorkflowsChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    workflows_dir = Path("src/shipboard/workflows")
    if not workflows_dir.exists():
        print("src/shipboard/workflows/ does not exist yet — skipping")
        return 0
    files = iter_python_files(workflows_dir)
    return run_checker(check_file, files, "Workflows must not import repositories or models")


if __name__ == "__main__":
    sys.exit(main())
