import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem

from gui.services.selection import (
    can_set_source_from_items,
    get_destination_paths,
    get_overwrite_entries,
)


class SelectionServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

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
        widget = QListWidget()

        first = QListWidgetItem("first")
        first.setData(Qt.UserRole, "/tmp/first.jpg")
        first.setData(Qt.UserRole + 1, 40.5)
        first.setData(Qt.UserRole + 2, -111.8)
        widget.addItem(first)

        second = QListWidgetItem("second")
        second.setData(Qt.UserRole, "/tmp/second.jpg")
        second.setData(Qt.UserRole + 1, None)
        second.setData(Qt.UserRole + 2, None)
        widget.addItem(second)

        entries = get_overwrite_entries(
            widget,
            [Path("/tmp/first.jpg"), Path("/tmp/second.jpg")],
        )

        self.assertEqual(entries, ["first.jpg — 40.500000, -111.800000"])

    def test_can_set_source_requires_one_new_item_with_gps(self) -> None:
        item = QListWidgetItem("photo")
        item.setData(Qt.UserRole, "/tmp/photo.jpg")
        item.setData(Qt.UserRole + 1, 40.5)
        item.setData(Qt.UserRole + 2, -111.8)

        self.assertTrue(can_set_source_from_items([item], None))
        self.assertFalse(can_set_source_from_items([], None))
        self.assertFalse(
            can_set_source_from_items([item], Path("/tmp/photo.jpg"))
        )


if __name__ == "__main__":
    unittest.main()
