"""
Thumbnail loading helpers.

Why this file exists:
    The main window should not need to know the details of opening image files,
    resizing them, and converting them into Qt icons.

    This module keeps that logic in one place so the GUI code stays simpler.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QBuffer, QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QImage,
    QImageReader,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)

from core.file_types import JPEG_EXTENSIONS, is_raw_file
from gui import system_thumbnails
from core.models import EmbeddedPreview
from core.runtime_paths import resource_path

# Reads embedded RAW previews: list of paths -> {path: EmbeddedPreview}.
type PreviewReader = Callable[[list[Path]], dict[Path, EmbeddedPreview]]


class ThumbnailLoader:
    """
    Create thumbnail icons for files selected in the app.

    Current behavior:
    1. JPG / JPEG files:
       We decode a scaled-down copy of the image with Qt.
    2. RAW files (CR2, CR3, DNG):
       We use the JPEG preview the camera stored inside the file, read through
       ExifTool, rotated to match the photo's orientation.
    3. Anything else, or if the above fails:
       We return a simple fallback icon.
    """

    BADGE_SIZE: Final[int] = 34
    BADGE_CORNER_RADIUS: Final[float] = 8.0
    BADGE_INSET: Final[int] = 2
    BADGE_ICON_NUDGE_X: Final[int] = 1
    BADGE_ICON_NUDGE_Y: Final[int] = -1
    MAX_CACHE_ENTRIES: Final[int] = 512

    def __init__(
        self,
        thumbnail_size: int = 128,
        preview_reader: PreviewReader | None = None,
        small_preview_reader: PreviewReader | None = None,
        use_system_cache: bool = False,
    ) -> None:
        """
        Store the target thumbnail size in pixels.

        Args:
            thumbnail_size:
                Maximum width and height for generated thumbnails.
            preview_reader:
                Reads embedded previews from RAW files. Without one, RAW files
                get the fallback icon.
            small_preview_reader:
                Reads the small thumbnails stored at the start of JPEG files,
                so a whole (possibly large, possibly network) photo doesn't
                have to be read. Without one, JPEGs are read in full.
            use_system_cache:
                Use and fill the Linux file managers' shared thumbnail cache
                (see system_thumbnails.py). Off by default so tests never touch
                the user's real cache.
        """
        self.thumbnail_size = thumbnail_size
        self.preview_reader = preview_reader
        self.small_preview_reader = small_preview_reader
        self.use_system_cache = use_system_cache and system_thumbnails.is_supported()
        self._icon_cache: dict[tuple[str, int | None, bool], QIcon] = {}

        # Store the path to the overlay icon used for photos that already have
        # GPS metadata. Keeping this as a project asset makes the badge more
        # consistent and professional than drawing a temporary text marker.
        self.overlay_icon_path = resource_path(
            Path("assets") / "satellite_overlay_icon_128 (croped).png"
        )
        self._fallback_icon = self._build_fallback_icon()
        self._badge_overlay_pixmap = self._load_trimmed_overlay_pixmap()
        self._gps_fallback_icon = self._build_badged_icon(self._fallback_icon)

    def load_icon(self, path: Path, has_gps: bool = False) -> QIcon:
        """
        Return a QIcon for the given file, building it right away if needed.

        JPEGs and RAW files get a real thumbnail; anything else, or a file
        that cannot be read, gets a fallback icon. Files with GPS metadata get
        a small badge in the top-right corner.

        This reads the file on the calling thread. For many files, use
        load_images() on a background thread and icon_from_image() instead.

        Args:
            path:
                Path to the file we want to represent in the UI.
            has_gps:
                True when the file has GPS metadata and should receive a badge.

        Returns:
            A QIcon that can be shown in a QListWidget or similar Qt widget.
        """
        cached_icon = self.cached_icon(path, has_gps)
        if cached_icon is not None:
            return cached_icon

        image = self.load_images([path]).get(path)
        return self.icon_from_image(path, has_gps, image)

    def cached_icon(self, path: Path, has_gps: bool = False) -> QIcon | None:
        """
        Return the icon if it was already built for this version of the file.
        """
        return self._icon_cache.get(self._build_cache_key(path, has_gps))

    def load_images(self, paths: list[Path]) -> dict[Path, QImage | None]:
        """
        Read thumbnail-sized images for many files, cheapest source first:

        1. The system thumbnail cache (Linux), a small local file.
        2. The preview stored inside the photo: for RAW files the embedded
           JPEG previews, for JPEGs their small EXIF thumbnail near the start
           of the file.
        3. The whole JPEG (only when it has no thumbnail inside).

        Thumbnails made from 2 or 3 are saved to the system cache.

        Safe to call on a background thread: it only uses QImage, never
        QPixmap or widgets, and does not touch the icon cache. Embedded
        previews for the whole list are read in one batch.

        Returns:
            {path: image} for every path; None where no image could be made.
        """
        images: dict[Path, QImage | None] = {}
        if self.use_system_cache:
            for path in paths:
                cached = system_thumbnails.read(path, self.thumbnail_size)
                if cached is not None:
                    images[path] = cached
        remaining = [path for path in paths if path not in images]

        raw_paths = [path for path in remaining if is_raw_file(path)]
        jpeg_paths = [path for path in remaining if path.suffix.lower() in JPEG_EXTENSIONS]
        previews: dict[Path, EmbeddedPreview] = {}
        for reader, reader_paths in (
            (self.preview_reader, raw_paths),
            (self.small_preview_reader, jpeg_paths),
        ):
            if reader_paths and reader is not None:
                try:
                    previews.update(reader(reader_paths))
                except Exception:
                    # Thumbnails are a convenience; fall back on any failure.
                    pass

        for path in remaining:
            image = None
            if path in previews:
                image = self._preview_to_image(previews[path])
            if image is None and path.suffix.lower() in JPEG_EXTENSIONS:
                image = self._read_jpeg_image(path)
            images[path] = image
            if image is not None and self.use_system_cache:
                system_thumbnails.write(path, image)
        return images

    def icon_from_image(self, path: Path, has_gps: bool, image: QImage | None) -> QIcon:
        """
        Turn an image from load_images() into a cached icon. GUI thread only.

        A missing image gives the fallback icon.
        """
        cache_key = self._build_cache_key(path, has_gps)

        if image is None or image.isNull():
            icon = self._gps_fallback_icon if has_gps else self._fallback_icon
        else:
            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                icon = self._gps_fallback_icon if has_gps else self._fallback_icon
            else:
                icon = self._build_badged_icon(QIcon(pixmap)) if has_gps else QIcon(pixmap)

        self._cache_icon(cache_key, icon)
        return icon

    def fallback_icon_for(self, has_gps: bool) -> QIcon:
        """
        The plain icon used when no thumbnail is available. Not cached per
        file, so a later load tries the real thumbnail again.
        """
        return self._gps_fallback_icon if has_gps else self._fallback_icon

    def _preview_to_image(self, preview: EmbeddedPreview) -> QImage | None:
        """
        Decode an embedded preview at thumbnail size, trim any padding, and
        rotate it upright.
        """
        buffer = QBuffer()
        buffer.setData(QByteArray(preview.jpeg_bytes))
        buffer.open(QBuffer.ReadOnly)
        reader = QImageReader(buffer)
        # Use the RAW file's orientation, not any tag inside the preview.
        reader.setAutoTransform(False)

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

        if preview.image_width and preview.image_height:
            image = _crop_to_aspect(image, preview.image_width, preview.image_height)
        return _apply_exif_orientation(image, preview.orientation)

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

    def _read_jpeg_image(self, path: Path) -> QImage | None:
        """
        Read a JPEG at thumbnail size, rotated upright using its own EXIF tag.

        Args:
            path:
                Path to a JPG/JPEG image.

        Returns:
            A QImage if reading succeeds, otherwise None.
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
        return None if image.isNull() else image

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


