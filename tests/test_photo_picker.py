import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QTreeWidgetItem

from core.models import PhotoInfo
from core.places import Place
from gui.background import BackgroundRunner
from gui.widgets.photo_picker import HAS_GPS_ROLE, PATH_ROLE, PhotoPickerDialog
from gui.widgets.thumbnail_delegate import IN_LIST_ROLE, SHIMMER_ROLE
from services.models import WorkflowSession


class FakeWorkflow:
    """Reads GPS from a dict instead of the files."""

    def __init__(self, gps_paths: set[Path]) -> None:
        self.gps_paths = gps_paths

    def refresh_photo_workflow(self, session: WorkflowSession) -> WorkflowSession:
        infos = {}
        for path in session.selected_paths:
            has_gps = path in self.gps_paths
            infos[path] = PhotoInfo(
                path=path,
                file_type="JPG",
                current_latitude=40.0 if has_gps else None,
                current_longitude=-111.0 if has_gps else None,
            )
        session.loaded_photo_infos = infos
        return session


class FakeThumbnailLoader:
    def __init__(self) -> None:
        self.loaded: list[Path] = []

    def cached_icon(self, path: Path, has_gps: bool = False):
        return None

    def load_images(self, paths: list[Path]) -> dict:
        self.loaded.extend(paths)
        return {path: None for path in paths}

    def icon_from_image(self, path: Path, has_gps: bool, image) -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.blue if has_gps else Qt.lightGray)
        return QIcon(pixmap)


class PhotoPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.trip = self.root / "Trip"
        self.year = self.trip / "2019"
        self.year.mkdir(parents=True)
        for name in ("a.jpg", "b.jpg", "c.jpg", "notes.txt"):
            (self.trip / name).write_bytes(b"")
        (self.year / "d.jpg").write_bytes(b"")
        self.other = self.root / "Other"
        self.other.mkdir()

        self.thumbnails = FakeThumbnailLoader()
        self.background = BackgroundRunner()
        self.background.run_inline = True

    def _open(self, start: Path, in_list: set[Path] = frozenset(), single: bool = False) -> PhotoPickerDialog:
        dialog = PhotoPickerDialog(
            None,
            title="Add Photos",
            start_folder=start,
            in_list=set(in_list),
            workflow=FakeWorkflow({self.trip / "b.jpg"}),
            thumbnail_loader=self.thumbnails,
            background=self.background,
            place_sections=[
                ("My Computer", [Place("Home", self.root)]),
                ("Bookmarks", [Place("My Trip", self.trip), Place("Other", self.other)]),
            ],
            single=single,
        )
        self.addCleanup(dialog.close)
        dialog.show()
        return dialog

    def _grid_names(self, dialog: PhotoPickerDialog) -> list[str]:
        return [dialog.grid.item(row).text() for row in range(dialog.grid.count())]

    def _click(self, dialog: PhotoPickerDialog, name: str, modifier=Qt.NoModifier) -> None:
        item = next(
            dialog.grid.item(row)
            for row in range(dialog.grid.count())
            if dialog.grid.item(row).text() == name
        )
        QTest.mouseClick(
            dialog.grid.viewport(),
            Qt.LeftButton,
            modifier,
            dialog.grid.visualItemRect(item).center(),
        )

    def _tree_item(self, dialog: PhotoPickerDialog, name: str):
        return dialog.tree.findItems(name, Qt.MatchExactly | Qt.MatchRecursive)[0]

    def test_shows_only_the_folders_photos(self) -> None:
        dialog = self._open(self.trip)

        # No folders, no other files.
        self.assertEqual(self._grid_names(dialog), ["a.jpg", "b.jpg", "c.jpg"])
        self.assertEqual(dialog.folder_summary_label.text(), "3 photos")
        self.assertEqual(dialog.path_box.text(), str(self.trip))
        self.assertEqual(self.thumbnails.loaded, [self.trip / "a.jpg", self.trip / "b.jpg", self.trip / "c.jpg"])

    def test_photos_already_in_the_list_cannot_be_selected(self) -> None:
        dialog = self._open(self.trip, in_list={self.trip / "a.jpg"})
        item = dialog.grid.item(0)

        self.assertTrue(item.data(IN_LIST_ROLE))
        self.assertEqual(dialog.folder_summary_label.text(), "3 photos · 1 already in the Photo List")

        self._click(dialog, "a.jpg")
        dialog.select_all_button.click()

        self.assertFalse(item.isSelected())
        self.assertEqual(dialog.selected_paths(), [self.trip / "b.jpg", self.trip / "c.jpg"])

    def test_clicking_photos_selects_them_and_updates_add(self) -> None:
        dialog = self._open(self.trip)
        self.assertFalse(dialog.add_button.isEnabled())
        self.assertFalse(dialog.selection_bar.property("active"))

        self._click(dialog, "a.jpg")
        self._click(dialog, "c.jpg", Qt.ShiftModifier)

        self.assertEqual(dialog.selected_paths(), [self.trip / name for name in ("a.jpg", "b.jpg", "c.jpg")])
        self.assertEqual(dialog.add_button.text(), "Add 3 Photos to Photo List")
        self.assertTrue(dialog.selection_bar.property("active"))

        self._click(dialog, "b.jpg")
        self.assertEqual(dialog.add_button.text(), "Add 2 Photos to Photo List")

        dialog.deselect_all_button.click()
        self.assertEqual(dialog.selected_paths(), [])
        self.assertFalse(dialog.add_button.isEnabled())

    def test_tree_shows_places_and_highlights_the_folder(self) -> None:
        dialog = self._open(self.trip)

        sections = [dialog.tree.topLevelItem(index).text(0) for index in range(dialog.tree.topLevelItemCount())]
        self.assertEqual(sections, ["My Computer", "Bookmarks"])
        # The closest place holding the folder is highlighted.
        self.assertEqual(dialog.tree.currentItem().text(0), "My Trip")

    def test_clicking_a_folder_in_the_tree_opens_it(self) -> None:
        dialog = self._open(self.trip)
        other = self._tree_item(dialog, "Other")

        dialog.tree.itemClicked.emit(other, 0)

        self.assertEqual(dialog.current_folder, self.other)
        self.assertEqual(self._grid_names(dialog), [])
        self.assertIn("No photos in this folder", dialog.empty_label.text())

    def test_expanding_a_folder_lists_its_subfolders(self) -> None:
        dialog = self._open(self.other)
        trip = self._tree_item(dialog, "My Trip")

        trip.setExpanded(True)

        self.assertEqual([trip.child(index).text(0) for index in range(trip.childCount())], ["2019"])

    def test_only_folders_with_subfolders_get_an_expand_arrow(self) -> None:
        dialog = self._open(self.other)
        trip = self._tree_item(dialog, "My Trip")
        other = self._tree_item(dialog, "Other")

        self.assertEqual(trip.childIndicatorPolicy(), QTreeWidgetItem.ShowIndicator)
        self.assertEqual(other.childIndicatorPolicy(), QTreeWidgetItem.DontShowIndicator)

        trip.setExpanded(True)
        year = trip.child(0)
        self.assertEqual(year.childIndicatorPolicy(), QTreeWidgetItem.DontShowIndicator)

    def test_opening_a_nested_folder_opens_the_tree_down_to_it(self) -> None:
        dialog = self._open(self.year)

        current = dialog.tree.currentItem()
        self.assertEqual(current.text(0), "2019")
        self.assertEqual(current.data(0, PATH_ROLE), str(self.year))
        self.assertEqual(self._grid_names(dialog), ["d.jpg"])

    def test_path_box_opens_a_typed_folder(self) -> None:
        dialog = self._open(self.trip)

        dialog.path_box.setText(str(self.year))
        dialog.path_box.returnPressed.emit()
        self.assertEqual(dialog.current_folder, self.year)

        dialog.path_box.setText(str(self.root / "missing"))
        dialog.path_box.returnPressed.emit()
        self.assertEqual(dialog.current_folder, self.year)
        self.assertTrue(dialog.path_box.property("error"))

    def test_enter_in_the_path_box_does_not_add_photos(self) -> None:
        dialog = self._open(self.trip)
        self._click(dialog, "a.jpg")

        dialog.path_box.setText(str(self.year))
        QTest.keyClick(dialog.path_box, Qt.Key_Return)

        self.assertTrue(dialog.isVisible())
        self.assertEqual(dialog.current_folder, self.year)

    def test_back_forward_and_up(self) -> None:
        dialog = self._open(self.trip)
        self.assertFalse(dialog.back_button.isEnabled())

        dialog.open_folder(self.year)
        dialog.back_button.click()
        self.assertEqual(dialog.current_folder, self.trip)

        dialog.forward_button.click()
        self.assertEqual(dialog.current_folder, self.year)

        dialog.up_button.click()
        self.assertEqual(dialog.current_folder, self.trip)

    def test_late_results_after_changing_folders_are_ignored(self) -> None:
        dialog = self._open(self.trip)
        generation = dialog._generation
        dialog.open_folder(self.year)

        # A thumbnail batch from the folder shown before arrives late.
        dialog._apply_thumbnails((generation, {self.trip / "a.jpg": None}))

        self.assertEqual(self._grid_names(dialog), ["d.jpg"])

    def test_photos_show_as_placeholders_before_their_thumbnails(self) -> None:
        background = self.background
        background.run_inline = False
        self.addCleanup(background.shutdown)
        dialog = self._open(self.trip)

        # Wait only for the folder listing; thumbnails are still on their way.
        for _ in range(100):
            QApplication.processEvents()
            if dialog.grid.count():
                break
            QTest.qWait(10)
        self.assertEqual(self._grid_names(dialog), ["a.jpg", "b.jpg", "c.jpg"])

        for _ in range(200):
            QApplication.processEvents()
            if not any(dialog.grid.item(row).data(SHIMMER_ROLE) for row in range(dialog.grid.count())):
                break
            QTest.qWait(10)
        self.assertFalse(dialog.grid.item(0).data(SHIMMER_ROLE))
        # GPS badges arrive in a second pass after the thumbnails: wait for
        # it too (a slow machine may not have it yet).
        for _ in range(200):
            QApplication.processEvents()
            if dialog.grid.item(1).data(HAS_GPS_ROLE):
                break
            QTest.qWait(10)
        self.assertTrue(dialog.grid.item(1).data(HAS_GPS_ROLE))
        self.assertFalse(dialog.grid.item(0).data(HAS_GPS_ROLE))

    def test_one_photo_mode_chooses_a_single_photo(self) -> None:
        dialog = self._open(self.trip, in_list={self.trip / "a.jpg"}, single=True)
        self.assertFalse(dialog.select_all_button.isVisibleTo(dialog))
        # Photos in the Photo List can still be used as a location.
        self.assertFalse(dialog.grid.item(0).data(IN_LIST_ROLE))

        self._click(dialog, "a.jpg")
        self._click(dialog, "c.jpg", Qt.ShiftModifier)

        self.assertEqual(dialog.selected_paths(), [self.trip / "c.jpg"])
        self.assertEqual(dialog.add_button.text(), "Use This Photo's Location")

    def test_double_click_chooses_the_photo_in_one_photo_mode(self) -> None:
        dialog = self._open(self.trip, single=True)
        item = dialog.grid.item(1)
        point = dialog.grid.visualItemRect(item).center()

        QTest.mouseDClick(dialog.grid.viewport(), Qt.LeftButton, Qt.NoModifier, point)

        self.assertEqual(dialog.result(), PhotoPickerDialog.Accepted)
        self.assertEqual(dialog.selected_paths(), [self.trip / "b.jpg"])

    def test_every_button_has_a_hover_hint(self) -> None:
        dialog = self._open(self.trip)

        missing = [button.text() for button in dialog.findChildren(QPushButton) if not button.toolTip()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
