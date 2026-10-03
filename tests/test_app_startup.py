import os
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


if __name__ == "__main__":
    unittest.main()
