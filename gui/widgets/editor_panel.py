"""
Inspector panel UI builder (the right side of the window).

The photos selected in the grid are the photos being edited. This panel shows
what is selected, holds the new location, and offers the two actions:
Apply (the main action) and Remove GPS (destructive, so styled to stand apart).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from gui.main_window import MainWindow

SELECTION_PREVIEW_HEIGHT = 168


def build_editor_panel(window: "MainWindow") -> QWidget:
    """
    Create the right side panel: selection summary, new location, and actions.
    """
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    # --- What is selected -------------------------------------------------
    # Orange throughout means "your selection: the photos to change".
    selection_eyebrow = QLabel("PHOTOS TO CHANGE")
    selection_eyebrow.setObjectName("eyebrow")
    selection_eyebrow.setProperty("tone", "selection")

    window.selection_title_label = QLabel("No Photos Selected")
    window.selection_title_label.setObjectName("sectionTitle")
    window.selection_title_label.setWordWrap(True)

    window.selection_preview = QLabel()
    window.selection_preview.setObjectName("selectionPreview")
    window.selection_preview.setAlignment(Qt.AlignCenter)
    window.selection_preview.setFixedHeight(SELECTION_PREVIEW_HEIGHT)

    window.selection_gps_label = QLabel()
    window.selection_gps_label.setObjectName("selectionGps")
    window.selection_gps_label.setWordWrap(True)
    window.selection_gps_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    window.copy_location_button = QPushButton("Copy")
    window.copy_location_button.setProperty("tone", "neutral")
    window.copy_location_button.setToolTip("Copy this photo's GPS coordinates")
    window.copy_location_button.clicked.connect(window.copy_selected_photo_gps_coordinates)

    selection_buttons = QHBoxLayout()
    selection_buttons.setSpacing(10)
    selection_buttons.addWidget(window.copy_location_button)
    selection_buttons.addStretch(1)

    # --- New location -----------------------------------------------------
    location_group = QGroupBox("New Location")
    location_group.setObjectName("locationGroup")
    location_layout = QVBoxLayout(location_group)
    location_layout.setSpacing(10)

    # Pick a photo in the grid to take its location from ("eyedropper").
    # Blue throughout means "where the location comes from".
    window.pick_location_button = QPushButton("Pick from Grid")
    window.pick_location_button.setObjectName("pickButton")
    window.pick_location_button.setCheckable(True)
    window.pick_location_button.setToolTip(
        "Click this, then click a photo in the grid to use its location. "
        "Your selection of photos to change is left alone."
    )
    window.pick_location_button.clicked.connect(window.toggle_picking_location)

    # Shows which photo the location came from, when it came from one.
    window.source_card = QFrame()
    window.source_card.setObjectName("sourceCard")
    source_card_layout = QHBoxLayout(window.source_card)
    source_card_layout.setContentsMargins(10, 8, 6, 8)
    source_card_layout.setSpacing(10)
    window.source_card_thumbnail = QLabel()
    window.source_card_thumbnail.setFixedSize(52, 52)
    window.source_card_thumbnail.setAlignment(Qt.AlignCenter)
    source_text = QVBoxLayout()
    source_text.setSpacing(2)
    window.source_card_title = QLabel()
    window.source_card_title.setObjectName("sourceCardTitle")
    window.source_card_detail = QLabel()
    window.source_card_detail.setObjectName("sourceCardDetail")
    source_text.addWidget(window.source_card_title)
    source_text.addWidget(window.source_card_detail)
    window.source_card_clear = QPushButton("✕")
    window.source_card_clear.setObjectName("sourceCardClear")
    window.source_card_clear.setToolTip("Clear the location")
    window.source_card_clear.setFixedSize(30, 30)
    window.source_card_clear.clicked.connect(window.clear_location_fields)
    source_card_layout.addWidget(window.source_card_thumbnail)
    source_card_layout.addLayout(source_text, 1)
    source_card_layout.addWidget(window.source_card_clear, 0, Qt.AlignTop)
    window.source_card.hide()

    fields = QFormLayout()
    fields.setSpacing(10)
    window.latitude_input = QLineEdit()
    window.longitude_input = QLineEdit()
    window.latitude_input.setPlaceholderText("e.g. 40.5865 or 40° 35' 11\" N")
    window.longitude_input.setPlaceholderText("e.g. -111.6558 or 111° 39' 21\" W")
    window.latitude_input.editingFinished.connect(window.validate_latitude_field)
    window.longitude_input.editingFinished.connect(window.validate_longitude_field)
    window.latitude_input.textChanged.connect(window._handle_location_input_change)
    window.longitude_input.textChanged.connect(window._handle_location_input_change)
    fields.addRow("Latitude:", window.latitude_input)
    fields.addRow("Longitude:", window.longitude_input)

    window.paste_coordinates_button = QPushButton("Paste")
    window.paste_coordinates_button.setProperty("tone", "neutral")
    window.paste_coordinates_button.setToolTip("Paste coordinates copied from a map or another photo")
    window.paste_coordinates_button.clicked.connect(window.paste_coordinates_from_clipboard)

    window.location_from_photo_button = QPushButton("From a Photo…")
    window.location_from_photo_button.setProperty("tone", "neutral")
    window.location_from_photo_button.setToolTip(
        "Choose any photo file and use its GPS coordinates"
    )
    window.location_from_photo_button.clicked.connect(window.choose_location_from_photo)

    window.clear_location_button = QPushButton("Clear")
    window.clear_location_button.setProperty("tone", "neutral")
    window.clear_location_button.setToolTip("Empty the latitude and longitude fields")
    window.clear_location_button.clicked.connect(window.clear_location_fields)

    location_buttons = QHBoxLayout()
    location_buttons.setSpacing(10)
    location_buttons.addWidget(window.paste_coordinates_button)
    location_buttons.addWidget(window.location_from_photo_button)
    location_buttons.addWidget(window.clear_location_button)

    location_layout.addWidget(window.pick_location_button)
    location_layout.addWidget(window.source_card)
    location_layout.addLayout(fields)
    location_layout.addLayout(location_buttons)

    # --- Actions ----------------------------------------------------------
    window.apply_hint_label = QLabel()
    window.apply_hint_label.setObjectName("applyHint")
    window.apply_hint_label.setWordWrap(True)

    window.apply_button = QPushButton("Apply to Selected Photos")
    window.apply_button.setObjectName("accentButton")
    window.apply_button.setEnabled(False)
    window.apply_button.setMinimumHeight(44)
    window.apply_button.clicked.connect(window.apply_coordinates_to_selected)

    window.remove_gps_button = QPushButton("Remove GPS")
    window.remove_gps_button.setObjectName("removeGpsButton")
    window.remove_gps_button.setEnabled(False)
    window.remove_gps_button.setToolTip(
        "Permanently delete the GPS coordinates stored in the selected photos"
    )
    window.remove_gps_button.clicked.connect(window.remove_gps_from_selected)

    layout.addWidget(selection_eyebrow)
    layout.addWidget(window.selection_title_label)
    layout.addWidget(window.selection_preview)
    layout.addWidget(window.selection_gps_label)
    layout.addLayout(selection_buttons)
    layout.addSpacing(6)
    layout.addWidget(location_group)
    layout.addStretch(1)
    layout.addWidget(window.apply_hint_label)
    layout.addWidget(window.apply_button)
    layout.addWidget(window.remove_gps_button)

    return panel
