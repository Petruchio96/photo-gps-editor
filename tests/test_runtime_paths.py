import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import runtime_paths


class RuntimePathTests(unittest.TestCase):
    def test_resource_path_uses_source_project_root_by_default(self) -> None:
        path = runtime_paths.resource_path("assets/app_icon_128.png")

        self.assertEqual(path, Path(__file__).resolve().parent.parent / "assets/app_icon_128.png")

    def test_resource_path_uses_pyinstaller_bundle_path_when_available(self) -> None:
        with patch.object(runtime_paths.sys, "_MEIPASS", "/tmp/photo-gps-bundle", create=True):
            path = runtime_paths.resource_path("assets/app_icon_128.png")

        self.assertEqual(path, Path("/tmp/photo-gps-bundle/assets/app_icon_128.png"))

    def test_default_exiftool_prefers_bundled_linux_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled = Path(temp_dir) / "tools" / "linux" / "exiftool"
            bundled.parent.mkdir(parents=True)
            bundled.write_text("#!/usr/bin/perl\n", encoding="utf-8")

            with (
                patch.object(runtime_paths.sys, "_MEIPASS", temp_dir, create=True),
                patch("core.runtime_paths.platform.system", return_value="Linux"),
            ):
                executable = runtime_paths.default_exiftool_executable()

        self.assertEqual(executable, str(bundled))

    def test_default_exiftool_uses_windows_executable_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled = Path(temp_dir) / "tools" / "windows" / "exiftool.exe"
            bundled.parent.mkdir(parents=True)
            bundled.write_text("placeholder", encoding="utf-8")

            with (
                patch.object(runtime_paths.sys, "_MEIPASS", temp_dir, create=True),
                patch("core.runtime_paths.platform.system", return_value="Windows"),
            ):
                executable = runtime_paths.default_exiftool_executable()

        self.assertEqual(executable, str(bundled))

    def test_default_exiftool_falls_back_to_path_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(runtime_paths.sys, "_MEIPASS", temp_dir, create=True),
                patch("core.runtime_paths.platform.system", return_value="Linux"),
            ):
                executable = runtime_paths.default_exiftool_executable()

        self.assertEqual(executable, "exiftool")


if __name__ == "__main__":
    unittest.main()
