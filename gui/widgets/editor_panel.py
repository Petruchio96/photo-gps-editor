"""
Editor panel UI builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def build_editor_panel(window: "MainWindow") -> QWidget:
    """
    Create the right side panel for GPS source and destination actions.
    """
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    inspector_title = QLabel("GPS Editor")
    inspector_title.setObjectName("sectionTitle")

    inspector_note = QLabel(
        "Choose a source photo or enter coordinates manually, review the selected destinations, and then write metadata with a clear overwrite check."
    )
    inspector_note.setObjectName("sectionNote")
    inspector_note.setWordWrap(True)

    source_group = QGroupBox("GPS Source")
    source_layout = QVBoxLayout(source_group)
    source_layout.setSpacing(10)

    window.photo_source_radio = QRadioButton("Use Source Photo")
    window.manual_source_radio = QRadioButton("Enter Coordinates Manually")
    window.photo_source_radio.setChecked(True)

    window.source_mode_group = QButtonGroup(window)
    window.source_mode_group.addButton(window.photo_source_radio)
    window.source_mode_group.addButton(window.manual_source_radio)
    window.photo_source_radio.toggled.connect(window._update_source_mode_ui)

    source_mode_layout = QVBoxLayout()
    source_mode_layout.setSpacing(6)
    source_mode_layout.addWidget(window.photo_source_radio)
    source_mode_layout.addWidget(window.manual_source_radio)

    window.source_preview_stack = QStackedWidget()

    empty_source_widget = QWidget()
    empty_source_layout = QVBoxLayout(empty_source_widget)
    empty_source_layout.setContentsMargins(0, 0, 0, 0)
    empty_source_layout.setSpacing(8)

    empty_source_label = QLabel(
        "No source photo selected yet. Choose a photo to load its thumbnail and GPS coordinates here."
    )
    empty_source_label.setObjectName("sourceHint")
    empty_source_label.setWordWrap(True)
    empty_source_layout.addWidget(empty_source_label)

    source_preview_widget = QWidget()
    source_preview_layout = QVBoxLayout(source_preview_widget)
    source_preview_layout.setContentsMargins(0, 0, 0, 0)
    source_preview_layout.setSpacing(8)

    window.source_thumbnail = QLabel()
    window.source_thumbnail.setObjectName("sourceThumbnail")
    window.source_thumbnail.setFixedSize(180, 180)
    window.source_thumbnail.setAlignment(Qt.AlignCenter)

    window.source_file_label = QLabel("No source photo selected")
    window.source_file_label.setObjectName("sourceFileLabel")
    window.source_file_label.setWordWrap(True)

    window.source_gps_label = QLabel("Source GPS: Not loaded")
    window.source_gps_label.setObjectName("destinationSummary")
    window.source_gps_label.setWordWrap(True)

    source_preview_layout.addWidget(window.source_file_label)
    source_preview_layout.addWidget(window.source_gps_label)
    source_preview_layout.addWidget(
        window.source_thumbnail,
        alignment=Qt.AlignCenter,
    )

    window.source_preview_stack.addWidget(empty_source_widget)
    window.source_preview_stack.addWidget(source_preview_widget)

    window.choose_source_button = QPushButton("Choose Source Photo...")
    window.choose_source_button.clicked.connect(window.choose_source_photo)

    window.clear_source_button = QPushButton("Clear Source")
    window.clear_source_button.setEnabled(False)
    window.clear_source_button.clicked.connect(window.clear_source_photo)

    photo_source_panel = QWidget()
    photo_source_layout = QVBoxLayout(photo_source_panel)
    photo_source_layout.setContentsMargins(0, 0, 0, 0)
    photo_source_layout.setSpacing(10)
    photo_source_layout.addWidget(window.source_preview_stack)

    source_button_row = QHBoxLayout()
    source_button_row.setSpacing(10)
    source_button_row.addWidget(window.choose_source_button)
    source_button_row.addWidget(window.clear_source_button)
    photo_source_layout.addLayout(source_button_row)

    window.manual_source_panel = QWidget()
    manual_source_layout = QFormLayout(window.manual_source_panel)
    manual_source_layout.setContentsMargins(0, 0, 0, 0)
    manual_source_layout.setSpacing(10)

    window.latitude_input = QLineEdit()
    window.longitude_input = QLineEdit()
    window.latitude_input.setPlaceholderText("e.g. 40.486325")
    window.longitude_input.setPlaceholderText("e.g. -111.813415")
    window.latitude_input.editingFinished.connect(window.validate_latitude_field)
    window.longitude_input.editingFinished.connect(window.validate_longitude_field)
    window.latitude_input.textChanged.connect(
        lambda text: window._handle_manual_coordinate_input_change(text)
    )
    window.longitude_input.textChanged.connect(
        lambda text: window._handle_manual_coordinate_input_change(text)
    )

    window.paste_coordinates_button = QPushButton("Paste Coordinates")
    window.paste_coordinates_button.clicked.connect(
        window.paste_coordinates_from_clipboard
    )

    manual_source_layout.addRow("Latitude:", window.latitude_input)
    manual_source_layout.addRow("Longitude:", window.longitude_input)
    manual_source_layout.addRow("", window.paste_coordinates_button)

    window.source_mode_stack = QStackedWidget()
    window.source_mode_stack.addWidget(photo_source_panel)
    window.source_mode_stack.addWidget(window.manual_source_panel)

    window.active_source_coordinates = QLabel("Coordinates to Apply: Not set")
    window.active_source_coordinates.setObjectName("sourceSummary")
    window.active_source_coordinates.setWordWrap(True)

    source_layout.addLayout(source_mode_layout)
    source_layout.addWidget(window.source_mode_stack)
    source_layout.addWidget(window.active_source_coordinates)

    window.destination_list = QListWidget()
    window.destination_list.setObjectName("destinationList")
    window.destination_list.setSelectionMode(QListWidget.NoSelection)
    window.destination_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    window.destination_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.destination_list.setMaximumHeight(124)
    window.destination_list.setMinimumHeight(124)

    window.destination_title_label = QLabel("Selected Destinations")
    window.destination_title_label.setObjectName("sectionTitle")

    window.apply_button = QPushButton("Apply GPS to Destination Files")
    window.apply_button.setEnabled(False)
    window.apply_button.setMinimumHeight(34)
    window.apply_button.clicked.connect(window.apply_coordinates_to_selected)

    window.status_message = QLabel("Choose a source and select destination photos.")
    window.status_message.setObjectName("statusCard")
    window.status_message.setProperty("tone", "info")
    window.status_message.setWordWrap(True)

    layout.addWidget(inspector_title)
    layout.addWidget(inspector_note)
    layout.addWidget(source_group)
    layout.addWidget(window.destination_title_label)
    layout.addWidget(window.destination_list)
    layout.addWidget(window.apply_button)
    layout.addWidget(window.status_message)
    layout.addStretch(1)

    window._update_source_mode_ui()
    return panel