def _apply_exif_orientation(image: QImage, orientation: int) -> QImage:
    """
    Rotate and/or mirror an image according to an EXIF orientation value.

    EXIF orientations: 1 normal, 2 mirrored, 3 rotated 180, 4 flipped
    vertically, 5 mirrored + rotated 270, 6 rotated 90, 7 mirrored + rotated
    90, 8 rotated 270 (all rotations clockwise).
    """
    mirror = orientation in (2, 4, 5, 7)
    rotation = {3: 180, 4: 180, 5: 270, 6: 90, 7: 90, 8: 270}.get(orientation, 0)

    if mirror:
        image = image.transformed(QTransform().scale(-1, 1))
    if rotation:
        image = image.transformed(QTransform().rotate(rotation))
    return image


def _crop_to_aspect(image: QImage, width: int, height: int) -> QImage:
    """
    Crop an image, centered, to the width:height shape of the full photo.

    Removes the black bars some cameras add to small previews (Canon CR3
    thumbnails are 4:3 while the photo is 3:2). Images already within 2% of
    the right shape are returned unchanged.
    """
    target_ratio = width / height
    image_ratio = image.width() / image.height()
    if abs(image_ratio / target_ratio - 1) < 0.02:
        return image

    if image_ratio < target_ratio:
        # Too tall for the photo's shape: trim the top and bottom.
        new_height = max(1, round(image.width() / target_ratio))
        top = (image.height() - new_height) // 2
        return image.copy(0, top, image.width(), new_height)

    # Too wide: trim the left and right.
    new_width = max(1, round(image.height() * target_ratio))
    left = (image.width() - new_width) // 2
    return image.copy(left, 0, new_width, image.height())
