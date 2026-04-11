import unittest
from pathlib import Path

from core.models import PhotoInfo
from services.photo_service import (
    refresh_destination_session,
    index_photo_infos,
    load_destination_photo_infos,
    load_source_photo_info,
)


class StubLoader:
    def __init__(self, photo_infos: dict[Path, PhotoInfo]) -> None:
        self.photo_infos = photo_infos
        self.calls: list[Path] = []

    def load_photo_info(self, path: Path) -> PhotoInfo:
        self.calls.append(path)
        return self.photo_infos[path]


class PhotoServiceTests(unittest.TestCase):
    def test_load_destination_photo_infos_preserves_input_order(self) -> None:
        first = Path("/tmp/first.jpg")
        second = Path("/tmp/second.jpg")
        loader = StubLoader(
            {
                first: PhotoInfo(path=first, file_type="JPG"),
                second: PhotoInfo(path=second, file_type="JPG"),
            }
        )

        loaded = load_destination_photo_infos([first, second], loader)

        self.assertEqual([info.path for info in loaded], [first, second])
        self.assertEqual(loader.calls, [first, second])

    def test_index_photo_infos_builds_lookup_by_path(self) -> None:
        first = PhotoInfo(path=Path("/tmp/first.jpg"), file_type="JPG")
        second = PhotoInfo(path=Path("/tmp/second.jpg"), file_type="JPG")

        indexed = index_photo_infos([first, second])

        self.assertEqual(indexed[first.path], first)
        self.assertEqual(indexed[second.path], second)

    def test_load_source_photo_info_delegates_to_loader(self) -> None:
        source = Path("/tmp/source.jpg")
        expected = PhotoInfo(
            path=source,
            file_type="JPG",
            current_latitude=40.5,
            current_longitude=-111.8,
        )
        loader = StubLoader({source: expected})

        loaded = load_source_photo_info(source, loader)

        self.assertEqual(loaded, expected)
        self.assertEqual(loader.calls, [source])

    def test_refresh_destination_session_builds_consistent_state(self) -> None:
        first = Path("/tmp/first.jpg")
        second = Path("/tmp/second.jpg")
        loader = StubLoader(
            {
                first: PhotoInfo(
                    path=first,
                    file_type="JPG",
                    current_latitude=40.5,
                    current_longitude=-111.8,
                ),
                second: PhotoInfo(path=second, file_type="JPG"),
            }
        )

        session = refresh_destination_session([first, second], loader)

        self.assertEqual(session.selected_paths, [first, second])
        self.assertEqual([info.path for info in session.loaded_photos], [first, second])
        self.assertEqual(session.thumbnail_items, [])
        self.assertEqual(session.loaded_photo_infos[first].current_latitude, 40.5)
        self.assertEqual(loader.calls, [first, second])


if __name__ == "__main__":
    unittest.main()
