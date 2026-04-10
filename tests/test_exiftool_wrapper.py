import json
import unittest
from pathlib import Path
from unittest.mock import patch

from core.exiftool_wrapper import ExifToolWrapper


class CompletedProcessStub:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ExifToolWrapperTests(unittest.TestCase):
    def test_is_available_checks_path(self) -> None:
        wrapper = ExifToolWrapper("custom-exiftool")

        with patch("core.exiftool_wrapper.shutil.which", return_value="/usr/bin/tool"):
            self.assertTrue(wrapper.is_available())

        with patch("core.exiftool_wrapper.shutil.which", return_value=None):
            self.assertFalse(wrapper.is_available())

    def test_read_gps_returns_coordinates(self) -> None:
        wrapper = ExifToolWrapper()
        payload = json.dumps([{"GPSLatitude": 40.5, "GPSLongitude": -111.8}])

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(0, stdout=payload),
        ) as run_mock:
            result = wrapper.read_gps(Path("/tmp/photo.jpg"))

        self.assertEqual(result, {"latitude": 40.5, "longitude": -111.8})
        command = run_mock.call_args.args[0]
        self.assertEqual(command[:4], ["exiftool", "-json", "-n", "-GPSLatitude"])

    def test_read_gps_returns_none_values_for_empty_payload(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(0, stdout="[]"),
        ):
            result = wrapper.read_gps(Path("/tmp/photo.jpg"))

        self.assertEqual(result, {"latitude": None, "longitude": None})

    def test_read_gps_raises_runtime_error_on_failure(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(1, stderr="bad read"),
        ):
            with self.assertRaisesRegex(RuntimeError, "bad read"):
                wrapper.read_gps(Path("/tmp/photo.jpg"))

    def test_write_gps_builds_expected_command_for_negative_values(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(0),
        ) as run_mock:
            wrapper.write_gps(Path("/tmp/photo.jpg"), -40.5, -111.8)

        command = run_mock.call_args.args[0]
        self.assertIn("-GPSLatitude=40.5", command)
        self.assertIn("-GPSLatitudeRef=S", command)
        self.assertIn("-GPSLongitude=111.8", command)
        self.assertIn("-GPSLongitudeRef=W", command)

    def test_write_gps_raises_runtime_error_on_failure(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(1, stderr="bad write"),
        ):
            with self.assertRaisesRegex(RuntimeError, "bad write"):
                wrapper.write_gps(Path("/tmp/photo.jpg"), 40.5, -111.8)


if __name__ == "__main__":
    unittest.main()
