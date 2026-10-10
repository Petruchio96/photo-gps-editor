"""
A clearer edge for the app's extra windows on Windows 11.

Windows 11 draws a very faint 1-pixel border around windows, so the map,
the picker, and Settings were hard to tell apart from the main window behind
them. The system lets an app pick that border's color; a soft slate keeps it
subtle but visible. Linux and macOS window managers already draw a shadow or
edge, so nothing changes there (or on Windows 10, which has no such setting).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QWidget

# DwmSetWindowAttribute's "border color" setting (Windows 11, build 22000+).
DWMWA_BORDER_COLOR = 34

# The border color: slate, the same as the app's disabled-button gray.
BORDER_RGB = (0x8F, 0xA1, 0xB4)


def apply_window_border(widget: QWidget) -> None:
    """
    Give a top-level window a visible slate border on Windows 11. Does
    nothing elsewhere, and never raises: the border is a nicety.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        red, green, blue = BORDER_RGB
        # Windows COLORREF is 0x00BBGGRR.
        color = ctypes.c_uint(red | (green << 8) | (blue << 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(widget.winId())),
            ctypes.c_uint(DWMWA_BORDER_COLOR),
            ctypes.byref(color),
            ctypes.sizeof(color),
        )
    except Exception:
        # Older Windows or no DWM: keep the system's border.
        pass
