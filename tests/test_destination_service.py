import unittest
from pathlib import Path

from core.models import PhotoInfo
from services.destination_service import get_destination_paths, get_overwrite_entries


class DestinationServiceTests(unittest.TestCase):
    def test_get_destination_paths_excludes_source_only_when_needed(self) -> None:
        source = Path("/tmp/source.jpg")
        destinations = [source, Path("/tmp/one.jpg"), Path("/tmp/two.jpg")]

        self.assertEqual(
            get_destination_paths(destinations, True, source),
            [Path("/tmp/one.jpg"), Path("/tmp/two.jpg")],
        )
        self.assertEqual(
            get_destination_paths(destinations, False, source),
            destinations,
        )
        self.assertEqual(
            get_destination_paths(destinations, True, None),
            destinations,
        )

    def test_get_overwrite_entries_formats_only_target_items_with_gps(self) -> None:
        first_path = Path("/tmp/first.jpg")
        second_path = Path("/tmp/second.jpg")
        photo_info_by_path = {
            first_path: PhotoInfo(
                path=first_path,
                file_type="JPG",
                current_latitude=40.5,
                current_longitude=-111.8,
            ),
            second_path: PhotoInfo(
                path=second_path,
                file_type="JPG",
            ),
        }

        entries = get_overwrite_entries(
            photo_info_by_path,
            [first_path, second_path],
        )

        self.assertEqual(
            [entry.display_text() for entry in entries],
            ["first.jpg — 40.500000, -111.800000"],
        )


if __name__ == "__main__":
    unittest.main()
