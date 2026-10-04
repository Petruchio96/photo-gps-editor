"""
Draws placeholder tiles with a moving shimmer for thumbnails still loading.

Why a delegate:
    Animating by swapping icons would mean updating every waiting item many
    times a second. Instead, waiting items are flagged with SHIMMER_ROLE and
    this delegate paints a gray tile with a light band over them. One timer
    moves the band (advance()) and repaints the grid once per frame.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

# Item data role: True while an item's thumbnail is still loading and its
# placeholder should be drawn.
SHIMMER_ROLE = Qt.UserRole + 3

# One sweep of the light band across a tile takes this long.
SHIMMER_PERIOD_MS = 1200

TILE_COLOR = QColor("#e3e9f0")
BAND_COLOR = QColor(255, 255, 255, 190)


class ThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # 0.0-1.0: where the light band is in its sweep.
        self.phase = 0.0

    def advance(self, elapsed_ms: int) -> None:
        """Move the light band forward by elapsed_ms of animation time."""
        self.phase = (self.phase + elapsed_ms / SHIMMER_PERIOD_MS) % 1.0

    def paint(self, painter: QPainter, option, index) -> None:
        super().paint(painter, option, index)
        if not index.data(SHIMMER_ROLE):
            return

        style_option = QStyleOptionViewItem(option)
        self.initStyleOption(style_option, index)
        widget = style_option.widget
        style = widget.style() if widget is not None else QApplication.style()
        icon_rect = QRectF(
            style.subElementRect(QStyle.SE_ItemViewItemDecoration, style_option, widget)
        )
        if icon_rect.isEmpty():
            return

        tile = _placeholder_tile(icon_rect)
        tile_path = QPainterPath()
        tile_path.addRoundedRect(tile, 6, 6)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillPath(tile_path, TILE_COLOR)

        # A soft light band sweeping left to right, clipped to the tile.
        band_width = tile.width() * 0.6
        band_left = tile.left() - band_width + (tile.width() + band_width) * self.phase
        gradient = QLinearGradient(band_left, 0, band_left + band_width, 0)
        transparent = QColor(BAND_COLOR)
        transparent.setAlpha(0)
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.5, BAND_COLOR)
        gradient.setColorAt(1.0, transparent)
        painter.setClipPath(tile_path)
        painter.fillRect(tile, gradient)
        painter.restore()


def _placeholder_tile(icon_rect: QRectF) -> QRectF:
    """
    A 3:2 tile centered in the icon area, the shape of most photos.
    """
    width = icon_rect.width()
    height = min(icon_rect.height(), width * 2 / 3)
    top = icon_rect.top() + (icon_rect.height() - height) / 2
    return QRectF(icon_rect.left(), top, width, height)
