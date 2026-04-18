"""
Thumbnail loading helpers.

Why this file exists:
    The main window should not need to know the details of opening image files,
    resizing them, and converting them into Qt icons.

    This module keeps that logic in one place so the GUI code stays simpler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QImageReader,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


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

    BADGE_SIZE: Final[int] = 34
    BADGE_CORNER_RADIUS: Final[float] = 8.0
    BADGE_INSET: Final[int] = 2
    BADGE_ICON_NUDGE_X: Final[int] = 1
    BADGE_ICON_NUDGE_Y: Final[int] = -1
    MAX_CACHE_ENTRIES: Final[int] = 512

    def __init__(self, thumbnail_size: int = 128) -> None:
        """
        Store the target thumbnail size in pixels.

        Args:
            thumbnail_size:
                Maximum width and height for generated thumbnails.
        """
        self.thumbnail_size = thumbnail_size
        self._icon_cache: dict[tuple[str, int | None, bool], QIcon] = {}

        # Store the path to the overlay icon used for photos that already have
        # GPS metadata. Keeping this as a project asset makes the badge more
        # consistent and professional than drawing a temporary text marker.
        self.overlay_icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "satellite_overlay_icon_128 (croped).png"
        )
        self._fallback_icon = self._build_fallback_icon()
        self._badge_overlay_pixmap = self._load_trimmed_overlay_pixmap()
        self._gps_fallback_icon = self._build_badged_icon(self._fallback_icon)

    def load_icon(self, path: Path, has_gps: bool = False) -> QIcon:
        """
        Return a QIcon for the given file.

        If the file is a JPG or JPEG, we try to generate a real thumbnail.
        If that fails, or if the file type is something else like CR2/CR3/DNG,
        we return a fallback icon.

        If the file has GPS metadata, we overlay a small badge in the top-right
        corner so the user can identify geotagged photos at a glance.

        Args:
            path:
                Path to the file we want to represent in the UI.
            has_gps:
                True when the file has GPS metadata and should receive a badge.

        Returns:
            A QIcon that can be shown in a QListWidget or similar Qt widget.
        """
        cache_key = self._build_cache_key(path, has_gps)
        cached_icon = self._icon_cache.get(cache_key)

        if cached_icon is not None:
            return cached_icon

        if path.suffix.lower() in {".jpg", ".jpeg"}:
            real_pixmap = self._load_jpeg_thumbnail(path)
            if real_pixmap is not None:
                icon = self._build_badged_icon(QIcon(real_pixmap)) if has_gps else QIcon(real_pixmap)
                self._cache_icon(cache_key, icon)
                return icon

        fallback_icon = self._gps_fallback_icon if has_gps else self._fallback_icon
        self._cache_icon(cache_key, fallback_icon)
        return fallback_icon

    def _cache_icon(self, cache_key: tuple[str, int | None, bool], icon: QIcon) -> None:
        """
        Keep thumbnail caching bounded so long sessions do not grow memory forever.
        """
        if len(self._icon_cache) >= self.MAX_CACHE_ENTRIES:
            self._icon_cache.clear()
        self._icon_cache[cache_key] = icon

    def _build_cache_key(self, path: Path, has_gps: bool) -> tuple[str, int | None, bool]:
        """
        Cache thumbnails by path, timestamp, and GPS badge state.
        """
        try:
            modified_at = path.stat().st_mtime_ns
        except OSError:
            modified_at = None

        return (str(path), modified_at, has_gps)

    def _load_jpeg_thumbnail(self, path: Path) -> QPixmap | None:
        """
        Try to open a JPEG file and convert it into a thumbnail pixmap.

        Args:
            path:
                Path to a JPG/JPEG image.

        Returns:
            A QPixmap if thumbnail generation succeeds, otherwise None.
        """
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)

        size = reader.size()
        if size.isValid():
            scaled_size = QSize(size)
            scaled_size.scale(
                self.thumbnail_size,
                self.thumbnail_size,
                Qt.KeepAspectRatio,
            )
            reader.setScaledSize(scaled_size)

        image = reader.read()
        if image.isNull():
            return None

        pixmap = QPixmap.fromImage(image)
        return None if pixmap.isNull() else pixmap

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

    def _build_badged_icon(self, icon: QIcon) -> QIcon:
        """
        Draw a small GPS badge in the upper-right corner of an existing icon.

        Instead of drawing a text or emoji marker, this version uses a real PNG
        asset from the project so the badge looks the same across systems.

        Args:
            icon:
                The base icon that represents the thumbnail.

        Returns:
            A new QIcon with the GPS badge drawn on top. If the overlay asset
            cannot be loaded, the original icon is returned unchanged.
        """
        base_pixmap = icon.pixmap(self.thumbnail_size, self.thumbnail_size)

        # If Qt fails to render the thumbnail pixmap, return the original icon
        # instead of trying to draw on an invalid surface.
        if base_pixmap.isNull():
            return icon

        overlay = self._badge_overlay_pixmap

        # If the overlay asset is missing or unreadable, fail gracefully and
        # return the original icon without a badge.
        if overlay.isNull():
            return icon

        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Use the actual pixmap dimensions, not the requested thumbnail size.
        # Real thumbnails often preserve aspect ratio, so they may be smaller
        # than the full bounding box in one dimension.
        badge_x = max(0, base_pixmap.width() - self.BADGE_SIZE)
        badge_y = 0

        badge_background_rect = QRectF(
            badge_x,
            badge_y,
            self.BADGE_SIZE,
            self.BADGE_SIZE,
        )
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor("white")))
        painter.drawPath(
            self._top_right_square_badge_path(
                badge_background_rect,
                self.BADGE_CORNER_RADIUS,
            )
        )

        inner_badge_rect = QRectF(
            badge_x + self.BADGE_INSET,
            badge_y + self.BADGE_INSET,
            self.BADGE_SIZE - (self.BADGE_INSET * 2),
            self.BADGE_SIZE - (self.BADGE_INSET * 2),
        )
        overlay = overlay.scaled(
            int(inner_badge_rect.width()),
            int(inner_badge_rect.height()),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        overlay_x = (
            int(inner_badge_rect.x() + ((inner_badge_rect.width() - overlay.width()) / 2))
            + self.BADGE_ICON_NUDGE_X
        )
        overlay_y = (
            int(inner_badge_rect.y() + ((inner_badge_rect.height() - overlay.height()) / 2))
            + self.BADGE_ICON_NUDGE_Y
        )
        painter.drawPixmap(overlay_x, overlay_y, overlay)
        painter.end()

        return QIcon(base_pixmap)

    def _load_trimmed_overlay_pixmap(self) -> QPixmap:
        """
        Load the overlay asset and trim any transparent padding around it.
        """
        try:
            with Image.open(self.overlay_icon_path) as overlay_image:
                overlay_image = overlay_image.convert("RGBA")
                alpha = overlay_image.getchannel("A")
                bounds = alpha.getbbox()

                if bounds is not None:
                    overlay_image = overlay_image.crop(bounds)

                pixmap = QPixmap()
                pixmap.loadFromData(
                    self._rgb_bytes_to_png_bytes(overlay_image),
                    "PNG",
                )
                return pixmap
        except (UnidentifiedImageError, OSError):
            return QPixmap()

    def _top_right_square_badge_path(
        self,
        rect: QRectF,
        radius: float,
    ) -> QPainterPath:
        """
        Return a badge path with a square top-right corner and rounded others.
        """
        left = rect.left()
        top = rect.top()
        right = rect.right()
        bottom = rect.bottom()
        radius = min(radius, rect.width() / 2, rect.height() / 2)

        path = QPainterPath()
        path.moveTo(left + radius, top)
        path.lineTo(right, top)
        path.lineTo(right, bottom - radius)
        path.arcTo(right - (2 * radius), bottom - (2 * radius), 2 * radius, 2 * radius, 0, -90)
        path.lineTo(left + radius, bottom)
        path.arcTo(left, bottom - (2 * radius), 2 * radius, 2 * radius, 270, -90)
        path.lineTo(left, top + radius)
        path.arcTo(left, top, 2 * radius, 2 * radius, 180, -90)
        path.closeSubpath()
        return path

    def _create_fallback_icon(self) -> QIcon:
        return self._fallback_icon

    def _build_fallback_icon(self) -> QIcon:
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
