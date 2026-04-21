import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIRS = ("core", "services")
FORBIDDEN_BACKEND_IMPORTS = {"PySide6", "PIL", "gui"}


class BackendBoundaryTests(unittest.TestCase):
    def test_backend_modules_do_not_import_desktop_dependencies(self) -> None:
        violations: list[str] = []

        for directory in BACKEND_DIRS:
            for path in (PROJECT_ROOT / directory).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    imported_root = self._imported_root_name(node)
                    if imported_root in FORBIDDEN_BACKEND_IMPORTS:
                        relative_path = path.relative_to(PROJECT_ROOT)
                        violations.append(f"{relative_path}: {imported_root}")

        self.assertEqual(violations, [])

    def test_backend_workflow_facade_imports_without_desktop_modules(self) -> None:
        import services.workflow_facade  # noqa: F401

    def _imported_root_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Import):
            return node.names[0].name.split(".", maxsplit=1)[0]

        if isinstance(node, ast.ImportFrom) and node.module is not None:
            return node.module.split(".", maxsplit=1)[0]

        return None
