"""
Runtime path helpers for source and packaged execution.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path


def app_base_path() -> Path:
    """
    Return the base directory for bundled resources.

    PyInstaller exposes bundled data through ``sys._MEIPASS``. In source mode,
    the project root is the parent directory of ``core``.
    """
    bundle_path = getattr(sys, "_MEIPASS", None)
    if bundle_path:
        return Path(bundle_path)

    return Path(__file__).resolve().parent.parent


def resource_path(relative_path: str | Path) -> Path:
    """
    Resolve a project resource in both source and packaged modes.
    """
    return app_base_path() / relative_path


def platform_tool_directory_name() -> str:
    system_name = platform.system().lower()
    if system_name == "windows":
        return "windows"
    if system_name == "darwin":
        return "macos"

    return "linux"


def bundled_tool_path(executable_name: str) -> Path:
    """
    Return the expected path for a bundled helper executable.
    """
    return resource_path(
        Path("tools") / platform_tool_directory_name() / executable_name
    )


def default_exiftool_executable() -> str:
    """
    Prefer bundled ExifTool and fall back to PATH for source development.
    """
    executable_name = "exiftool.exe" if platform.system().lower() == "windows" else "exiftool"
    bundled_executable = bundled_tool_path(executable_name)
    if bundled_executable.exists():
        return str(bundled_executable)

    return "exiftool"
