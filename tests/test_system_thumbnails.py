import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from gui import system_thumbnails


class SystemThumbnailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name) / "thumbnails"
        self.photo = Path(temp_dir.name) / "Abi & Andrew" / "DSC 01.jpg"
        self.photo.parent.mkdir()
        self.photo.write_bytes(b"photo")

    def _image(self, width: int, height: int) -> QImage:
        image = QImage(width, height, QImage.Format_RGB32)
        image.fill(0x336699)
        return image

    def test_uri_and_name_match_the_file_manager(self) -> None:
        # Spaces are escaped; "&" is left as is, as GLib does.
        uri = system_thumbnails.file_uri(Path("/mnt/photos/Abi & Andrew/DSC 01.jpg"))
        self.assertEqual(uri, "file:///mnt/photos/Abi%20&%20Andrew/DSC%2001.jpg")
        self.assertRegex(system_thumbnails.thumbnail_name(Path("/a.jpg")), r"^[0-9a-f]{32}\.png$")

    def test_written_thumbnail_is_read_back_with_its_labels(self) -> None:
        system_thumbnails.write(self.photo, self._image(300, 200), root=self.root)

        saved = self.root / "normal" / system_thumbnails.thumbnail_name(self.photo)
        labels = system_thumbnails.png_text(saved)
        self.assertEqual(labels["Thumb::URI"], system_thumbnails.file_uri(self.photo))
        self.assertEqual(labels["Thumb::MTime"], str(int(self.photo.stat().st_mtime)))
        image = system_thumbnails.read(self.photo, 64, root=self.root)
        # Scaled to fit 64 x 64, keeping its shape.
        self.assertEqual(image.width(), 64)
        self.assertLess(image.height(), 64)

    def test_out_of_date_thumbnail_is_ignored(self) -> None:
        system_thumbnails.write(self.photo, self._image(40, 40), root=self.root)
        modified = self.photo.stat().st_mtime + 10
        os.utime(self.photo, (modified, modified))

        self.assertIsNone(system_thumbnails.read(self.photo, 64, root=self.root))

    def test_missing_thumbnail_reads_nothing(self) -> None:
        self.assertIsNone(system_thumbnails.read(self.photo, 64, root=self.root))


if __name__ == "__main__":
    unittest.main()
