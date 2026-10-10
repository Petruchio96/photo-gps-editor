import os
import subprocess
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import app


class ExifToolStartupCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_ready_when_exiftool_is_available(self) -> None:
        with (
            patch("app.ExifToolWrapper.is_available", return_value=True),
            patch("app.QMessageBox.critical") as critical_mock,
        ):
            self.assertTrue(app.exiftool_is_ready())

        critical_mock.assert_not_called()

    def test_shows_error_when_exiftool_is_missing(self) -> None:
        with (
            patch("app.ExifToolWrapper.is_available", return_value=False),
            patch("app.QMessageBox.critical") as critical_mock,
        ):
            self.assertFalse(app.exiftool_is_ready())

        critical_mock.assert_called_once()
        title, message = critical_mock.call_args.args[1:3]
        self.assertEqual(title, "ExifTool Not Found")
        self.assertIn("https://exiftool.org", message)


class DesktopCursorTests(unittest.TestCase):
    def _run(self, values: dict[tuple[str, str], str], environ: dict[str, str]):
        def fake_run(command, **_kwargs):
            _gsettings, _get, schema, key = command
            value = values.get((schema, key))
            return subprocess.CompletedProcess(
                command, 0 if value is not None else 1, stdout=f"{value}\n" if value else ""
            )

        with (
            patch("app.sys.platform", "linux"),
            patch("app.shutil.which", return_value="/usr/bin/gsettings"),
            patch("app.subprocess.run", side_effect=fake_run),
            patch.dict(app.os.environ, environ, clear=True),
        ):
            app.match_desktop_cursor()
            return dict(app.os.environ)

    def test_uses_the_cinnamon_pointer_size_and_theme(self) -> None:
        environ = self._run(
            {
                ("org.cinnamon.desktop.interface", "cursor-size"): "31",
                ("org.cinnamon.desktop.interface", "cursor-theme"): "'Adwaita'",
            },
            {},
        )
        self.assertEqual(environ["XCURSOR_SIZE"], "31")
        self.assertEqual(environ["XCURSOR_THEME"], "Adwaita")

    def test_falls_back_to_gnome(self) -> None:
        environ = self._run({("org.gnome.desktop.interface", "cursor-size"): "48"}, {})
        self.assertEqual(environ["XCURSOR_SIZE"], "48")
        self.assertNotIn("XCURSOR_THEME", environ)

    def test_the_users_own_setting_wins(self) -> None:
        environ = self._run(
            {("org.cinnamon.desktop.interface", "cursor-size"): "31"},
            {"XCURSOR_SIZE": "64"},
        )
        self.assertEqual(environ["XCURSOR_SIZE"], "64")

    def test_nothing_changes_without_gsettings_values(self) -> None:
        environ = self._run({}, {})
        self.assertNotIn("XCURSOR_SIZE", environ)


if __name__ == "__main__":
    unittest.main()
