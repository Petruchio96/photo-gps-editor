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


def build_browser_panel(window: "MainWindow") -> QWidget:
    """
    Create the thumbnail browser panel shown on the left side.
    """
    panel = QFrame()
    panel.setObjectName("panel")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    section_heading = QLabel("Library")
    section_heading.setObjectName("sectionTitle")

    section_note = QLabel(
        "Select one or many images. Right click any thumbnail to copy its current GPS coordinates."
    )
    section_note.setObjectName("sectionNote")
    section_note.setWordWrap(True)

    window.list_widget = QListWidget()
    window.list_widget.setObjectName("thumbnailGrid")
    window.list_widget.setViewMode(QListWidget.IconMode)
    window.list_widget.setIconSize(QSize(128, 128))
    window.list_widget.setGridSize(QSize(170, 190))
    window.list_widget.setResizeMode(QListWidget.Adjust)
    window.list_widget.setSpacing(12)
    window.list_widget.setUniformItemSizes(True)
    window.list_widget.setWordWrap(True)
    window.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
    window.list_widget.itemSelectionChanged.connect(window.update_details_panel)
    window.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
    window.list_widget.customContextMenuRequested.connect(window.show_context_menu)

    window.select_all_button = QPushButton("Select All")
    window.select_all_button.clicked.connect(window.select_all_photos)

    window.clear_selection_button = QPushButton("Clear Selection")
    window.clear_selection_button.clicked.connect(window.clear_photo_selection)

    selection_button_row = QHBoxLayout()
    selection_button_row.setSpacing(10)
    selection_button_row.addWidget(window.select_all_button)
    selection_button_row.addWidget(window.clear_selection_button)

    window.browser_hint = QLabel(
        "No photos loaded yet. Use Open Photos to populate the grid."
    )
    window.browser_hint.setObjectName("browserHint")
    window.browser_hint.setWordWrap(True)

    layout.addWidget(section_heading)
    layout.addWidget(section_note)
    layout.addLayout(selection_button_row)
    layout.addWidget(window.list_widget, 1)
    layout.addWidget(window.browser_hint)

    return panel
