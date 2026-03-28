"""
Thumbnail loading helpers.

Why this file exists:
    The main window should not need to know the details of opening image files,
    resizing them, and converting them into Qt icons.

    This module keeps that logic in one place so the GUI code stays simpler.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt


class ThumbnailLoader:
    """
    Create thumbnail icons for files selected in the app.

    Current behavior:
    1. JPG / JPEG files:
       We try to open them with Pillow and build a real thumbnail.
    2. Other supported files:
       We return a simple fallback icon for now.
       Later we can improve RAW preview support.
    """

    def __init__(self, thumbnail_size: int = 128) -> None:
        """
        Store the target thumbnail size in pixels.

        Args:
            thumbnail_size:
                Maximum width and height for generated thumbnails.
        """
        self.thumbnail_size = thumbnail_size

    def load_icon(self, path: Path) -> QIcon:
        """
        Return a QIcon for the given file.

        If the file is a JPG or JPEG, we try to generate a real thumbnail.
        If that fails, or if the file type is something else like CR2/CR3/DNG,
        we return a fallback icon.

        Args:
            path:
                Path to the file we want to represent in the UI.

        Returns:
            A QIcon that can be shown in a QListWidget or similar Qt widget.
        """
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            real_icon = self._load_jpeg_thumbnail(path)
            if real_icon is not None:
                return real_icon

        return self._create_fallback_icon()

    def _load_jpeg_thumbnail(self, path: Path) -> QIcon | None:
        """
        Try to open a JPEG file and convert it into a thumbnail icon.

        Args:
            path:
                Path to a JPG/JPEG image.

        Returns:
            A QIcon if thumbnail generation succeeds, otherwise None.
        """
        try:
            with Image.open(path) as image:
                # Some photos, especially from phones and cameras, store their
                # correct display orientation in EXIF metadata instead of
                # physically rotating the pixel data. exif_transpose applies
                # that orientation so portrait images appear correctly.
                image = ImageOps.exif_transpose(image)

                # Convert to RGB so we avoid issues with unusual source modes.
                image = image.convert("RGB")

                # Pillow modifies the image in place so it fits inside the
                # requested bounding box while keeping the aspect ratio.
                image.thumbnail((self.thumbnail_size, self.thumbnail_size))

                # Build a QPixmap from raw image bytes so Qt can display it.
                width, height = image.size
                raw_data = image.tobytes("raw", "RGB")

                pixmap = QPixmap(width, height)
                pixmap.loadFromData(self._rgb_bytes_to_png_bytes(image), "PNG")

                if pixmap.isNull():
                    return None

                return QIcon(pixmap)

        except (UnidentifiedImageError, OSError):
            return None

    def _rgb_bytes_to_png_bytes(self, image: Image.Image) -> bytes:
        """
        Convert a Pillow image into PNG bytes in memory.

        Why this helper exists:
            Qt can load image bytes directly, and PNG is a convenient format for
            transferring the resized thumbnail from Pillow to QPixmap without
            writing temporary files to disk.

        Args:
            image:
                A Pillow image object.

        Returns:
            PNG-encoded bytes for the image.
        """
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_fallback_icon(self) -> QIcon:
        """
        Create a simple placeholder icon for files that do not have a real
        thumbnail yet.

        For version 1, this is good enough for RAW files and any image that
        fails thumbnail generation.

        Returns:
            A basic square QIcon.
        """
        pixmap = QPixmap(self.thumbnail_size, self.thumbnail_size)
        pixmap.fill(Qt.lightGray)
        return QIcon(pixmap)