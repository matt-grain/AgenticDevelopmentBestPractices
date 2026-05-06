"""Pre-commit check: models use SQLAlchemy 2.0 typed `Mapped[...]` syntax.

ADR-005 + CLAUDE.md: every column declaration in `models/` uses
`Mapped[T] = mapped_column(...)`. Legacy `Column(...)` calls or untyped
`Mapped` (no subscript) are blocking.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker


class ModelMappedChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []
        self._inside_class = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._inside_class += 1
        self.generic_visit(node)
        self._inside_class -= 1

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._inside_class > 0:
            self._check_annotation(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._inside_class > 0 and self._is_legacy_column_call(node.value):
            target_name = self._first_target_name(node)
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    (
                        f"Untyped Column() at '{target_name}' — use "
                        "`Mapped[T] = mapped_column(...)` (SQLAlchemy 2.0 typed style)"
                    ),
                )
            )
        self.generic_visit(node)

    def _check_annotation(self, node: ast.AnnAssign) -> None:
        if not isinstance(node.target, ast.Name):
            return
        ann = node.annotation
        if isinstance(ann, ast.Subscript):
            head = ann.value
            if (isinstance(head, ast.Name) and head.id == "Mapped") or (
                isinstance(head, ast.Attribute) and head.attr == "Mapped"
            ):
                if self._is_legacy_column_call(node.value):
                    self.violations.append(
                        Violation(
                            self.file_path,
                            node.lineno,
                            f"Field '{node.target.id}' uses Column() — switch to mapped_column()",
                        )
                    )
                return
        if isinstance(ann, ast.Name) and ann.id == "Mapped":
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    f"Field '{node.target.id}' uses bare `Mapped` — must be `Mapped[T]`",
                )
            )

    def _is_legacy_column_call(self, value: ast.expr | None) -> bool:
        if value is None:
            return False
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name) and value.func.id == "Column":
                return True
            if isinstance(value.func, ast.Attribute) and value.func.attr == "Column":
                return True
        return False

    @staticmethod
    def _first_target_name(node: ast.Assign) -> str:
        if node.targets and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
        return "<expr>"


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = ModelMappedChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    models_dir = Path("src/shipboard/models")
    if not models_dir.exists():
        print("src/shipboard/models/ does not exist — skipping")
        return 0
    files = [f for f in iter_python_files(models_dir) if f.name != "__init__.py"]
    return run_checker(check_file, files, "Models use SQLAlchemy 2.0 typed Mapped[...] syntax")


if __name__ == "__main__":
    sys.exit(main())
