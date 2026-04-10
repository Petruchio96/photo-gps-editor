import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from core.models import PhotoInfo
from gui.main_window import MainWindow


class FakeExifTool:
    def __init__(self) -> None:
        self.writes: list[tuple[Path, float, float]] = []
        self.failures: dict[Path, Exception] = {}

    def write_gps(self, path: Path, latitude: float, longitude: float) -> None:
        if path in self.failures:
            raise self.failures[path]
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

        self.source_path = Path("/tmp/source.jpg")
        self.paths = [
            Path("/tmp/destination-one.jpg"),
            Path("/tmp/destination-two.jpg"),
        ]
        self.gps_by_path = {
            self.source_path: (40.486325, -111.813415),
            self.paths[0]: (None, None),
            self.paths[1]: (None, None),
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

    def _assert_coordinates_almost_equal(
        self,
        actual: tuple[float, float],
        expected: tuple[float, float],
    ) -> None:
        self.assertAlmostEqual(actual[0], expected[0], places=12)
        self.assertAlmostEqual(actual[1], expected[1], places=12)

    def test_window_builds_expected_panels(self) -> None:
        self.assertIsNotNone(self.window.list_widget)
        self.assertIsNotNone(self.window.destination_list)
        self.assertIsNotNone(self.window.select_all_button)
        self.assertIsNotNone(self.window.apply_button)
        self.assertIsNotNone(self.window.choose_source_button)
        self.assertIsNotNone(self.window.status_message)

    def test_initial_status_and_destination_controls_match_new_flow(self) -> None:
        self.assertEqual(self.window.select_button.text(), "Select Photos")
        self.assertEqual(
            self.window.status_message.text(),
            "Choose a source and select destination photos.",
        )
        self.assertEqual(self.window.loaded_count_badge.text(), "2 loaded")
        self.assertEqual(self.window.selection_count_badge.text(), "No selection")

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

    def test_manual_coordinate_pair_paste_supports_dms(self) -> None:
        self.window.manual_source_radio.setChecked(True)

        self.window.latitude_input.setText('40°42\'51"N, 74°00\'21"W')

        self.assertEqual(self.window.latitude_input.text(), '40°42\'51"N')
        self.assertEqual(self.window.longitude_input.text(), '74°00\'21"W')
        self._assert_coordinates_almost_equal(
            self.window._get_manual_coordinates(),
            (40.714166666666664, -74.00583333333333),
        )

    def test_manual_coordinate_pair_paste_supports_decimal_minutes(self) -> None:
        self.window.manual_source_radio.setChecked(True)

        self.window.latitude_input.setText("40°42.850'N, 74°00.360'W")

        self.assertEqual(self.window.latitude_input.text(), "40°42.850'N")
        self.assertEqual(self.window.longitude_input.text(), "74°00.360'W")
        self._assert_coordinates_almost_equal(
            self.window._get_manual_coordinates(),
            (40.714166666666664, -74.006),
        )

    def test_separate_source_photo_can_drive_destination_selection(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()

        target_paths = self.window._get_destination_paths()

        self.assertEqual(target_paths, self.paths)
        self.assertEqual(self.window.destination_list.count(), len(self.paths))
        self.assertTrue(self.window.apply_button.isEnabled())
        self.assertEqual(self.window.source_file_label.text(), "source.jpg")
        self.assertIn("40.486325", self.window.source_gps_label.text())

    def test_apply_uses_separate_source_photo_for_destinations(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.apply_coordinates_to_selected()

        self.assertEqual(
            self.window.exiftool.writes,
            [
                (self.paths[0], 40.486325, -111.813415),
                (self.paths[1], 40.486325, -111.813415),
            ],
        )
        self.assertEqual(
            self.window.status_message.text(),
            "Updated GPS on 2 destination file(s).",
        )

    def test_apply_cancels_when_overwrite_confirmation_is_rejected(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()

        with patch(
            "gui.main_window.QMessageBox.exec",
            return_value=QMessageBox.Cancel,
        ) as dialog_exec:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(dialog_exec.call_count, 1)
        self.assertEqual(self.window.exiftool.writes, [])
        self.assertIn("cancelled", self.window.status_message.text().lower())

    def test_apply_overwrites_when_confirmation_is_accepted(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()

        with patch(
            "gui.main_window.QMessageBox.exec",
            return_value=QMessageBox.Ok,
        ) as dialog_exec:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(dialog_exec.call_count, 1)
        self.assertEqual(
            self.window.exiftool.writes,
            [
                (self.paths[0], 40.486325, -111.813415),
                (self.paths[1], 40.486325, -111.813415),
            ],
        )

    def test_clear_source_photo_resets_preview(self) -> None:
        self.window._load_source_photo(self.source_path)

        self.window.clear_source_photo()

        self.assertIsNone(self.window.source_photo_path)
        self.assertEqual(self.window.source_file_label.text(), "No source photo selected")
        self.assertEqual(self.window.source_gps_label.text(), "Source GPS: Not loaded")

    def test_source_photo_without_gps_disables_apply(self) -> None:
        no_gps_source = Path("/tmp/source-no-gps.jpg")
        self.gps_by_path[no_gps_source] = (None, None)

        self.window._load_source_photo(no_gps_source)
        self.window.select_all_photos()

        self.assertFalse(self.window.apply_button.isEnabled())
        self.assertIn("does not contain GPS", self.window.status_message.text())

    def test_invalid_clipboard_paste_sets_error_status_without_crashing(self) -> None:
        QApplication.clipboard().setText("not coordinates")

        self.window.paste_coordinates_from_clipboard()

        self.assertIn("could not be parsed", self.window.status_message.text())

    def test_valid_clipboard_paste_sets_manual_source_and_status(self) -> None:
        QApplication.clipboard().setText("40.486325, -111.813415")

        self.window.paste_coordinates_from_clipboard()

        self.assertTrue(self.window.manual_source_radio.isChecked())
        self.assertEqual(self.window.latitude_input.text(), "40.486325")
        self.assertEqual(self.window.longitude_input.text(), "-111.813415")
        self.assertIn("pasted", self.window.status_message.text().lower())

    def test_apply_requires_destination_selection(self) -> None:
        self.window._load_source_photo(self.source_path)

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [])
        self.assertIn("select one or more destination", self.window.status_message.text().lower())

    def test_apply_requires_valid_manual_coordinates(self) -> None:
        self.window.manual_source_radio.setChecked(True)
        self.window.select_all_photos()
        self.window.latitude_input.setText("bad")
        self.window.longitude_input.setText("still bad")

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [])
        self.assertIn("enter valid latitude and longitude", self.window.status_message.text().lower())

    def test_apply_reports_partial_write_failures(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.exiftool.failures[self.paths[1]] = RuntimeError("disk full")

        self.window.apply_coordinates_to_selected()

        self.assertEqual(
            self.window.exiftool.writes,
            [(self.paths[0], 40.486325, -111.813415)],
        )
        self.assertIn("Failed", self.window.status_message.text())
        self.assertIn("destination-two.jpg: disk full", self.window.status_message.text())


if __name__ == "__main__":
    unittest.main()
