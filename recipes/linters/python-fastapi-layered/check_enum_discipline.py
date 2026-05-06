"""Pre-commit check: enum discipline — no raw string comparisons against known enum values.

`status == "active"` should be `status == ComponentStatus.ACTIVE`. This check
scans for ShipBoard's known enum values being used as raw string literals
inside `==` / `!=` / `in` comparisons. Files allowed: enums/ (definitions),
seed.py (raw SQL), seeds/, and tests.

ADAPT FOR YOUR PROJECT: replace KNOWN_ENUM_VALUES below with your own dict
mapping each enum member's string value to a human-readable suggestion of the
canonical enum reference. The whole point of this rule is that the dict is
project-specific — no generic version exists.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _base import Violation, iter_python_files, run_checker

KNOWN_ENUM_VALUES: dict[str, str] = {
    # ComponentStatus
    "planning": "ComponentStatus.PLANNING / PhaseType.PLANNING (depends on context)",
    "active": "ComponentStatus.ACTIVE",
    "maintenance": "ComponentStatus.MAINTENANCE",
    "shipped": "ComponentStatus.SHIPPED",
    "archived": "ComponentStatus.ARCHIVED",
    # MilestoneStatus
    "planned": "MilestoneStatus.PLANNED",
    "in_progress": "MilestoneStatus.IN_PROGRESS / DeploymentStatus.IN_PROGRESS",
    "at_risk": "MilestoneStatus.AT_RISK",
    "on_track": "MilestoneStatus.ON_TRACK",
    "completed": "MilestoneStatus.COMPLETED",
    "cancelled": "MilestoneStatus.CANCELLED",
    # DependencyType
    "hard": "DependencyType.HARD",
    "soft": "DependencyType.SOFT",
    "api": "DependencyType.API",
    # PRStatus
    "draft": "PRStatus.DRAFT",
    "open": "PRStatus.OPEN",
    "in_review": "PRStatus.IN_REVIEW",
    "approved": "PRStatus.APPROVED",
    "merged": "PRStatus.MERGED",
    "deployed_dev": "PRStatus.DEPLOYED_DEV",
    "deployed_staging": "PRStatus.DEPLOYED_STAGING",
    "deployed_prod": "PRStatus.DEPLOYED_PROD",
    "closed": "PRStatus.CLOSED",
    # PhaseType
    "implementation": "PhaseType.IMPLEMENTATION",
    "testing": "PhaseType.TESTING",
    "review": "PhaseType.REVIEW",
    "documentation": "PhaseType.DOCUMENTATION",
    "unknown": "PhaseType.UNKNOWN",
    # DeploymentEnvironment
    "dev": "DeploymentEnvironment.DEV",
    "staging": "DeploymentEnvironment.STAGING",
    "prod": "DeploymentEnvironment.PROD",
    # DeploymentStatus
    "pending": "DeploymentStatus.PENDING",
    "success": "DeploymentStatus.SUCCESS",
    "failed": "DeploymentStatus.FAILED",
    "rolled_back": "DeploymentStatus.ROLLED_BACK",
}


def _is_dot_value_comparison(node: ast.Compare) -> bool:
    """ORM/serialization boundary often does `status_col.value == "active"` — allow it."""
    if isinstance(node.left, ast.Attribute) and node.left.attr == "value":
        return True
    return any(isinstance(c, ast.Attribute) and c.attr == "value" for c in node.comparators)


class EnumDisciplineChecker(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []
        self._in_strenum = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        is_strenum = any(
            (isinstance(b, ast.Name) and b.id == "StrEnum")
            or (isinstance(b, ast.Attribute) and b.attr == "StrEnum")
            for b in node.bases
        )
        if is_strenum:
            return  # don't descend into enum class bodies
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if _is_dot_value_comparison(node):
            self.generic_visit(node)
            return
        operands: list[ast.expr] = [node.left, *node.comparators]
        for operand in operands:
            if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
                self._flag_if_known(operand.value, node.lineno)
        self.generic_visit(node)

    def _flag_if_known(self, value: str, lineno: int) -> None:
        suggestion = KNOWN_ENUM_VALUES.get(value)
        if suggestion is None:
            return
        self.violations.append(
            Violation(
                self.file_path,
                lineno,
                f'Raw string "{value}" in comparison — use {suggestion} instead',
            )
        )


def check_file(file_path: Path, tree: ast.AST) -> list[Violation]:
    checker = EnumDisciplineChecker(file_path)
    checker.visit(tree)
    return checker.violations


def _is_excluded(file_path: Path) -> bool:
    if "enums" in file_path.parts:
        return True
    if file_path.name == "seed.py":
        return True
    return False


def main() -> int:
    src_dir = Path("src")
    if not src_dir.exists():
        print("src/ directory not found")
        return 1
    files = [f for f in iter_python_files(src_dir) if not _is_excluded(f)]
    return run_checker(check_file, files, "Enum discipline (no raw string comparisons)")


if __name__ == "__main__":
    sys.exit(main())
