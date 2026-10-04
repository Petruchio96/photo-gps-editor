"""
Browser panel UI builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.loading_indicator import LoadingIndicator
from gui.widgets.thumbnail_delegate import ThumbnailDelegate

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ThumbnailGrid(QListWidget):
    """
    QListWidget variant that lets the window keep full-width section rows sized
    correctly after the icon grid is resized.
    """

    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self._window = window
        # Shown in the middle of the grid when no photos are visible.
        self.empty_message = ""

    def mousePressEvent(self, event) -> None:
        # Pick mode: a click chooses the location source and never changes
        # which photos are selected for updating.
        if self._window.is_picking_location and event.button() == Qt.LeftButton:
            self._window.pick_location_from_item(self.itemAt(event.position().toPoint()))
            event.accept()
            return
        # Right-click opens the context menu for the photo under the cursor
        # without changing the selection (Qt would normally select it).
        if event.button() == Qt.RightButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        # Esc leaves pick mode when the grid has focus (the window-wide Esc
        # shortcut covers the rest of the window).
        if self._window.is_picking_location and event.key() == Qt.Key_Escape:
            self._window.stop_picking_location()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._window.is_picking_location:
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def set_empty_message(self, message: str) -> None:
        if message != self.empty_message:
            self.empty_message = message
            self.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._window._refresh_thumbnail_group_header_sizes()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.empty_message:
            return
        painter = QPainter(self.viewport())
        painter.setPen(QColor("#7a8899"))
        font = QFont(painter.font())
        font.setPointSize(font.pointSize() + 2)
        painter.setFont(font)
        painter.drawText(self.viewport().rect(), Qt.AlignCenter | Qt.TextWordWrap, self.empty_message)
        painter.end()


# Show filter values, in button order.
GRID_FILTERS = (
    ("all", "All"),
    ("needs", "Needs GPS"),
    ("has", "Has GPS"),
)


def build_browser_panel(window: "MainWindow") -> QWidget:
    """
    Create the photo grid panel shown on the left side.
    """
    panel = QFrame()
    panel.setObjectName("panel")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)

    section_heading = QLabel("Photos")
    section_heading.setObjectName("sectionTitle")

    # Row 1: add/remove photos, and selection shortcuts.
    header_row = QHBoxLayout()
    header_row.setSpacing(10)
    window.select_button.setProperty("tone", "primary")
    header_row.addWidget(window.select_button)
    window.remove_loaded_photos_button = QPushButton("Remove All from List")
    window.remove_loaded_photos_button.setProperty("tone", "neutral")
    window.remove_loaded_photos_button.setEnabled(False)
    window.remove_loaded_photos_button.setToolTip(
        "Removes photos from this list only. Files are not changed or deleted."
    )
    window.remove_loaded_photos_button.clicked.connect(window.remove_photos_from_browser_list)
    header_row.addWidget(window.remove_loaded_photos_button)
    header_row.addStretch(1)

    window.select_all_button = QPushButton("Select All")
    window.select_all_button.setProperty("tone", "neutral")
    window.select_all_button.setToolTip("Select every photo currently shown")
    window.select_all_button.clicked.connect(window.select_all_photos)
    window.clear_selection_button = QPushButton("Clear Selection")
    window.clear_selection_button.setProperty("tone", "neutral")
    window.clear_selection_button.clicked.connect(window.clear_photo_selection)
    header_row.addWidget(window.select_all_button)
    header_row.addWidget(window.clear_selection_button)

    # Row 2: Show filter (All / Needs GPS / Has GPS), a segmented control.
    filter_row = QHBoxLayout()
    filter_row.setSpacing(0)
    show_label = QLabel("Show:")
    show_label.setObjectName("filterLabel")
    filter_row.addWidget(show_label)
    filter_row.addSpacing(10)
    window.grid_filter_group = QButtonGroup(panel)
    window.grid_filter_group.setExclusive(True)
    window.grid_filter_buttons = {}
    for position, (key, text) in enumerate(GRID_FILTERS):
        button = QPushButton(text)
        button.setObjectName("filterButton")
        button.setProperty("filter", key)
        button.setCheckable(True)
        button.setProperty(
            "segment",
            "first" if position == 0 else "last" if position == len(GRID_FILTERS) - 1 else "middle",
        )
        button.clicked.connect(lambda _checked=False, key=key: window.set_grid_filter(key))
        window.grid_filter_group.addButton(button)
        window.grid_filter_buttons[key] = button
        filter_row.addWidget(button)
    window.grid_filter_buttons["all"].setChecked(True)
    filter_row.addStretch(1)

    # Banner shown while picking a location source from the grid.
    window.pick_banner = QFrame()
    window.pick_banner.setObjectName("pickBanner")
    banner_layout = QHBoxLayout(window.pick_banner)
    banner_layout.setContentsMargins(14, 8, 8, 8)
    window.pick_banner_label = QLabel()
    window.pick_banner_label.setObjectName("pickBannerText")
    window.pick_banner_label.setWordWrap(True)
    window.pick_cancel_button = QPushButton("Cancel")
    window.pick_cancel_button.setObjectName("pickCancel")
    window.pick_cancel_button.clicked.connect(window.stop_picking_location)
    banner_layout.addWidget(window.pick_banner_label, 1)
    banner_layout.addWidget(window.pick_cancel_button)
    window.pick_banner.hide()

    window.list_widget = ThumbnailGrid(window)
    window.list_widget.setObjectName("thumbnailGrid")
    window.list_widget.setViewMode(QListWidget.IconMode)
    window.list_widget.setIconSize(QSize(128, 128))
    window.list_widget.setResizeMode(QListWidget.Adjust)
    window.list_widget.setSpacing(12)
    window.list_widget.setWordWrap(True)
    window.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
    window.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
    # Tiles stay in place: no dragging them around the grid.
    window.list_widget.setMovement(QListWidget.Static)
    window.list_widget.setDragEnabled(False)
    window.list_widget.setDragDropMode(QListWidget.NoDragDrop)
    window.list_widget.itemSelectionChanged.connect(window.update_details_panel)
    window.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
    window.list_widget.customContextMenuRequested.connect(window.show_context_menu)
    window.list_widget.verticalScrollBar().setSingleStep(24)
    # Draws shimmering placeholders for thumbnails that are still loading.
    window.thumbnail_delegate = ThumbnailDelegate(window.list_widget)
    window.list_widget.setItemDelegate(window.thumbnail_delegate)

    # Status row under the grid: photo counts, action feedback (with Undo),
    # and the loading progress row, which takes its place while loading.
    window.browser_hint = QLabel(
        "No photos loaded yet. Use Choose Photos to add some."
    )
    window.browser_hint.setObjectName("browserHint")
    window.browser_hint.setWordWrap(True)
    window.browser_hint.setTextFormat(Qt.RichText)
    window.browser_hint.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
    window.browser_hint.linkActivated.connect(window._handle_status_link)

    window.loading_indicator = LoadingIndicator(window.browser_hint)
    window.loading_indicator.cancel_requested.connect(window.cancel_loading)

    layout.addWidget(section_heading)
    layout.addLayout(header_row)
    layout.addLayout(filter_row)
    layout.addWidget(window.pick_banner)
    layout.addWidget(window.list_widget, 1)
    layout.addWidget(window.loading_indicator)

    return panel
