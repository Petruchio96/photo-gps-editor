import unittest
import tempfile
from pathlib import Path

from core.models import PhotoInfo
from services.photo_metadata_cache import PhotoMetadataCache
from services.photo_service import (
    index_photo_infos,
    load_source_photo_info,
    load_selected_photo_infos,
    refresh_photo_session,
)


class StubLoader:
    def __init__(self, photo_infos: dict[Path, PhotoInfo]) -> None:
        self.photo_infos = photo_infos
        self.calls: list[Path] = []

    def load_photo_info(self, path: Path) -> PhotoInfo:
        self.calls.append(path)
        return self.photo_infos[path]


class BulkStubLoader(StubLoader):
    def __init__(self, photo_infos: dict[Path, PhotoInfo]) -> None:
        super().__init__(photo_infos)
        self.bulk_calls: list[list[Path]] = []

    def load_photo_infos(self, paths: list[Path]) -> list[PhotoInfo]:
        self.bulk_calls.append(paths)
        return [self.photo_infos[path] for path in paths]


class PhotoServiceTests(unittest.TestCase):
    def test_load_selected_photo_infos_preserves_input_order(self) -> None:
        first = Path("/tmp/first.jpg")
        second = Path("/tmp/second.jpg")
        loader = StubLoader(
            {
                first: PhotoInfo(path=first, file_type="JPG"),
                second: PhotoInfo(path=second, file_type="JPG"),
            }
        )

        loaded = load_selected_photo_infos([first, second], loader)

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

    def test_refresh_photo_session_builds_consistent_state(self) -> None:
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

        session = refresh_photo_session([first, second], loader)

        self.assertEqual(session.selected_paths, [first, second])
        self.assertEqual([info.path for info in session.loaded_photos], [first, second])
        self.assertEqual(session.thumbnail_items, [])
        self.assertEqual(session.loaded_photo_infos[first].current_latitude, 40.5)
        self.assertEqual(loader.calls, [first, second])

    def test_load_selected_photo_infos_reuses_cached_unchanged_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "photo.jpg"
            path.write_text("original", encoding="utf-8")
            loader = StubLoader(
                {
                    path: PhotoInfo(
                        path=path,
                        file_type="JPG",
                        current_latitude=40.5,
                        current_longitude=-111.8,
                    ),
                }
            )
            cache = PhotoMetadataCache()

            first_load = load_selected_photo_infos([path], loader, cache)
            second_load = load_selected_photo_infos([path], loader, cache)

        self.assertEqual(first_load[0].current_latitude, 40.5)
        self.assertEqual(second_load[0].current_latitude, 40.5)
        self.assertEqual(loader.calls, [path])

    def test_load_selected_photo_infos_reloads_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "photo.jpg"
            path.write_text("original", encoding="utf-8")
            loader = StubLoader(
                {
                    path: PhotoInfo(
                        path=path,
                        file_type="JPG",
                        current_latitude=40.5,
                        current_longitude=-111.8,
                    ),
                }
            )
            cache = PhotoMetadataCache()

            first_load = load_selected_photo_infos([path], loader, cache)
            path.write_text("changed content", encoding="utf-8")
            loader.photo_infos[path] = PhotoInfo(
                path=path,
                file_type="JPG",
                current_latitude=41.0,
                current_longitude=-112.0,
            )
            second_load = load_selected_photo_infos([path], loader, cache)

        self.assertEqual(first_load[0].current_latitude, 40.5)
        self.assertEqual(second_load[0].current_latitude, 41.0)
        self.assertEqual(loader.calls, [path, path])

    def test_metadata_cache_supports_multi_file_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.jpg"
            second = Path(temp_dir) / "second.jpg"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            cache = PhotoMetadataCache()
            expected_infos = [
                PhotoInfo(path=first, file_type="JPG", current_latitude=40.5),
                PhotoInfo(path=second, file_type="JPG", current_longitude=-111.8),
            ]

            cache.set_many(expected_infos)
            cached_infos = cache.get_many([first, second])

        self.assertEqual(cached_infos[first].current_latitude, 40.5)
        self.assertEqual(cached_infos[second].current_longitude, -111.8)

    def test_load_selected_photo_infos_bulk_loads_cache_misses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cached_path = Path(temp_dir) / "cached.jpg"
            first_miss = Path(temp_dir) / "first-miss.jpg"
            second_miss = Path(temp_dir) / "second-miss.jpg"
            cached_path.write_text("cached", encoding="utf-8")
            first_miss.write_text("first", encoding="utf-8")
            second_miss.write_text("second", encoding="utf-8")
            cache = PhotoMetadataCache()
            cache.set(
                PhotoInfo(
                    path=cached_path,
                    file_type="JPG",
                    current_latitude=40.5,
                )
            )
            loader = BulkStubLoader(
                {
                    first_miss: PhotoInfo(
                        path=first_miss,
                        file_type="JPG",
                        current_latitude=41.0,
                    ),
                    second_miss: PhotoInfo(
                        path=second_miss,
                        file_type="JPG",
                        current_latitude=42.0,
                    ),
                }
            )

            loaded = load_selected_photo_infos(
                [cached_path, first_miss, second_miss],
                loader,
                cache,
            )

        self.assertEqual([info.path for info in loaded], [cached_path, first_miss, second_miss])
        self.assertEqual(loader.bulk_calls, [[first_miss, second_miss]])
        self.assertEqual(loader.calls, [])


if __name__ == "__main__":
    unittest.main()
