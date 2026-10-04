import os
import tomllib
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from gui.main_window import APP_VERSION

PYPROJECT_PATH = Path(__file__).resolve().parent.parent / "pyproject.toml"


class VersionTests(unittest.TestCase):
    def test_about_dialog_version_matches_pyproject(self) -> None:
        # pyproject.toml is the source of truth; the packaged macOS app reads
        # its version from there, so the About dialog must match it.
        with PYPROJECT_PATH.open("rb") as pyproject_file:
            project_version = tomllib.load(pyproject_file)["project"]["version"]

        self.assertEqual(APP_VERSION, project_version)


if __name__ == "__main__":
    unittest.main()
