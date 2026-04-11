import unittest
from pathlib import Path

from core.models import PhotoInfo
from services.source_service import (
    resolve_active_source,
    resolve_manual_source,
    resolve_photo_source,
)


class SourceServiceTests(unittest.TestCase):
    def test_resolve_photo_source_returns_coordinates_when_photo_has_gps(self) -> None:
        info = PhotoInfo(
            path=Path("/tmp/source.jpg"),
            file_type="JPG",
            current_latitude=40.5,
            current_longitude=-111.8,
        )

        resolution = resolve_photo_source(info)

        self.assertIsNotNone(resolution.coordinates)
        self.assertEqual(resolution.coordinates.latitude, 40.5)
        self.assertEqual(resolution.coordinates.longitude, -111.8)
        self.assertIsNone(resolution.error_message)

    def test_resolve_photo_source_returns_error_when_missing_gps(self) -> None:
        info = PhotoInfo(path=Path("/tmp/source.jpg"), file_type="JPG")

        resolution = resolve_photo_source(info)

        self.assertIsNone(resolution.coordinates)
        self.assertEqual(
            resolution.error_message,
            "Choose a source photo with GPS coordinates before applying.",
        )

    def test_resolve_manual_source_parses_valid_coordinate_text(self) -> None:
        resolution = resolve_manual_source("40.486325", "-111.813415")

        self.assertIsNotNone(resolution.coordinates)
        self.assertEqual(resolution.coordinates.latitude, 40.486325)
        self.assertEqual(resolution.coordinates.longitude, -111.813415)

    def test_resolve_active_source_uses_selected_mode(self) -> None:
        info = PhotoInfo(
            path=Path("/tmp/source.jpg"),
            file_type="JPG",
            current_latitude=40.5,
            current_longitude=-111.8,
        )

        photo_resolution = resolve_active_source(
            using_photo_source=True,
            source_photo_info=info,
            latitude_text="",
            longitude_text="",
        )
        manual_resolution = resolve_active_source(
            using_photo_source=False,
            source_photo_info=None,
            latitude_text="41.0",
            longitude_text="-112.0",
        )

        self.assertEqual(photo_resolution.coordinates.latitude, 40.5)
        self.assertEqual(manual_resolution.coordinates.latitude, 41.0)


if __name__ == "__main__":
    unittest.main()
