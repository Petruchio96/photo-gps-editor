"""
Keeps the inspector panel in sync with the photos selected in the grid.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap

from gui.presenters.inspector_state import InspectorState, build_inspector_state

# Multi-selection preview: up to this many small thumbnails, then "+N".
PREVIEW_TILE_SIZE = 72
PREVIEW_MAX_TILES = 4
PREVIEW_GAP = 8


class InspectorMixin:
    def update_details_panel(self) -> None:
        self._update_selection_metrics()
        state = self._build_inspector_state()
        self._apply_inspector_state(state)

    def _build_inspector_state(self) -> InspectorState:
        return build_inspector_state(
            selected_paths=self.get_selected_paths(),
            photo_infos=self.session.loaded_photo_infos,
            latitude_text=self.latitude_input.text(),
            longitude_text=self.longitude_input.text(),
        )

    def _apply_inspector_state(self, state: InspectorState) -> None:
        self.selection_title_label.setText(state.title)
        self.selection_gps_label.setText(state.gps_summary)
        self._refresh_selection_preview()

        single = state.selected_count == 1
        self.copy_location_button.setVisible(single)
        self.use_location_button.setVisible(single)
        self.copy_location_button.setEnabled(state.can_use_location)
        self.use_location_button.setEnabled(state.can_use_location)

        has_fields = bool(self.latitude_input.text().strip() or self.longitude_input.text().strip())
        self.clear_location_button.setEnabled(has_fields)
        self._update_clipboard_buttons()

        self.apply_button.setText(state.apply_label)
        self.apply_button.setEnabled(state.can_apply)
        self.apply_hint_label.setText(state.apply_hint)
        self.apply_hint_label.setVisible(bool(state.apply_hint))
        self._set_tone(self.apply_hint_label, state.apply_hint_tone)

        self.remove_gps_button.setText(state.remove_gps_label)
        self.remove_gps_button.setEnabled(state.can_remove_gps)

    def _refresh_selection_preview(self) -> None:
        """
        Show the selected photo's thumbnail, or a row of small ones.
        """
        items = self._selected_photo_items()
        width = max(self.selection_preview.width(), 200)
        height = self.selection_preview.height()

        if not items:
            self.selection_preview.clear()
            self.selection_preview.setProperty("empty", True)
            self._repolish(self.selection_preview)
            return

        self.selection_preview.setProperty("empty", False)
        self._repolish(self.selection_preview)

        if len(items) == 1:
            size = height - 8
            self.selection_preview.setPixmap(items[0].icon().pixmap(size, size))
            return

        canvas = QPixmap(width, height)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        shown = items[:PREVIEW_MAX_TILES]
        extra = len(items) - len(shown)
        tile_count = len(shown) + (1 if extra else 0)
        total_width = tile_count * PREVIEW_TILE_SIZE + (tile_count - 1) * PREVIEW_GAP
        left = max(0, (width - total_width) // 2)
        top = (height - PREVIEW_TILE_SIZE) // 2

        for position, item in enumerate(shown):
            pixmap = item.icon().pixmap(PREVIEW_TILE_SIZE, PREVIEW_TILE_SIZE)
            x = left + position * (PREVIEW_TILE_SIZE + PREVIEW_GAP)
            # Center each thumbnail in its square tile.
            painter.drawPixmap(
                x + (PREVIEW_TILE_SIZE - pixmap.width()) // 2,
                top + (PREVIEW_TILE_SIZE - pixmap.height()) // 2,
                pixmap,
            )

        if extra:
            x = left + len(shown) * (PREVIEW_TILE_SIZE + PREVIEW_GAP)
            tile = QRect(x, top, PREVIEW_TILE_SIZE, PREVIEW_TILE_SIZE)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#e3e9f0"))
            painter.drawRoundedRect(tile, 8, 8)
            font = QFont(painter.font())
            font.setPointSize(13)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#31445a"))
            painter.drawText(tile, Qt.AlignCenter, f"+{extra}")

        painter.end()
        self.selection_preview.setPixmap(canvas)

    def _set_tone(self, widget, tone: str) -> None:
        if widget.property("tone") != tone:
            widget.setProperty("tone", tone)
            self._repolish(widget)

    @staticmethod
    def _repolish(widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
