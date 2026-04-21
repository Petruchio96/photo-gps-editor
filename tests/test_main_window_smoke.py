import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from core.models import PhotoInfo
from gui.main_window import APP_VERSION, MainWindow
from services.workflow_facade import PhotoWorkflowFacade


class FakeExifTool:
    def __init__(
        self,
        gps_by_path: dict[Path, tuple[float | None, float | None]] | None = None,
    ) -> None:
        self.writes: list[tuple[Path, float, float]] = []
        self.clears: list[Path] = []
        self.failures: dict[Path, Exception] = {}
        self.gps_by_path = gps_by_path if gps_by_path is not None else {}

    def write_gps(self, path: Path, latitude: float, longitude: float) -> None:
        if path in self.failures:
            raise self.failures[path]
        self.writes.append((path, latitude, longitude))
        self.gps_by_path[path] = (latitude, longitude)

    def clear_gps(self, path: Path) -> None:
        self.clears.append(path)
        self.gps_by_path[path] = (None, None)


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
            Path("/tmp/photo-one.jpg"),
            Path("/tmp/photo-two.jpg"),
        ]
        self.gps_by_path = {
            self.source_path: (40.486325, -111.813415),
            self.paths[0]: (None, None),
            self.paths[1]: (None, None),
        }

        self.window.exiftool = FakeExifTool(self.gps_by_path)
        self.window.loader = FakePhotoLoader(self.gps_by_path)
        self.window.workflow = PhotoWorkflowFacade(
            loader=self.window.loader,
            writer=self.window.exiftool,
        )
        self.window.thumbnail_loader = FakeThumbnailLoader()
        self.window.session.selected_paths = list(self.paths)
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
        self.assertIsNotNone(self.window.selected_photos_list)
        self.assertIsNotNone(self.window.select_all_button)
        self.assertIsNotNone(self.window.remove_loaded_photos_button)
        self.assertEqual(self.window.remove_loaded_photos_button.property("tone"), "primary")
        self.assertIsNotNone(self.window.apply_button)
        self.assertIsNotNone(self.window.choose_source_button)
        self.assertEqual(self.window.choose_source_button.text(), "Choose Source Photo")
        self.assertEqual(self.window.choose_source_button.objectName(), "accentButton")
        self.assertEqual(self.window.clear_source_button.property("tone"), "neutral")
        self.assertIsNotNone(self.window.clear_manual_coordinates_button)
        self.assertEqual(
            self.window.clear_manual_coordinates_button.property("tone"),
            "neutral",
        )
        self.assertIsNotNone(self.window.add_selected_button)
        self.assertIsNotNone(self.window.remove_selected_photos_button)
        self.assertIsNotNone(self.window.clear_selected_gps_button)
        self.assertIsNotNone(self.window.about_action)
        self.assertEqual(self.window.remove_photos_action.text(), "Remove Photos")
        self.assertIn(
            self.window.exit_action.shortcuts()[0],
            QKeySequence.keyBindings(QKeySequence.StandardKey.Quit),
        )
        self.assertEqual(self.window.undo_action.text(), "Undo")
        self.assertFalse(self.window.undo_action.isEnabled())
        self.assertIn(
            self.window.undo_action.shortcuts()[0],
            QKeySequence.keyBindings(QKeySequence.StandardKey.Undo),
        )
        self.assertEqual(self.window.redo_action.text(), "Redo")
        self.assertFalse(self.window.redo_action.isEnabled())
        self.assertIn(
            self.window.redo_action.shortcuts()[0],
            QKeySequence.keyBindings(QKeySequence.StandardKey.Redo),
        )
        self.assertEqual(self.window.copy_action.text(), "Copy")
        self.assertEqual(self.window.paste_action.text(), "Paste")
        self.assertEqual(
            self.window.paste_coordinates_button.text(),
            "Paste Coordinates from Clipboard",
        )
        self.assertEqual(self.window.paste_coordinates_button.objectName(), "accentButton")

    def test_initial_status_and_photo_selection_controls_match_new_flow(self) -> None:
        self.assertEqual(
            self.window.select_button.text(),
            "Choose Photos",
        )
        self.assertEqual(self.window.open_action.text(), "Choose Photos...")
        self.assertEqual(self.window.select_button.objectName(), "accentButton")
        self.assertEqual(
            self.window.selected_photos_title_label.text(),
            "Selected Photos to Change GPS Coordinates (0)",
        )
        self.assertEqual(
            self.window.apply_button.text(),
            "Apply New GPS Coordinates to Photos",
        )
        self.assertEqual(self.window.apply_button.objectName(), "applyButton")
        self.assertEqual(self.window.apply_button.property("tone"), "safe")
        self.assertEqual(
            self.window.remove_selected_photos_button.text(),
            "Remove All Photos",
        )
        self.assertEqual(self.window.remove_selected_photos_button.property("tone"), "neutral")
        self.assertEqual(
            self.window.clear_selected_gps_button.text(),
            "Clear Coordinates from Photos",
        )
        self.assertEqual(self.window.clear_selected_gps_button.property("tone"), "neutral")
        self.assertFalse(self.window.add_selected_button.isEnabled())
        self.assertTrue(self.window.remove_loaded_photos_button.isEnabled())
        self.assertEqual(self.window.remove_loaded_photos_button.property("tone"), "primary")
        self.assertEqual(self.window.remove_loaded_photos_button.text(), "Remove All Photos")
        self.assertTrue(self.window.remove_photos_action.isEnabled())
        self.assertFalse(self.window.copy_action.isEnabled())
        self.assertFalse(self.window.remove_selected_photos_button.isEnabled())
        self.assertFalse(self.window.clear_selected_gps_button.isEnabled())
        self.assertEqual(self.window.selected_photos_stack.currentIndex(), 0)

    def test_about_action_opens_versioned_dialog(self) -> None:
        with patch("gui.main_window.QMessageBox.about") as about_dialog:
            self.window.show_about_dialog()

        about_dialog.assert_called_once()
        _, title, text = about_dialog.call_args.args
        self.assertIn(APP_VERSION, title)
        self.assertIn("Photo GPS Editor", text)
        self.assertIn(APP_VERSION, text)
        self.assertIn("https://github.com/Petruchio96/photo-gps-editor", text)

    def test_select_all_and_clear_selection_buttons_work(self) -> None:
        self.window.select_all_photos()
        self.assertEqual(len(self.window.list_widget.selectedItems()), len(self.paths))
        self.assertEqual(
            self.window.remove_loaded_photos_button.text(),
            "Remove All Photos",
        )

        self.window.clear_photo_selection()
        self.assertEqual(len(self.window.list_widget.selectedItems()), 0)
        self.assertEqual(self.window.remove_loaded_photos_button.text(), "Remove All Photos")

    def test_partial_browser_selection_uses_remove_selected_label(self) -> None:
        self._select_index(0)

        self.assertEqual(
            self.window.remove_loaded_photos_button.text(),
            "Remove Selected Photos",
        )

    def test_remove_loaded_photos_button_clears_browser_list_when_nothing_is_selected(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.window.clear_photo_selection()

        self.window.remove_photos_from_browser_list()

        self.assertEqual(self.window.session.selected_paths, [])
        self.assertEqual(self.window.session.target_paths, [])
        self.assertEqual(self.window.list_widget.count(), 0)
        self.assertFalse(self.window.remove_loaded_photos_button.isEnabled())
        self.assertEqual(self.window.remove_loaded_photos_button.property("tone"), "neutral")
        self.assertEqual(self.window.remove_loaded_photos_button.text(), "Remove All Photos")
        self.assertFalse(self.window.remove_photos_action.isEnabled())

    def test_remove_loaded_photos_button_removes_selected_browser_photos_only(self) -> None:
        self._select_index(0)
        self.window.add_selected_photos_to_target_list()
        self._select_index(1)

        self.window.remove_photos_from_browser_list()

        self.assertEqual(self.window.session.selected_paths, [self.paths[0]])
        self.assertEqual(self.window.session.target_paths, [self.paths[0]])

    def test_file_menu_remove_photos_clears_all_browser_photos(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        self.window.remove_photos_action.trigger()

        self.assertEqual(self.window.session.selected_paths, [])
        self.assertEqual(self.window.session.target_paths, [])
        self.assertFalse(self.window.remove_photos_action.isEnabled())

    def test_edit_copy_is_enabled_for_one_selected_photo_with_gps(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()

        self.window.select_browser_paths([self.paths[0]])

        self.assertTrue(self.window.copy_action.isEnabled())

        self.window.copy_action.trigger()

        self.assertEqual(QApplication.clipboard().text(), "41.000000, -112.000000")

    def test_edit_copy_is_disabled_for_multiple_selected_photos(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.gps_by_path[self.paths[1]] = (42.0, -113.0)
        self.window.populate_list()
        self.window.select_all_photos()

        self.assertFalse(self.window.copy_action.isEnabled())

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

    def test_manual_coordinate_pair_paste_supports_spaced_dms(self) -> None:
        self.window.manual_source_radio.setChecked(True)

        self.window.latitude_input.setText('40° 42\' 51" N, 74° 0\' 21" W')

        self.assertEqual(self.window.latitude_input.text(), '40° 42\' 51" N')
        self.assertEqual(self.window.longitude_input.text(), '74° 0\' 21" W')
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

    def test_adding_browser_selection_populates_target_list_and_clears_left_selection(self) -> None:
        self.window.select_all_photos()

        self.assertTrue(self.window.add_selected_button.isEnabled())

        self.window.add_selected_photos_to_target_list()

        self.assertEqual(self.window.session.target_paths, self.paths)
        self.assertEqual(len(self.window.list_widget.selectedItems()), 0)
        self.assertEqual(self.window.selected_photos_list.count(), len(self.paths))
        self.assertEqual(
            self.window.selected_photos_title_label.text(),
            "Selected Photos to Change GPS Coordinates (2)",
        )
        self.assertEqual(self.window.selected_photos_stack.currentIndex(), 1)
        self.assertTrue(self.window.remove_selected_photos_button.isEnabled())
        self.assertEqual(self.window.remove_selected_photos_button.property("tone"), "primary")
        self.assertEqual(self.window.remove_selected_photos_button.text(), "Remove All Photos")
        self.assertFalse(self.window.clear_selected_gps_button.isEnabled())
        self.assertEqual(self.window.clear_selected_gps_button.property("tone"), "neutral")

    def test_selecting_target_list_item_syncs_browser_selection(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        target_item = self.window.selected_photos_list.item(0)
        target_item.setSelected(True)
        self.window.handle_target_list_selection_changed()

        selected_browser_paths = self.window.get_selected_paths()

        self.assertEqual(selected_browser_paths, [self.paths[0]])
        self.assertTrue(self.window.remove_selected_photos_button.isEnabled())
        self.assertEqual(self.window.remove_selected_photos_button.property("tone"), "primary")
        self.assertEqual(
            self.window.remove_selected_photos_button.text(),
            "Remove Selected Photos",
        )

    def test_selecting_all_target_list_items_uses_remove_all_label(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        self.window.selected_photos_list.selectAll()
        self.window.handle_target_list_selection_changed()

        self.assertEqual(
            self.window.remove_selected_photos_button.text(),
            "Remove All Photos",
        )

    def test_target_list_selection_replaces_browser_selection(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        first_item = self.window.selected_photos_list.item(0)
        first_item.setSelected(True)
        self.window.handle_target_list_selection_changed()
        self.assertEqual(self.window.get_selected_paths(), [self.paths[0]])

        self.window.selected_photos_list.clearSelection()
        self.window.handle_target_list_selection_changed()
        second_item = self.window.selected_photos_list.item(1)
        second_item.setSelected(True)
        self.window.handle_target_list_selection_changed()
        self.assertEqual(self.window.get_selected_paths(), [self.paths[1]])

    def test_separate_source_photo_can_drive_selected_photo_list(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        target_paths = self.window._get_target_paths()

        self.assertEqual(target_paths, self.paths)
        self.assertEqual(self.window.selected_photos_list.count(), len(self.paths))
        self.assertTrue(self.window.apply_button.isEnabled())
        self.assertEqual(self.window.source_file_label.text(), "source.jpg")
        self.assertEqual(
            self.window.source_file_label.alignment(),
            Qt.AlignCenter,
        )
        self.assertIn(
            "Source GPS Coordinates: 40.486325, -111.813415",
            self.window.active_source_coordinates.text(),
        )
        self.assertEqual(self.window.apply_button.property("tone"), "safe")
        self.assertEqual(self.window.clear_source_button.property("tone"), "primary")

    def test_apply_button_warns_when_selected_photo_already_has_gps(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.assertEqual(self.window.apply_button.property("tone"), "warning")
        self.assertEqual(self.window.clear_selected_gps_button.property("tone"), "danger")

    def test_apply_uses_separate_source_photo_for_selected_files(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.window.apply_coordinates_to_selected()

        self.assertCountEqual(
            self.window.exiftool.writes,
            [
                (self.paths[0], 40.486325, -111.813415),
                (self.paths[1], 40.486325, -111.813415),
            ],
        )
        self.assertEqual(self.window.session.target_paths, [])
        self.assertEqual(self.window.selected_photos_list.count(), 0)

    def test_undo_and_redo_apply_gps_coordinates(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.window.apply_coordinates_to_selected()

        self.assertTrue(self.window.undo_action.isEnabled())
        self.assertFalse(self.window.redo_action.isEnabled())

        self.window.undo_action.trigger()

        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))
        self.assertEqual(self.gps_by_path[self.paths[1]], (None, None))
        self.assertFalse(self.window.undo_action.isEnabled())
        self.assertTrue(self.window.redo_action.isEnabled())

        self.window.redo_action.trigger()

        self.assertEqual(self.gps_by_path[self.paths[0]], (40.486325, -111.813415))
        self.assertEqual(self.gps_by_path[self.paths[1]], (40.486325, -111.813415))
        self.assertTrue(self.window.undo_action.isEnabled())
        self.assertFalse(self.window.redo_action.isEnabled())

    def test_choose_photos_clears_undo_and_redo_memory(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.window.apply_coordinates_to_selected()
        self.window.undo_gps_edit()

        new_path = Path("/tmp/new-photo.jpg")
        self.gps_by_path[new_path] = (None, None)

        with patch.object(self.window, "_pick_photo_files", return_value=[new_path]):
            self.window.select_photos()

        self.assertFalse(self.window.undo_action.isEnabled())
        self.assertFalse(self.window.redo_action.isEnabled())

    def test_apply_cancels_when_overwrite_confirmation_is_rejected(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        with patch(
            "gui.main_window.QMessageBox.exec",
            return_value=QMessageBox.Cancel,
        ) as dialog_exec:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(dialog_exec.call_count, 1)
        self.assertEqual(self.window.exiftool.writes, [])

    def test_apply_overwrites_when_confirmation_is_accepted(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        with patch(
            "gui.main_window.QMessageBox.exec",
            return_value=QMessageBox.Ok,
        ) as dialog_exec:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(dialog_exec.call_count, 1)
        self.assertCountEqual(
            self.window.exiftool.writes,
            [
                (self.paths[0], 40.486325, -111.813415),
                (self.paths[1], 40.486325, -111.813415),
            ],
        )

    def test_clear_source_photo_resets_preview(self) -> None:
        self.window._load_source_photo(self.source_path)

        self.window.clear_source_photo()

        self.assertIsNone(self.window.session.source_photo_path)
        self.assertEqual(self.window.source_file_label.text(), "No source photo selected")

    def test_source_photo_without_gps_disables_apply(self) -> None:
        no_gps_source = Path("/tmp/source-no-gps.jpg")
        self.gps_by_path[no_gps_source] = (None, None)

        self.window._load_source_photo(no_gps_source)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        self.assertFalse(self.window.apply_button.isEnabled())
    
    def test_invalid_clipboard_paste_does_not_crash(self) -> None:
        QApplication.clipboard().setText("not coordinates")
        self.assertFalse(self.window.paste_coordinates_button.isEnabled())
        self.assertFalse(self.window.paste_action.isEnabled())

        self.window.paste_coordinates_from_clipboard()

    def test_valid_clipboard_paste_sets_manual_source(self) -> None:
        QApplication.clipboard().setText("40.486325, -111.813415")
        self.assertTrue(self.window.paste_coordinates_button.isEnabled())
        self.assertTrue(self.window.paste_action.isEnabled())

        self.window.paste_action.trigger()

        self.assertTrue(self.window.manual_source_radio.isChecked())
        self.assertEqual(self.window.latitude_input.text(), "40.486325")
        self.assertEqual(self.window.longitude_input.text(), "-111.813415")
        self.assertTrue(self.window.clear_manual_coordinates_button.isEnabled())

    def test_paste_button_is_disabled_when_clipboard_is_empty(self) -> None:
        QApplication.clipboard().setText("")

        self.assertFalse(self.window.paste_coordinates_button.isEnabled())
        self.assertFalse(self.window.paste_action.isEnabled())

    def test_clear_manual_coordinates_button_disables_when_fields_are_blank(self) -> None:
        self.window.manual_source_radio.setChecked(True)

        self.assertFalse(self.window.clear_manual_coordinates_button.isEnabled())
        self.assertEqual(
            self.window.clear_manual_coordinates_button.property("tone"),
            "neutral",
        )

        self.window.latitude_input.setText("40.486325")

        self.assertTrue(self.window.clear_manual_coordinates_button.isEnabled())
        self.assertEqual(
            self.window.clear_manual_coordinates_button.property("tone"),
            "primary",
        )

        self.window.clear_manual_coordinates()

        self.assertEqual(self.window.latitude_input.text(), "")
        self.assertEqual(self.window.longitude_input.text(), "")
        self.assertFalse(self.window.clear_manual_coordinates_button.isEnabled())
        self.assertEqual(
            self.window.clear_manual_coordinates_button.property("tone"),
            "neutral",
        )

    def test_apply_requires_photo_selection(self) -> None:
        self.window._load_source_photo(self.source_path)

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [])

    def test_apply_requires_valid_manual_coordinates(self) -> None:
        self.window.manual_source_radio.setChecked(True)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.window.latitude_input.setText("bad")
        self.window.longitude_input.setText("still bad")

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [])

    def test_apply_reports_partial_write_failures(self) -> None:
        self.window._load_source_photo(self.source_path)
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()
        self.window.exiftool.failures[self.paths[1]] = RuntimeError("disk full")

        self.window.apply_coordinates_to_selected()

        self.assertEqual(
            self.window.exiftool.writes,
            [(self.paths[0], 40.486325, -111.813415)],
        )

    def test_remove_selected_photos_button_updates_target_list(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        target_item = self.window.selected_photos_list.item(0)
        target_item.setSelected(True)
        self.window.handle_target_list_selection_changed()
        self.window.remove_selected_photos_from_target_list()

        self.assertEqual(self.window.session.target_paths, [self.paths[1]])
        self.assertEqual(self.window.selected_photos_list.count(), 1)

    def test_remove_selected_photos_button_clears_list_when_nothing_is_selected(self) -> None:
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        self.window.remove_selected_photos_from_target_list()

        self.assertEqual(self.window.session.target_paths, [])
        self.assertEqual(self.window.selected_photos_list.count(), 0)

    def test_clear_coordinates_from_list_updates_loaded_metadata(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self.window.add_selected_photos_to_target_list()

        continue_button = object()
        cancel_button = object()
        with patch(
            "gui.window_mixins.source_editor.QMessageBox.addButton",
            side_effect=[continue_button, cancel_button],
        ), patch(
            "gui.window_mixins.source_editor.QMessageBox.exec",
        ), patch(
            "gui.window_mixins.source_editor.QMessageBox.setDefaultButton",
        ), patch(
            "gui.window_mixins.source_editor.QMessageBox.clickedButton",
            return_value=continue_button,
        ):
            self.window.clear_selected_target_coordinates()

        self.assertEqual(self.window.exiftool.clears, [self.paths[0]])
        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))
        self.assertEqual(self.window.session.target_paths, [])
        self.assertEqual(self.window.selected_photos_list.count(), 0)
        self.assertTrue(self.window.undo_action.isEnabled())

        self.window.undo_action.trigger()

        self.assertEqual(self.gps_by_path[self.paths[0]], (41.0, -112.0))
        self.assertFalse(self.window.undo_action.isEnabled())
        self.assertTrue(self.window.redo_action.isEnabled())

        self.window.redo_action.trigger()

        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))
        self.assertTrue(self.window.undo_action.isEnabled())
        self.assertFalse(self.window.redo_action.isEnabled())


if __name__ == "__main__":
    unittest.main()
