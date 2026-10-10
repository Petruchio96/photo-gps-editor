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


if __name__ == "__main__":
    unittest.main()
