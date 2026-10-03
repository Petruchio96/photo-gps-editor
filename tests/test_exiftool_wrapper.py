import json
import subprocess
import tempfile
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
        self.assertEqual(
            command,
            [
                "exiftool",
                "-charset",
                "filename=utf8",
                "-json",
                "-n",
                "-GPSLatitude",
                "-GPSLongitude",
                "-@",
                "-",
            ],
        )
        self.assertEqual(run_mock.call_args.kwargs["input"], "/tmp/photo.jpg\n")

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

    def test_read_gps_many_returns_coordinates_by_path(self) -> None:
        wrapper = ExifToolWrapper()
        first = Path("/tmp/first.jpg")
        second = Path("/tmp/second.jpg")
        payload = json.dumps(
            [
                {
                    "SourceFile": str(first),
                    "GPSLatitude": 40.5,
                    "GPSLongitude": -111.8,
                },
                {
                    "SourceFile": str(second),
                    "GPSLatitude": None,
                    "GPSLongitude": None,
                },
            ]
        )

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(0, stdout=payload),
        ) as run_mock:
            result = wrapper.read_gps_many([first, second])

        self.assertEqual(
            result,
            {
                first: {"latitude": 40.5, "longitude": -111.8},
                second: {"latitude": None, "longitude": None},
            },
        )
        command = run_mock.call_args.args[0]
        self.assertEqual(command[3:7], ["-json", "-n", "-GPSLatitude", "-GPSLongitude"])
        self.assertEqual(command[-2:], ["-@", "-"])
        self.assertEqual(
            run_mock.call_args.kwargs["input"],
            f"{first}\n{second}\n",
        )

    def test_read_gps_many_raises_runtime_error_on_failure(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(1, stderr="bad bulk read"),
        ):
            with self.assertRaisesRegex(RuntimeError, "bad bulk read"):
                wrapper.read_gps_many([Path("/tmp/photo.jpg")])

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

    def test_clear_gps_blanks_gps_tags(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(0),
        ) as run_mock:
            wrapper.clear_gps(Path("/tmp/photo.jpg"))

        command = run_mock.call_args.args[0]
        self.assertIn("-overwrite_original", command)
        self.assertIn("-GPSLatitude=", command)
        self.assertIn("-GPSLongitudeRef=", command)
        self.assertEqual(run_mock.call_args.kwargs["input"], "/tmp/photo.jpg\n")

    def test_runs_use_utf8_and_hidden_console_window(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(0, stdout="[]"),
        ) as run_mock:
            wrapper.read_gps(Path("/tmp/photo.jpg"))

        kwargs = run_mock.call_args.kwargs
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(
            kwargs["creationflags"],
            getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def test_write_gps_raises_runtime_error_on_failure(self) -> None:
        wrapper = ExifToolWrapper()

        with patch(
            "core.exiftool_wrapper.subprocess.run",
            return_value=CompletedProcessStub(1, stderr="bad write"),
        ):
            with self.assertRaisesRegex(RuntimeError, "bad write"):
                wrapper.write_gps(Path("/tmp/photo.jpg"), 40.5, -111.8)


@unittest.skipUnless(ExifToolWrapper().is_available(), "ExifTool is not installed")
class ExifToolWrapperIntegrationTests(unittest.TestCase):
    def test_write_read_clear_round_trip_with_unicode_file_name(self) -> None:
        # Pillow is a desktop dependency; it is only used here to make a JPEG.
        from PIL import Image

        wrapper = ExifToolWrapper()

        with tempfile.TemporaryDirectory() as temp_dir:
            photo = Path(temp_dir) / "Café 東京 #1.jpg"
            Image.new("RGB", (8, 8), "white").save(photo)

            wrapper.write_gps(photo, -33.8568, 151.2153)
            gps = wrapper.read_gps(photo)
            self.assertAlmostEqual(gps["latitude"], -33.8568, places=4)
            self.assertAlmostEqual(gps["longitude"], 151.2153, places=4)

            bulk = wrapper.read_gps_many([photo])
            self.assertAlmostEqual(bulk[photo]["latitude"], -33.8568, places=4)

            wrapper.clear_gps(photo)
            self.assertEqual(
                wrapper.read_gps(photo),
                {"latitude": None, "longitude": None},
            )


if __name__ == "__main__":
    unittest.main()
