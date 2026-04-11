import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem

from gui.presenters.selection import can_set_source_from_items


class SelectionServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

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
