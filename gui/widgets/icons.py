"""
Small line icons for buttons and tabs, drawn in code.

Drawing them with QPainter (instead of loading SVG files) keeps the packaged
app free of Qt's SVG plugin and keeps the icons sharp at any screen scale.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

ICON_SIZE = 16
# Drawn at 2x so they stay crisp on high-DPI screens.
_SCALE = 2


def _icon(color: str, draw) -> QIcon:
    pixmap = QPixmap(ICON_SIZE * _SCALE, ICON_SIZE * _SCALE)
    pixmap.setDevicePixelRatio(_SCALE)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    draw(painter)
    painter.end()
    return QIcon(pixmap)


def plus_icon(color: str) -> QIcon:
    def draw(painter: QPainter) -> None:
        painter.drawLine(QPointF(8, 3), QPointF(8, 13))
        painter.drawLine(QPointF(3, 8), QPointF(13, 8))

    return _icon(color, draw)


def pin_icon(color: str) -> QIcon:
    """Map pin, for the Location tab."""

    def draw(painter: QPainter) -> None:
        path = QPainterPath(QPointF(8, 14.5))
        path.cubicTo(QPointF(8, 14.5), QPointF(3, 10), QPointF(3, 6.5))
        path.arcTo(QRectF(3, 1.5, 10, 10), 180, -180)
        path.cubicTo(QPointF(13, 10), QPointF(8, 14.5), QPointF(8, 14.5))
        painter.drawPath(path)
        painter.drawEllipse(QPointF(8, 6.5), 1.8, 1.8)

    return _icon(color, draw)


def clock_icon(color: str) -> QIcon:
    """Clock face, for the Date & Time tab."""

    def draw(painter: QPainter) -> None:
        painter.drawEllipse(QPointF(8, 8), 6, 6)
        painter.drawLine(QPointF(8, 4.8), QPointF(8, 8))
        painter.drawLine(QPointF(8, 8), QPointF(10.2, 9.4))

    return _icon(color, draw)
