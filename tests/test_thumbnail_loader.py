import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

from core.thumbnail_loader import ThumbnailLoader


class ThumbnailLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_load_icon_returns_real_thumbnail_for_jpeg(self) -> None:
        loader = ThumbnailLoader(thumbnail_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "photo.jpg"
            Image.new("RGB", (120, 80), color="red").save(path)

            icon = loader.load_icon(path)

        self.assertFalse(icon.isNull())

    def test_load_icon_falls_back_for_non_jpeg_files(self) -> None:
        loader = ThumbnailLoader(thumbnail_size=64)
        icon = loader.load_icon(Path("/tmp/photo.cr3"))
        self.assertFalse(icon.isNull())

    def test_load_icon_handles_unreadable_jpeg_with_fallback(self) -> None:
        loader = ThumbnailLoader(thumbnail_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.jpg"
            path.write_text("not really an image", encoding="utf-8")

            icon = loader.load_icon(path)

        self.assertFalse(icon.isNull())

    def test_load_icon_with_gps_badge_still_returns_icon(self) -> None:
        loader = ThumbnailLoader(thumbnail_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "photo.jpg"
            Image.new("RGB", (64, 64), color="blue").save(path)

            icon = loader.load_icon(path, has_gps=True)

        self.assertFalse(icon.isNull())


if __name__ == "__main__":
    unittest.main()
