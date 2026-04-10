import unittest
from pathlib import Path

from core.photo_loader import PhotoLoader


class FakeExifTool:
    def __init__(self) -> None:
        self.calls: list[Path] = []
        self.response = {"latitude": 40.5, "longitude": -111.8}
        self.error: Exception | None = None

    def read_gps(self, path: Path) -> dict:
        self.calls.append(path)
        if self.error is not None:
            raise self.error
        return self.response


class PhotoLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.exiftool = FakeExifTool()
        self.loader = PhotoLoader(self.exiftool)

    def test_load_photo_info_reads_supported_file(self) -> None:
        path = Path("/tmp/photo.jpg")

        info = self.loader.load_photo_info(path)

        self.assertEqual(info.path, path)
        self.assertEqual(info.file_type, "JPG")
        self.assertEqual(info.current_latitude, 40.5)
        self.assertEqual(info.current_longitude, -111.8)
        self.assertIsNone(info.gps_error)
        self.assertEqual(self.exiftool.calls, [path])

    def test_load_photo_info_keeps_missing_gps_as_none(self) -> None:
        self.exiftool.response = {"latitude": None, "longitude": None}

        info = self.loader.load_photo_info(Path("/tmp/photo.jpeg"))

        self.assertIsNone(info.current_latitude)
        self.assertIsNone(info.current_longitude)
        self.assertIsNone(info.gps_error)

    def test_load_photo_info_rejects_unsupported_file_without_exif_call(self) -> None:
        path = Path("/tmp/photo.png")

        info = self.loader.load_photo_info(path)

        self.assertEqual(info.gps_error, "Unsupported file type.")
        self.assertEqual(self.exiftool.calls, [])

    def test_load_photo_info_captures_exif_errors(self) -> None:
        self.exiftool.error = RuntimeError("ExifTool failed")

        info = self.loader.load_photo_info(Path("/tmp/photo.jpg"))

        self.assertEqual(info.gps_error, "ExifTool failed")
        self.assertIsNone(info.current_latitude)
        self.assertIsNone(info.current_longitude)


if __name__ == "__main__":
    unittest.main()
