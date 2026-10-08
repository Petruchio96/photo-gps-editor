"""
Inspector panel UI builder (the right side of the window).

The photos selected in the Photo List are the photos being edited. This pane
shows what is selected, then two tabs: Location (the new location and the two
actions, Apply and Remove GPS, which is destructive so styled to stand apart)
and Date & Time (a placeholder for now).
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.browser_panel import build_pane_header
from gui.widgets.icons import clock_icon, pin_icon

if TYPE_CHECKING:
    from gui.main_window import MainWindow

# The pick button's label; it reads "Cancel" while picking.
PICK_BUTTON_TEXT = "From a Photo in the Photo List"
PICK_BUTTON_TIP = (
    "Click this, then click a photo with GPS in the Photo List to copy "
    "its location. The photos selected to change stay selected."
)

# Tab positions in editor_tabs.
LOCATION_TAB = 0
DATE_TIME_TAB = 1


def _build_selection_summary(window: "MainWindow") -> QWidget:
    """
    Under the header: how many photos are selected, and how many of them
    have GPS.
    """
    summary = QWidget()
    layout = QHBoxLayout(summary)
    layout.setContentsMargins(22, 16, 20, 12)
    layout.setSpacing(14)

    window.selection_title_label = QLabel("No Photos Selected")
    window.selection_title_label.setObjectName("sectionTitle")
    window.selection_title_label.setWordWrap(True)

    window.selection_gps_label = QLabel()
    window.selection_gps_label.setObjectName("selectionGps")
    window.selection_gps_label.setWordWrap(True)
    window.selection_gps_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    text = QVBoxLayout()
    text.setSpacing(2)
    text.addWidget(window.selection_title_label)
    text.addWidget(window.selection_gps_label)

    # Shown only when one photo with GPS is selected.
    window.copy_location_button = QPushButton("Copy")
    window.copy_location_button.setProperty("tone", "neutral")
    window.copy_location_button.setToolTip("Copy this photo's GPS coordinates")
    window.copy_location_button.clicked.connect(window.copy_selected_photo_gps_coordinates)

    layout.addLayout(text, 1)
    layout.addWidget(window.copy_location_button, 0, Qt.AlignVCenter)
    return summary


def _build_location_group(window: "MainWindow") -> QGroupBox:
    """
    The New Location box: where the new coordinates come from.
    Blue throughout means "where the location comes from".
    """
    location_group = QGroupBox("New Location")
    location_group.setObjectName("locationGroup")
    location_layout = QVBoxLayout(location_group)
    location_layout.setSpacing(10)

    copy_label = QLabel("Copy location")
    copy_label.setObjectName("fieldLabel")

    # Pick a photo in the grid to take its location from ("eyedropper").
    window.pick_location_button = QPushButton(PICK_BUTTON_TEXT)
    window.pick_location_button.setObjectName("pickButton")
    window.pick_location_button.setCheckable(True)
    window.pick_location_button.setToolTip(PICK_BUTTON_TIP)
    window.pick_location_button.clicked.connect(window.toggle_picking_location)

    window.location_from_photo_button = QPushButton("From a Photo on Your Computer")
    window.location_from_photo_button.setObjectName("pickButton")
    window.location_from_photo_button.setToolTip(
        "Choose any photo file on your computer and use its GPS coordinates"
    )
    window.location_from_photo_button.clicked.connect(window.choose_location_from_photo)

    copy_buttons = QHBoxLayout()
    copy_buttons.setSpacing(8)
    copy_buttons.addWidget(window.pick_location_button, 1)
    copy_buttons.addWidget(window.location_from_photo_button, 1)

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

    window.clear_location_button = QPushButton("Clear")
    window.clear_location_button.setProperty("tone", "neutral")
    window.clear_location_button.setToolTip("Empty the latitude and longitude fields")
    window.clear_location_button.clicked.connect(window.clear_location_fields)

    location_buttons = QHBoxLayout()
    location_buttons.setSpacing(8)
    location_buttons.addWidget(window.paste_coordinates_button, 1)
    location_buttons.addWidget(window.clear_location_button, 1)

    location_layout.addWidget(copy_label)
    location_layout.addLayout(copy_buttons)
    location_layout.addWidget(window.source_card)
    location_layout.addLayout(fields)
    location_layout.addLayout(location_buttons)
    return location_group


def _build_location_tab(window: "MainWindow") -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 20)
    layout.setSpacing(10)

    window.apply_hint_label = QLabel()
    window.apply_hint_label.setObjectName("applyHint")
    window.apply_hint_label.setWordWrap(True)

    window.apply_button = QPushButton("Apply Location to Selected Photos")
    window.apply_button.setObjectName("accentButton")
    window.apply_button.setEnabled(False)
    window.apply_button.setMinimumHeight(44)
    window.apply_button.setToolTip("Write the New Location into the selected photos")
    window.apply_button.clicked.connect(window.apply_coordinates_to_selected)

    window.remove_gps_button = QPushButton("Remove GPS from Selected Photos")
    window.remove_gps_button.setObjectName("removeGpsButton")
    window.remove_gps_button.setEnabled(False)
    window.remove_gps_button.setToolTip(
        "Delete the GPS coordinates stored in the selected photos that have them. "
        "You can undo this afterwards."
    )
    window.remove_gps_button.clicked.connect(window.remove_gps_from_selected)

    layout.addWidget(_build_location_group(window))
    layout.addStretch(1)
    layout.addWidget(window.apply_hint_label)
    layout.addWidget(window.apply_button)
    layout.addWidget(window.remove_gps_button)
    return page


def _build_date_time_tab() -> QWidget:
    """
    Placeholder until changing photo dates and times is designed.
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 20)

    placeholder = QFrame()
    placeholder.setObjectName("tabPlaceholder")
    placeholder_layout = QVBoxLayout(placeholder)
    placeholder_layout.setContentsMargins(24, 24, 24, 24)
    placeholder_layout.setSpacing(8)
    title = QLabel("Date & Time editing")
    title.setObjectName("tabPlaceholderTitle")
    title.setAlignment(Qt.AlignCenter)
    detail = QLabel("Coming soon: changing the date and time stored in photos.")
    detail.setObjectName("tabPlaceholderDetail")
    detail.setAlignment(Qt.AlignCenter)
    detail.setWordWrap(True)
    placeholder_layout.addStretch(1)
    placeholder_layout.addWidget(title)
    placeholder_layout.addWidget(detail)
    placeholder_layout.addStretch(1)

    layout.addWidget(placeholder, 1)
    return page


def build_editor_panel(window: "MainWindow") -> QWidget:
    """
    Create the right side pane: what is selected, then the Location and
    Date & Time tabs.
    """
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # Brown: "your selection, the photos to change".
    header, _header_layout = build_pane_header("PHOTOS TO CHANGE", "change")

    window.editor_tabs = QTabWidget()
    window.editor_tabs.setObjectName("editorTabs")
    window.editor_tabs.tabBar().setDrawBase(False)
    window.editor_tabs.addTab(_build_location_tab(window), pin_icon("#31445a"), "Location")
    # "&&" shows a plain "&" (a single "&" marks a keyboard shortcut letter).
    window.editor_tabs.addTab(_build_date_time_tab(), clock_icon("#31445a"), "Date && Time")
    window.editor_tabs.setTabToolTip(LOCATION_TAB, "Change where the selected photos were taken")
    window.editor_tabs.setTabToolTip(DATE_TIME_TAB, "Change when the selected photos were taken (coming soon)")

    layout.addWidget(header)
    layout.addWidget(_build_selection_summary(window))
    layout.addWidget(window.editor_tabs, 1)
    return panel
