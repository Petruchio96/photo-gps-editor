import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
)

from gui.services.thumbnail_items import build_tooltip_text, reselect_paths


class ThumbnailItemServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_build_tooltip_text_with_gps(self) -> None:
        self.assertEqual(
            build_tooltip_text("photo.jpg", 40.5, -111.8),
            "photo.jpg\nGPS: 40.500000, -111.800000",
        )

    def test_build_tooltip_text_without_gps(self) -> None:
        self.assertEqual(build_tooltip_text("photo.jpg", None, None), "photo.jpg\nNo GPS")

    def test_reselect_paths_restores_matching_items_only(self) -> None:
        widget = QListWidget()
        widget.setSelectionMode(QListWidget.ExtendedSelection)

        for name in ["one.jpg", "two.jpg", "three.jpg"]:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, f"/tmp/{name}")
            widget.addItem(item)

        reselect_paths(widget, [Path("/tmp/one.jpg"), Path("/tmp/three.jpg")])

        selected = [widget.item(index).text() for index in range(widget.count()) if widget.item(index).isSelected()]
        self.assertEqual(selected, ["one.jpg", "three.jpg"])


if __name__ == "__main__":
    unittest.main()
