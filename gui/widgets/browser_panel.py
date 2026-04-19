"""
Browser panel UI builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._window._refresh_thumbnail_group_header_sizes()


def build_browser_panel(window: "MainWindow") -> QWidget:
    """
    Create the thumbnail browser panel shown on the left side.
    """
    panel = QFrame()
    panel.setObjectName("panel")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    section_heading = QLabel("Photos to Update")
    section_heading.setObjectName("sectionTitle")

    section_note = QLabel(
        "Choose photos in the browser, then add them to the update list on the right. Right click any thumbnail to copy its current GPS coordinates."
    )
    section_note.setObjectName("sectionNote")
    section_note.setWordWrap(True)

    header_row = QHBoxLayout()
    header_row.setSpacing(10)
    header_row.addWidget(window.select_button)
    window.remove_loaded_photos_button = QPushButton("Remove All Photos")
    window.remove_loaded_photos_button.setProperty("tone", "neutral")
    window.remove_loaded_photos_button.setEnabled(False)
    window.remove_loaded_photos_button.clicked.connect(window.remove_photos_from_browser_list)
    header_row.addWidget(window.remove_loaded_photos_button)
    header_row.addStretch(1)

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
    window.list_widget.itemSelectionChanged.connect(window.update_details_panel)
    window.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
    window.list_widget.customContextMenuRequested.connect(window.show_context_menu)
    window.list_widget.verticalScrollBar().setSingleStep(24)

    window.select_all_button = QPushButton("Select All")
    window.select_all_button.clicked.connect(window.select_all_photos)

    window.clear_selection_button = QPushButton("Clear Selection")
    window.clear_selection_button.clicked.connect(window.clear_photo_selection)

    window.add_selected_button = QPushButton("Add Selected to Update List")
    window.add_selected_button.setObjectName("accentButton")
    window.add_selected_button.setEnabled(False)
    window.add_selected_button.clicked.connect(window.add_selected_photos_to_target_list)

    selection_button_row = QHBoxLayout()
    selection_button_row.setSpacing(10)
    selection_button_row.addWidget(window.select_all_button)
    selection_button_row.addWidget(window.clear_selection_button)
    selection_button_row.addWidget(window.add_selected_button)

    window.browser_hint = QLabel(
        "No photos loaded yet. Use Choose Photos to populate the grid."
    )
    window.browser_hint.setObjectName("browserHint")
    window.browser_hint.setWordWrap(True)

    layout.addWidget(section_heading)
    layout.addWidget(section_note)
    layout.addLayout(header_row)
    layout.addLayout(selection_button_row)
    layout.addWidget(window.list_widget, 1)
    layout.addWidget(window.browser_hint)

    return panel
