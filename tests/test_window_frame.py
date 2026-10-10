import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from gui import window_frame


class WindowFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_does_nothing_off_windows(self) -> None:
        widget = QWidget()
        with patch.object(window_frame.sys, "platform", "linux"), patch("ctypes.c_uint") as c_uint:
            window_frame.apply_window_border(widget)
        c_uint.assert_not_called()

    def test_sets_the_border_color_on_windows(self) -> None:
        widget = QWidget()
        dwmapi = MagicMock()
        with patch.object(window_frame.sys, "platform", "win32"), patch(
            "ctypes.windll", create=True
        ) as windll:
            windll.dwmapi = dwmapi
            window_frame.apply_window_border(widget)

        attribute = dwmapi.DwmSetWindowAttribute.call_args.args[1]
        self.assertEqual(attribute.value, window_frame.DWMWA_BORDER_COLOR)

    def test_never_raises_when_windows_refuses(self) -> None:
        widget = QWidget()
        with patch.object(window_frame.sys, "platform", "win32"), patch(
            "ctypes.windll", create=True
        ) as windll:
            windll.dwmapi.DwmSetWindowAttribute.side_effect = OSError("no DWM")
            window_frame.apply_window_border(widget)


if __name__ == "__main__":
    unittest.main()
