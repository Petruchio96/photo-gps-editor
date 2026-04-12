import unittest
from pathlib import Path

from core.models import PhotoInfo
from services.target_paths_service import get_overwrite_entries, get_target_paths


class TargetPathsServiceTests(unittest.TestCase):
    def test_get_target_paths_excludes_source_only_when_needed(self) -> None:
        source = Path("/tmp/source.jpg")
        target_paths = [source, Path("/tmp/one.jpg"), Path("/tmp/two.jpg")]

        self.assertEqual(
            get_target_paths(target_paths, True, source),
            [Path("/tmp/one.jpg"), Path("/tmp/two.jpg")],
        )
        self.assertEqual(
            get_target_paths(target_paths, False, source),
            target_paths,
        )
        self.assertEqual(
            get_target_paths(target_paths, True, None),
            target_paths,
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
