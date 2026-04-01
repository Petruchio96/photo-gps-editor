import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from core.models import PhotoInfo
from gui.main_window import MainWindow


class FakeExifTool:
    def __init__(self) -> None:
        self.writes: list[tuple[Path, float, float]] = []

    def write_gps(self, path: Path, latitude: float, longitude: float) -> None:
        self.writes.append((path, latitude, longitude))


class FakePhotoLoader:
    def __init__(self, gps_by_path: dict[Path, tuple[float | None, float | None]]) -> None:
        self.gps_by_path = gps_by_path

    def load_photo_info(self, path: Path) -> PhotoInfo:
        latitude, longitude = self.gps_by_path[path]
        return PhotoInfo(
            path=path,
            file_type=path.suffix.upper().lstrip("."),
            current_latitude=latitude,
            current_longitude=longitude,
        )


class FakeThumbnailLoader:
    def load_icon(self, path: Path, has_gps: bool = False) -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.blue if has_gps else Qt.lightGray)
        return QIcon(pixmap)


class MainWindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()
        self.window.show()

        self.paths = [
            Path("/tmp/source.jpg"),
            Path("/tmp/destination-one.jpg"),
            Path("/tmp/destination-two.jpg"),
        ]
        self.gps_by_path = {
            self.paths[0]: (40.486325, -111.813415),
            self.paths[1]: (None, None),
            self.paths[2]: (None, None),
        }

        self.window.exiftool = FakeExifTool()
        self.window.loader = FakePhotoLoader(self.gps_by_path)
        self.window.thumbnail_loader = FakeThumbnailLoader()
        self.window.selected_paths = list(self.paths)
        self.window.populate_list()

    def tearDown(self) -> None:
        self.window.close()

    def _select_index(self, index: int, clear: bool = True) -> None:
        if clear:
            self.window.list_widget.clearSelection()
        item = self.window.list_widget.item(index)
        item.setSelected(True)
        self.window.update_details_panel()

    def test_window_builds_expected_panels(self) -> None:
        self.assertIsNotNone(self.window.list_widget)
        self.assertIsNotNone(self.window.destination_list)
        self.assertIsNotNone(self.window.select_all_button)
        self.assertIsNotNone(self.window.apply_button)

    def test_select_all_and_clear_selection_buttons_work(self) -> None:
        self.window.select_all_photos()
        self.assertEqual(len(self.window.list_widget.selectedItems()), len(self.paths))

        self.window.clear_photo_selection()
        self.assertEqual(len(self.window.list_widget.selectedItems()), 0)

    def test_manual_coordinate_pair_paste_splits_across_both_fields(self) -> None:
        self.window.manual_source_radio.setChecked(True)

        self.window.latitude_input.setText("40.486325, -111.813415")

        self.assertEqual(self.window.latitude_input.text(), "40.486325")
        self.assertEqual(self.window.longitude_input.text(), "-111.813415")

    def test_source_can_remain_selected_without_becoming_destination(self) -> None:
        self._select_index(0)
        self.window.set_selected_photo_as_source()

        self.window.select_all_photos()

        target_paths = self.window._get_destination_paths()

        self.assertEqual(target_paths, self.paths[1:])
        self.assertEqual(self.window.destination_list.count(), 2)
        self.assertTrue(self.window.apply_button.isEnabled())

    def test_apply_skips_locked_source_file(self) -> None:
        self._select_index(0)
        self.window.set_selected_photo_as_source()

        self.window.select_all_photos()
        self.window.apply_coordinates_to_selected()

        self.assertEqual(
            self.window.exiftool.writes,
            [
                (self.paths[1], 40.486325, -111.813415),
                (self.paths[2], 40.486325, -111.813415),
            ],
        )


if __name__ == "__main__":
    unittest.main()
