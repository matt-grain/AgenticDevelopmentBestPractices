"""Pre-commit check: every class in `enums/` must inherit from StrEnum.

CLAUDE.md hard rule: status / type / environment fields are StrEnum, never raw
strings or `str, Enum` mixins (the mixin form does not preserve `__str__`
behavior in match statements with newer Python).
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker


def _is_strenum_base(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id == "StrEnum"
    if isinstance(base, ast.Attribute):
        return base.attr == "StrEnum"
    return False


class StrEnumChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not any(_is_strenum_base(b) for b in node.bases):
            self.violations.append(
                Violation(
                    self.file_path,
                    node.lineno,
                    f"Class '{node.name}' in enums/ must inherit from StrEnum",
                )
            )
        self.generic_visit(node)


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = StrEnumChecker(file_path)
    checker.visit(tree)
    return checker.violations


def main() -> int:
    enums_dir = Path("src/shipboard/enums")
    if not enums_dir.exists():
        print("src/shipboard/enums/ does not exist — skipping")
        return 0
    files = [f for f in iter_python_files(enums_dir) if f.name != "__init__.py"]
    return run_checker(check_file, files, "Classes in enums/ must inherit from StrEnum")


if __name__ == "__main__":
    sys.exit(main())
