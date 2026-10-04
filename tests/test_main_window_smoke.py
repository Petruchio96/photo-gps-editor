import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QMessageBox

from core.models import PhotoInfo
from gui.main_window import APP_VERSION, MainWindow
from gui.window_mixins.photo_list import THUMBNAIL_PATH_ROLE
from gui.widgets.thumbnail_delegate import PICK_DISABLED_ROLE, SOURCE_ROLE
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
        if path in self.failures:
            raise self.failures[path]
        self.clears.append(path)
        self.gps_by_path[path] = (None, None)


class FakePhotoLoader:
    def __init__(self, gps_by_path: dict[Path, tuple[float | None, float | None]]) -> None:
        self.gps_by_path = gps_by_path
        self.calls: list[Path] = []

    def load_photo_info(self, path: Path) -> PhotoInfo:
        self.calls.append(path)
        latitude, longitude = self.gps_by_path[path]
        return PhotoInfo(
            path=path,
            file_type=path.suffix.upper().lstrip("."),
            current_latitude=latitude,
            current_longitude=longitude,
        )


class FakeThumbnailLoader:
    def cached_icon(self, path: Path, has_gps: bool = False):
        return None

    def load_images(self, paths: list[Path]) -> dict:
        return {path: None for path in paths}

    def icon_from_image(self, path: Path, has_gps: bool, image) -> QIcon:
        return self.load_icon(path, has_gps)

    def fallback_icon_for(self, has_gps: bool) -> QIcon:
        return self.load_icon(Path("fallback"), has_gps)

    def load_icon(self, path: Path, has_gps: bool = False) -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.blue if has_gps else Qt.lightGray)
        return QIcon(pixmap)


class MainWindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        # Use a throwaway settings file so tests never read or change the
        # user's real preferences.
        settings_dir = tempfile.TemporaryDirectory()
        self.addCleanup(settings_dir.cleanup)
        self.settings_path = Path(settings_dir.name) / "settings.ini"
        self.settings = QSettings(str(self.settings_path), QSettings.IniFormat)

        self.window = MainWindow(settings=self.settings)
        # Run background loading immediately, so these tests can check results
        # right after each action. Background behavior is tested separately.
        self.window.background.run_inline = True
        self.window.show()

        self.source_path = Path("/tmp/source.jpg")
        self.paths = [
            Path("/tmp/photo-one.jpg"),
            Path("/tmp/photo-two.jpg"),
        ]
        self.location = (40.486325, -111.813415)
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

    def _photo_items(self) -> list:
        # Group headings sit between photos in the grid; skip them.
        list_widget = self.window.list_widget
        return [
            list_widget.item(row)
            for row in range(list_widget.count())
            if list_widget.item(row).data(THUMBNAIL_PATH_ROLE) is not None
        ]

    def _visible_paths(self) -> list[Path]:
        return [
            Path(item.data(THUMBNAIL_PATH_ROLE))
            for item in self._photo_items()
            if not item.isHidden()
        ]

    def _select_index(self, index: int, clear: bool = True) -> None:
        """Select the index-th photo in the grid (headings not counted)."""
        if clear:
            self.window.list_widget.clearSelection()
        item = self._photo_items()[index]
        item.setSelected(True)
        self.window.update_details_panel()

    def _select_paths(self, paths: list[Path]) -> None:
        self.window.select_browser_paths(paths)

    def _set_location(self, latitude: float, longitude: float) -> None:
        self.window.set_location_fields(str(latitude), str(longitude))

    def _new_location(self):
        location = self.window._build_inspector_state().new_location
        return None if location is None else (location.latitude, location.longitude)

    def _assert_coordinates_almost_equal(self, actual, expected) -> None:
        self.assertAlmostEqual(actual[0], expected[0], places=12)
        self.assertAlmostEqual(actual[1], expected[1], places=12)

    # --- Layout and menus -------------------------------------------------

    def test_window_builds_expected_panels(self) -> None:
        self.assertEqual(self.window.select_button.text(), "Choose Photos")
        self.assertEqual(self.window.select_button.property("tone"), "primary")
        self.assertEqual(self.window.open_action.text(), "Choose Photos...")
        self.assertEqual(self.window.remove_photos_action.text(), "Remove Photos")
        # Apply is the only orange (main action) button; Remove GPS has its own
        # destructive style.
        self.assertEqual(self.window.apply_button.objectName(), "accentButton")
        self.assertEqual(self.window.remove_gps_button.objectName(), "removeGpsButton")
        self.assertNotEqual(self.window.select_button.objectName(), "accentButton")
        self.assertNotEqual(self.window.paste_coordinates_button.objectName(), "accentButton")
        self.assertEqual(self.window.paste_coordinates_button.text(), "Paste")
        self.assertEqual(self.window.location_from_photo_button.text(), "Browse Photos")
        self.assertEqual(self.window.pick_location_button.text(), "Copy from Photo on Left")
        self.assertEqual(self.window.clear_location_button.text(), "Clear")
        # The platform decides the Quit shortcut: Ctrl+Q on most Linux
        # desktops, Cmd+Q on macOS, and none on Windows (Alt+F4 is built in).
        self.assertEqual(
            self.window.exit_action.shortcuts(),
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
        self.assertEqual(self.window.copy_action.text(), "Copy GPS Coordinates")
        self.assertEqual(self.window.paste_action.text(), "Paste Coordinates")
        self.assertEqual(self.window.select_all_action.text(), "Select All Photos")

    def test_initial_inspector_with_nothing_selected(self) -> None:
        self.assertEqual(self.window.selection_title_label.text(), "No Photos Selected")
        self.assertFalse(self.window.apply_button.isEnabled())
        self.assertEqual(self.window.apply_button.text(), "Apply to Selected Photos")
        self.assertEqual(
            self.window.apply_hint_label.text(),
            "Select the photos to update in the grid.",
        )
        self.assertFalse(self.window.remove_gps_button.isEnabled())
        self.assertTrue(self.window.copy_location_button.isHidden())
        self.assertTrue(self.window.source_card.isHidden())
        self.assertTrue(self.window.pick_banner.isHidden())
        self.assertIn("2 photos loaded", self.window.browser_hint.text())

    def test_about_action_opens_versioned_dialog(self) -> None:
        with patch("gui.main_window.QMessageBox.exec") as exec_mock:
            self.window.show_about_dialog()

        exec_mock.assert_called_once()

    def test_about_dialog_uses_clickable_external_repository_link(self) -> None:
        about_dialog = self.window._build_about_dialog()
        # macOS hides message box titles, so Qt reports an empty title there.
        if sys.platform != "darwin":
            self.assertIn(APP_VERSION, about_dialog.windowTitle())
        self.assertFalse(about_dialog.iconPixmap().isNull())
        link_label = about_dialog.findChild(QLabel, "aboutRepositoryLink")
        self.assertIsNotNone(link_label)
        self.assertIn(APP_VERSION, link_label.text())
        self.assertEqual(link_label.textFormat(), Qt.RichText)
        self.assertEqual(link_label.textInteractionFlags(), Qt.TextBrowserInteraction)
        self.assertTrue(link_label.openExternalLinks())
        self.assertGreaterEqual(link_label.minimumWidth(), 360)
        self.assertGreaterEqual(about_dialog.minimumWidth(), 520)
        self.assertIn("Photo GPS Editor", link_label.text())
        self.assertIn(APP_VERSION, link_label.text())
        self.assertIn(
            '<a href="https://github.com/Petruchio96/photo-gps-editor">',
            link_label.text(),
        )

    # --- Selecting and removing photos -----------------------------------

    def test_select_all_and_clear_selection_buttons_work(self) -> None:
        self.window.select_all_photos()
        self.assertEqual(self.window.get_selected_paths(), self.paths)
        self.assertEqual(self.window.selection_title_label.text(), "2 Photos Selected")
        self.assertEqual(self.window.remove_loaded_photos_button.text(), "Remove All from List")

        self.window.clear_photo_selection()
        self.assertEqual(self.window.get_selected_paths(), [])
        self.assertEqual(self.window.selection_title_label.text(), "No Photos Selected")

    def test_partial_selection_uses_remove_selected_label(self) -> None:
        self._select_index(0)

        self.assertEqual(
            self.window.remove_loaded_photos_button.text(),
            "Remove Selected from List",
        )

    def test_remove_from_list_removes_all_when_nothing_is_selected(self) -> None:
        self.window.remove_photos_from_browser_list()

        self.assertEqual(self.window.session.selected_paths, [])
        self.assertEqual(self.window.list_widget.count(), 0)
        self.assertFalse(self.window.remove_loaded_photos_button.isEnabled())
        self.assertFalse(self.window.remove_photos_action.isEnabled())
        self.assertIn("Choose Photos", self.window.list_widget.empty_message)

    def test_remove_from_list_removes_selected_photos_only(self) -> None:
        self._select_index(1)

        self.window.remove_photos_from_browser_list()

        self.assertEqual(self.window.session.selected_paths, [self.paths[0]])

    def test_file_menu_remove_photos_clears_all_photos(self) -> None:
        self.window.remove_photos_action.trigger()

        self.assertEqual(self.window.session.selected_paths, [])
        self.assertFalse(self.window.remove_photos_action.isEnabled())

    # --- Show filter --------------------------------------------------------

    def test_show_filter_hides_photos_headings_and_counts(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self.assertEqual(self.window.grid_filter_buttons["all"].text(), "All (2)")
        self.assertEqual(self.window.grid_filter_buttons["needs"].text(), "Needs GPS (1)")
        self.assertEqual(self.window.grid_filter_buttons["has"].text(), "Has GPS (1)")

        self.window.set_grid_filter("needs")
        self.assertEqual(self._visible_paths(), [self.paths[0]])
        self.assertEqual(self._visible_headings(), ["Photos without GPS Coordinates (1)"])

        self.window.set_grid_filter("has")
        self.assertEqual(self._visible_paths(), [self.paths[1]])
        self.assertEqual(self._visible_headings(), ["Photos with GPS Coordinates (1)"])

        self.window.set_grid_filter("all")
        self.assertEqual(self._visible_paths(), self.paths)

    def test_select_all_only_selects_photos_shown(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.set_grid_filter("needs")

        self.window.select_all_photos()

        self.assertEqual(self.window.get_selected_paths(), [self.paths[0]])

    def test_hidden_photos_are_never_acted_on(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        # Ctrl+A in the grid selects everything, including hidden items.
        self.window.set_grid_filter("needs")
        self.window.list_widget.selectAll()

        self.assertEqual(self.window.get_selected_paths(), [self.paths[0]])

    def test_filter_shows_message_when_nothing_matches(self) -> None:
        self.window.set_grid_filter("has")

        self.assertEqual(self._visible_paths(), [])
        self.assertEqual(self.window.list_widget.empty_message, "None of these photos have GPS yet.")

        self.window.set_grid_filter("all")
        self.assertEqual(self.window.list_widget.empty_message, "")

    # --- Inspector ------------------------------------------------------------

    def test_single_photo_with_gps_offers_copy(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()

        self._select_paths([self.paths[0]])

        self.assertEqual(self.window.selection_title_label.text(), "photo-one.jpg")
        self.assertEqual(self.window.selection_gps_label.text(), "Current GPS: 41.000000, -112.000000")
        self.assertFalse(self.window.copy_location_button.isHidden())
        self.assertTrue(self.window.copy_location_button.isEnabled())
        self.assertTrue(self.window.copy_action.isEnabled())

        self.window.copy_location_button.click()
        self.assertEqual(QApplication.clipboard().text(), "41.000000, -112.000000")
        # Selecting a photo never fills New Location by itself.
        self.assertIsNone(self._new_location())

    def test_single_photo_without_gps_cannot_copy(self) -> None:
        self._select_paths([self.paths[0]])

        self.assertEqual(self.window.selection_gps_label.text(), "Current GPS: none")
        self.assertFalse(self.window.copy_location_button.isEnabled())
        self.assertFalse(self.window.copy_action.isEnabled())

    def test_multiple_selection_summarizes_gps(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()

        self.window.select_all_photos()

        self.assertEqual(self.window.selection_title_label.text(), "2 Photos Selected")
        self.assertEqual(self.window.selection_gps_label.text(), "Current GPS: 1 of 2 have GPS")
        self.assertTrue(self.window.copy_location_button.isHidden())
        self.assertFalse(self.window.copy_action.isEnabled())
        self.assertEqual(self.window.remove_gps_button.text(), "Remove GPS from 1 Photo")
        self.assertTrue(self.window.remove_gps_button.isEnabled())

    def test_apply_button_label_hint_and_overwrite_warning(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self.assertFalse(self.window.apply_button.isEnabled())
        self.assertIn("Set a new location", self.window.apply_hint_label.text())

        self._set_location(*self.location)

        self.assertTrue(self.window.apply_button.isEnabled())
        self.assertEqual(self.window.apply_button.text(), "Apply to 2 Photos")
        self.assertEqual(
            self.window.apply_hint_label.text(),
            "1 photo already has GPS, which will be replaced.",
        )
        self.assertEqual(self.window.apply_hint_label.property("tone"), "warning")

    # --- Location source: Copy from Photo on Left, right-click, card ------

    def _item_for(self, path: Path):
        return self.window._grid_items_by_path[str(path)]

    def _click_item(self, path: Path, button=Qt.LeftButton) -> None:
        grid = self.window.list_widget
        center = grid.visualItemRect(self._item_for(path)).center()
        QTest.mouseClick(grid.viewport(), button, Qt.NoModifier, center)

    def test_pick_from_grid_sets_source_without_changing_selection(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self._select_paths([self.paths[0]])

        self.window.pick_location_button.click()
        self.assertTrue(self.window.is_picking_location)
        self.assertFalse(self.window.pick_banner.isHidden())

        self._click_item(self.paths[1])

        self.assertFalse(self.window.is_picking_location)
        self.assertTrue(self.window.pick_banner.isHidden())
        self.assertEqual(self._new_location(), (41.0, -112.0))
        self.assertEqual(self.window.get_selected_paths(), [self.paths[0]])
        self.assertFalse(self.window.source_card.isHidden())
        self.assertEqual(self.window.source_card_title.text(), "From photo-two.jpg")
        self.assertTrue(self._item_for(self.paths[1]).data(SOURCE_ROLE))
        self.assertFalse(self._item_for(self.paths[0]).data(SOURCE_ROLE))

    def test_pick_mode_dims_photos_without_gps_and_ignores_clicks_on_them(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()

        self.window.pick_location_button.click()

        self.assertEqual(self.window.pick_location_button.text(), "Cancel")
        self.assertTrue(self._item_for(self.paths[0]).data(PICK_DISABLED_ROLE))
        self.assertFalse(self._item_for(self.paths[1]).data(PICK_DISABLED_ROLE))

        self._click_item(self.paths[0])

        self.assertTrue(self.window.is_picking_location)
        self.assertIsNone(self._new_location())
        self.assertEqual(self.window.get_selected_paths(), [])

    def test_pick_mode_locks_everything_but_the_allowed_controls(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self._select_paths([self.paths[0]])
        self._set_location(*self.location)
        QApplication.clipboard().setText("40.1, -111.2")

        self.window.start_picking_location()

        window = self.window
        for widget in (
            window.select_all_button,
            window.clear_selection_button,
            window.grid_filter_buttons["needs"],
            window.latitude_input,
            window.longitude_input,
            window.paste_coordinates_button,
            window.location_from_photo_button,
            window.clear_location_button,
            window.apply_button,
            window.remove_gps_button,
        ):
            self.assertFalse(widget.isEnabled(), widget)
        for action in (window.select_all_action, window.paste_action, window.undo_action):
            self.assertFalse(action.isEnabled())
        for widget in (
            window.grid_filter_buttons["all"],
            window.grid_filter_buttons["has"],
            window.select_button,
            window.remove_loaded_photos_button,
            window.pick_location_button,
        ):
            self.assertTrue(widget.isEnabled(), widget)

        # The lock survives things that recompute button states.
        window.update_details_panel()
        QApplication.clipboard().setText("41.5, -112.5")
        self.assertFalse(window.apply_button.isEnabled())
        self.assertFalse(window.paste_coordinates_button.isEnabled())

        window.pick_location_button.click()  # Cancel

        self.assertFalse(window.is_picking_location)
        self.assertTrue(window.apply_button.isEnabled())
        self.assertTrue(window.select_all_button.isEnabled())
        for widget in (
            window.latitude_input,
            window.longitude_input,
            window.location_from_photo_button,
            window.source_card_clear,
            window.grid_filter_buttons["needs"],
            window.clear_location_button,
            window.clear_selection_button,
        ):
            self.assertTrue(widget.isEnabled(), widget)
        self.assertFalse(self._item_for(self.paths[0]).data(PICK_DISABLED_ROLE))

    def test_starting_pick_mode_switches_needs_gps_filter_to_all(self) -> None:
        self.window.set_grid_filter("needs")

        self.window.start_picking_location()

        self.assertEqual(self.window._grid_filter, "all")
        self.assertTrue(self.window.grid_filter_buttons["all"].isChecked())

    def test_choose_photos_and_remove_from_list_work_while_picking(self) -> None:
        self.window.start_picking_location()
        new_path = Path("/tmp/new-photo.jpg")
        self.gps_by_path[new_path] = (None, None)

        with patch.object(self.window, "_pick_photo_files", return_value=[new_path]):
            self.window.select_button.click()

        self.assertEqual(self.window.session.selected_paths, [new_path])
        self.assertTrue(self.window.is_picking_location)
        self.assertTrue(self._item_for(new_path).data(PICK_DISABLED_ROLE))
        self.assertFalse(self.window.apply_button.isEnabled())

        self.window.remove_loaded_photos_button.click()

        self.assertEqual(self.window.session.selected_paths, [])
        self.assertTrue(self.window.is_picking_location)

    def test_escape_and_cancel_stop_picking(self) -> None:
        self.window.start_picking_location()
        # Window shortcuts only reach the active window.
        self.window.activateWindow()
        QTest.qWaitForWindowActive(self.window)
        self.window.list_widget.setFocus()
        QTest.keyClick(self.window.list_widget, Qt.Key_Escape)
        self.assertFalse(self.window.is_picking_location)

        self.window.pick_location_button.click()
        self.assertEqual(self.window.pick_location_button.text(), "Cancel")
        self.window.pick_location_button.click()
        self.assertFalse(self.window.is_picking_location)
        self.assertFalse(self.window.pick_location_button.isChecked())
        self.assertEqual(self.window.pick_location_button.text(), "Copy from Photo on Left")

    def test_right_click_does_not_change_selection(self) -> None:
        self._select_paths([self.paths[0]])

        with patch.object(self.window, "show_context_menu"):
            self._click_item(self.paths[1], Qt.RightButton)

        self.assertEqual(self.window.get_selected_paths(), [self.paths[0]])

    def test_context_menu_use_this_location_sets_source(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()

        self.assertTrue(self.window.use_location_from_path(self.paths[1]))

        self.assertEqual(self._new_location(), (41.0, -112.0))
        self.assertTrue(self._item_for(self.paths[1]).data(SOURCE_ROLE))
        self.assertFalse(self.window.use_location_from_path(self.paths[0]))

    def test_editing_fields_by_hand_drops_the_source(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.use_location_from_path(self.paths[1])

        self.window.latitude_input.setText("41.5")

        self.assertTrue(self.window.source_card.isHidden())
        self.assertFalse(self._item_for(self.paths[1]).data(SOURCE_ROLE))

    def test_source_card_clear_button_empties_location(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.use_location_from_path(self.paths[1])

        self.window.source_card_clear.click()

        self.assertIsNone(self._new_location())
        self.assertTrue(self.window.source_card.isHidden())

    def test_source_marker_survives_applying(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.use_location_from_path(self.paths[1])
        self._select_paths([self.paths[0]])

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [(self.paths[0], 41.0, -112.0)])
        self.assertTrue(self._item_for(self.paths[1]).data(SOURCE_ROLE))

    def test_grid_tiles_cannot_be_dragged_around(self) -> None:
        self.assertEqual(self.window.list_widget.movement(), QListWidget.Static)
        self.assertFalse(self.window.list_widget.dragEnabled())

    # --- New location fields ----------------------------------------------

    def test_coordinate_pair_typed_in_one_field_splits_across_both(self) -> None:
        self.window.latitude_input.setText("40.486325, -111.813415")

        self.assertEqual(self.window.latitude_input.text(), "40.486325")
        self.assertEqual(self.window.longitude_input.text(), "-111.813415")

    def test_coordinate_pair_supports_dms(self) -> None:
        self.window.latitude_input.setText('40°42\'51"N, 74°00\'21"W')

        self.assertEqual(self.window.latitude_input.text(), '40°42\'51"N')
        self.assertEqual(self.window.longitude_input.text(), '74°00\'21"W')
        self._assert_coordinates_almost_equal(
            self._new_location(),
            (40.714166666666664, -74.00583333333333),
        )

    def test_coordinate_pair_supports_spaced_dms(self) -> None:
        self.window.latitude_input.setText('40° 42\' 51" N, 74° 0\' 21" W')

        self.assertEqual(self.window.latitude_input.text(), '40° 42\' 51" N')
        self._assert_coordinates_almost_equal(
            self._new_location(),
            (40.714166666666664, -74.00583333333333),
        )

    def test_coordinate_pair_supports_decimal_minutes(self) -> None:
        self.window.latitude_input.setText("40°42.850'N, 74°00.360'W")

        self._assert_coordinates_almost_equal(self._new_location(), (40.714166666666664, -74.006))

    def test_paste_button_fills_fields_from_clipboard(self) -> None:
        QApplication.clipboard().setText("40.486325, -111.813415")
        self.assertTrue(self.window.paste_coordinates_button.isEnabled())

        self.window.paste_coordinates_button.click()

        self.assertEqual(self._new_location(), self.location)

    def test_paste_button_is_disabled_without_coordinates_on_clipboard(self) -> None:
        QApplication.clipboard().setText("not coordinates")

        self.assertFalse(self.window.paste_coordinates_button.isEnabled())
        self.assertFalse(self.window.paste_action.isEnabled())

    def test_invalid_clipboard_paste_shows_message(self) -> None:
        QApplication.clipboard().setText("not coordinates")

        self.window.paste_coordinates_from_clipboard()

        self.assertIsNone(self._new_location())
        self.assertIn("doesn't contain coordinates", self.window.browser_hint.text())

    def test_clear_button_empties_fields(self) -> None:
        self._set_location(*self.location)
        self.assertTrue(self.window.clear_location_button.isEnabled())

        self.window.clear_location_button.click()

        self.assertEqual(self.window.latitude_input.text(), "")
        self.assertEqual(self.window.longitude_input.text(), "")
        self.assertFalse(self.window.clear_location_button.isEnabled())

    def test_location_from_a_photo_file(self) -> None:
        with patch.object(self.window, "_pick_photo_file", return_value=self.source_path):
            self.window.location_from_photo_button.click()

        self.assertEqual(self._new_location(), self.location)
        self.assertIn("source.jpg", self.window.browser_hint.text())
        self.assertEqual(self.window.source_card_title.text(), "From source.jpg")

    def test_location_from_a_photo_without_gps_explains(self) -> None:
        with patch.object(self.window, "_pick_photo_file", return_value=self.paths[0]):
            self.window.choose_location_from_photo()

        self.assertIsNone(self._new_location())
        self.assertIn("has no GPS", self.window.browser_hint.text())

    def test_invalid_location_explains_and_blocks_apply(self) -> None:
        self.window.select_all_photos()
        self.window.set_location_fields("95", "-111")

        self.assertFalse(self.window.apply_button.isEnabled())
        self.assertIn("isn't valid", self.window.apply_hint_label.text())
        self.assertEqual(self.window.apply_hint_label.property("tone"), "error")

    # --- Apply --------------------------------------------------------------

    def test_apply_writes_location_to_selected_photos_and_reports(self) -> None:
        self.window.select_all_photos()
        self._set_location(*self.location)

        self.window.apply_coordinates_to_selected()

        self.assertCountEqual(
            self.window.exiftool.writes,
            [(path, *self.location) for path in self.paths],
        )
        hint = self.window.browser_hint.text()
        self.assertIn("Applied GPS to 2 photos.", hint)
        self.assertIn('href="undo"', hint)
        self.assertEqual(self.window.browser_hint.property("tone"), "success")
        # The same photos stay selected after the grid is redrawn.
        self.assertEqual(self.window.get_selected_paths(), self.paths)

    def test_apply_only_touches_selected_photos(self) -> None:
        self._select_paths([self.paths[1]])
        self._set_location(*self.location)

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [(self.paths[1], *self.location)])

    def test_apply_requires_photo_selection(self) -> None:
        self._set_location(*self.location)

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [])
        self.assertIn("Select the photos to update", self.window.browser_hint.text())

    def test_apply_requires_valid_coordinates(self) -> None:
        self.window.select_all_photos()
        self.window.set_location_fields("north", "west")

        self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [])

    def test_apply_cancels_when_overwrite_confirmation_is_rejected(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self._set_location(*self.location)

        with patch(
            "gui.window_mixins.apply_workflow.QMessageBox.exec",
            return_value=QMessageBox.Cancel,
        ) as dialog_exec:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(dialog_exec.call_count, 1)
        self.assertEqual(self.window.exiftool.writes, [])
        self.assertIn("Nothing was changed", self.window.browser_hint.text())

    def test_apply_overwrites_when_confirmation_is_accepted(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self._set_location(*self.location)

        with patch(
            "gui.window_mixins.apply_workflow.QMessageBox.exec",
            return_value=QMessageBox.Ok,
        ) as dialog_exec:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(dialog_exec.call_count, 1)
        self.assertCountEqual(
            self.window.exiftool.writes,
            [(path, *self.location) for path in self.paths],
        )

    def test_apply_reports_partial_write_failures(self) -> None:
        self.window.select_all_photos()
        self._set_location(*self.location)
        self.window.exiftool.failures[self.paths[1]] = RuntimeError("disk full")

        with patch.object(self.window, "_report_write_failures") as report_mock:
            self.window.apply_coordinates_to_selected()

        self.assertEqual(self.window.exiftool.writes, [(self.paths[0], *self.location)])
        report_mock.assert_called_once_with("apply GPS to", ["photo-two.jpg: disk full"])
        # Only the file that changed can be undone.
        self.assertEqual(self.window.gps_history.undo_states(), {self.paths[0]: (None, None)})

    def test_write_failure_dialog_lists_each_file(self) -> None:
        with patch("gui.main_window.QMessageBox.exec") as exec_mock, patch(
            "gui.main_window.QMessageBox.setDetailedText"
        ) as details_mock:
            self.window._report_write_failures("apply GPS to", ["a.jpg: locked"])

        exec_mock.assert_called_once()
        details_mock.assert_called_once_with("a.jpg: locked")

    def test_no_failure_dialog_when_everything_succeeds(self) -> None:
        with patch("gui.main_window.QMessageBox.exec") as exec_mock:
            self.window._report_write_failures("apply GPS to", [])

        exec_mock.assert_not_called()

    # --- Undo / redo ------------------------------------------------------

    def test_undo_and_redo_apply(self) -> None:
        self.window.select_all_photos()
        self._set_location(*self.location)
        self.window.apply_coordinates_to_selected()
        self.assertTrue(self.window.undo_action.isEnabled())
        self.assertFalse(self.window.redo_action.isEnabled())

        self.window.undo_action.trigger()

        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))
        self.assertEqual(self.gps_by_path[self.paths[1]], (None, None))
        self.assertFalse(self.window.undo_action.isEnabled())
        self.assertTrue(self.window.redo_action.isEnabled())

        self.window.redo_action.trigger()

        self.assertEqual(self.gps_by_path[self.paths[0]], self.location)
        self.assertEqual(self.gps_by_path[self.paths[1]], self.location)

    def test_undo_link_in_status_row_undoes_apply(self) -> None:
        self.window.select_all_photos()
        self._set_location(*self.location)
        self.window.apply_coordinates_to_selected()

        self.window.browser_hint.linkActivated.emit("undo")

        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))
        self.assertTrue(self.window.redo_action.isEnabled())
        self.assertNotIn('href="undo"', self.window.browser_hint.text())

    def test_status_message_gives_way_to_photo_counts(self) -> None:
        self.window._set_status_message("Something happened.", "success")
        self.assertIn("Something happened.", self.window.browser_hint.text())

        self.window._clear_status_message()

        self.assertIn("2 photos loaded", self.window.browser_hint.text())
        self.assertEqual(self.window.browser_hint.property("tone"), "info")

    def test_choose_photos_clears_undo_and_redo_memory(self) -> None:
        self.window.select_all_photos()
        self._set_location(*self.location)
        self.window.apply_coordinates_to_selected()
        self.window.undo_gps_edit()

        new_path = Path("/tmp/new-photo.jpg")
        self.gps_by_path[new_path] = (None, None)
        with patch.object(self.window, "_pick_photo_files", return_value=[new_path]):
            self.window.select_photos()

        self.assertFalse(self.window.undo_action.isEnabled())
        self.assertFalse(self.window.redo_action.isEnabled())

    def test_undo_reports_files_that_could_not_be_restored(self) -> None:
        self.window.select_all_photos()
        self._set_location(*self.location)
        self.window.apply_coordinates_to_selected()
        self.window.exiftool.failures[self.paths[0]] = RuntimeError("read-only")

        with patch.object(self.window, "_report_write_failures") as report_mock:
            self.window.undo_action.trigger()

        report_mock.assert_called_once_with(
            "undo the GPS change for",
            ["photo-one.jpg: read-only"],
        )
        # The other file was still restored.
        self.assertEqual(self.gps_by_path[self.paths[1]], (None, None))
        self.assertTrue(self.window.redo_action.isEnabled())

    # --- Remove GPS -------------------------------------------------------

    def _confirm_remove_gps(self, answer=QMessageBox.Ok) -> None:
        with patch("gui.window_mixins.apply_workflow.QMessageBox.exec", return_value=answer):
            self.window.remove_gps_from_selected()

    def test_remove_gps_clears_selected_photos_after_confirming(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self.window.loader.calls.clear()

        self._confirm_remove_gps()

        self.assertEqual(self.window.exiftool.clears, [self.paths[0]])
        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))
        self.assertEqual(self.window.loader.calls, self.paths)
        self.assertIn("Removed GPS from 1 photo.", self.window.browser_hint.text())
        self.assertTrue(self.window.undo_action.isEnabled())

        self.window.undo_action.trigger()
        self.assertEqual(self.gps_by_path[self.paths[0]], (41.0, -112.0))

        self.window.redo_action.trigger()
        self.assertEqual(self.gps_by_path[self.paths[0]], (None, None))

    def test_remove_gps_does_nothing_when_cancelled(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.window.populate_list()
        self.window.select_all_photos()

        self._confirm_remove_gps(QMessageBox.Cancel)

        self.assertEqual(self.window.exiftool.clears, [])

    def test_remove_gps_continues_past_a_failed_file(self) -> None:
        self.gps_by_path[self.paths[0]] = (41.0, -112.0)
        self.gps_by_path[self.paths[1]] = (42.0, -113.0)
        self.window.populate_list()
        self.window.select_all_photos()
        self.window.exiftool.failures[self.paths[0]] = RuntimeError("locked")

        with patch.object(self.window, "_report_write_failures") as report_mock:
            self._confirm_remove_gps()

        self.assertEqual(self.window.exiftool.clears, [self.paths[1]])
        self.assertEqual(self.gps_by_path[self.paths[0]], (41.0, -112.0))
        report_mock.assert_called_once_with("remove GPS from", ["photo-one.jpg: locked"])
        self.assertEqual(self.window.gps_history.undo_states(), {self.paths[1]: (42.0, -113.0)})

    def _group_headings(self, *, visible_only: bool = False) -> list[str]:
        list_widget = self.window.list_widget
        headings = []
        for row in range(list_widget.count()):
            item = list_widget.item(row)
            widget = list_widget.itemWidget(item)
            if widget is not None and not (visible_only and item.isHidden()):
                headings.append(widget.findChild(QLabel, "thumbnailGroupHeader").text())
        return headings

    def _visible_headings(self) -> list[str]:
        return self._group_headings(visible_only=True)

    def test_grid_has_heading_for_each_gps_group(self) -> None:
        self.gps_by_path[self.paths[1]] = (41.0, -112.0)
        self.window.populate_list()

        self.assertEqual(
            self._group_headings(),
            [
                "Photos without GPS Coordinates (1)",
                "Photos with GPS Coordinates (1)",
            ],
        )

    def test_no_heading_for_an_empty_group(self) -> None:
        self.assertEqual(self._group_headings(), ["Photos without GPS Coordinates (2)"])

    def test_keep_backups_option_is_saved_and_applied(self) -> None:
        self.assertFalse(self.window.keep_backups_action.isChecked())

        self.window.keep_backups_action.setChecked(True)

        self.assertTrue(self.window.workflow.writer.keep_backups)
        self.assertTrue(self.settings.value("keep_backup_copies", type=bool))

        reopened = MainWindow(settings=QSettings(str(self.settings_path), QSettings.IniFormat))
        self.addCleanup(reopened.close)
        self.assertTrue(reopened.keep_backups_action.isChecked())
        self.assertTrue(reopened.workflow.writer.keep_backups)



if __name__ == "__main__":
    unittest.main()
