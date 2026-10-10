import ast
import unittest
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent / "gui"


class NoBlockingDialogTests(unittest.TestCase):
    def test_gui_code_never_opens_a_dialog_with_exec(self) -> None:
        """
        exec() runs a second event loop inside the code that opened the
        dialog; background results arriving inside it crashed the Windows
        build. Dialogs use show() plus a callback (see MainWindow.show_message).
        """
        calls = []
        for path in GUI_DIR.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"exec", "exec_"}
                ):
                    calls.append(f"{path.relative_to(GUI_DIR.parent)}:{node.lineno}")

        self.assertEqual(calls, [])

    def test_gui_code_never_uses_the_blocking_message_box_shortcuts(self) -> None:
        """
        QMessageBox.warning() and friends run exec() inside: same problem.
        """
        shortcuts = {"warning", "information", "critical", "question", "about"}
        calls = []
        for path in GUI_DIR.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in shortcuts
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "QMessageBox"
                ):
                    calls.append(f"{path.relative_to(GUI_DIR.parent)}:{node.lineno}")

        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
