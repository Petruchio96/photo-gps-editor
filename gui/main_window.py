"""
Main application window.

This is the first real GUI for the project.

What this window does:
1. Allows user to select one or more photos
2. Displays selected photos in a grid (list widget)
3. Shows basic information about selected items

This will evolve into the full app UI later.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.coordinates import validate_coordinates
from core.exiftool_wrapper import ExifToolWrapper
from core.photo_loader import PhotoLoader
from core.thumbnail_loader import ThumbnailLoader


class MainWindow(QMainWindow):
    """
    Main application window.

    This class is responsible for:
    1. building the UI
    2. handling user actions
    3. coordinating backend calls
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Photo GPS Editor")
        self.resize(1500, 920)
        self.setMinimumSize(1280, 820)

        # Initialize backend components
        self.exiftool = ExifToolWrapper()
        self.loader = PhotoLoader(self.exiftool)

        # Thumbnail creation is kept separate from metadata loading so the UI
        # can stay focused on presentation while backend code stays focused on
        # file metadata.
        self.thumbnail_loader = ThumbnailLoader(thumbnail_size=128)

        # Store selected file paths so the rest of the window can work with the
        # currently loaded files without having to ask the list widget for raw
        # string values.
        self.selected_paths: list[Path] = []
        self.source_photo_path: Path | None = None
        self.source_latitude: float | None = None
        self.source_longitude: float | None = None

        # Build the UI
        self._build_ui()
        self._build_menu_bar()
        self._apply_window_style()
        self._update_selection_metrics()

    def _build_ui(self) -> None:
        """
        Create and arrange all UI elements.
        """

        central_widget = QWidget()
        central_widget.setObjectName("centralSurface")
        self.setCentralWidget(central_widget)

        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(18)

        self.select_button = QPushButton("Open Photos")
        self.select_button.clicked.connect(self.select_photos)

        self.loaded_count_badge = QLabel("0 loaded")
        self.loaded_count_badge.setObjectName("metricBadge")

        self.selection_count_badge = QLabel("No selection")
        self.selection_count_badge.setObjectName("metricBadgeMuted")

        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        title_label = QLabel("Photo GPS Editor")
        title_label.setObjectName("windowTitle")

        subtitle_label = QLabel(
            "Review thumbnails, inspect coordinates, and write precise GPS metadata with a desktop-grade workflow."
        )
        subtitle_label.setObjectName("windowSubtitle")
        subtitle_label.setWordWrap(True)

        header_text_layout.addWidget(title_label)
        header_text_layout.addWidget(subtitle_label)

        header_actions_layout = QHBoxLayout()
        header_actions_layout.setSpacing(10)
        header_actions_layout.addWidget(self.loaded_count_badge)
        header_actions_layout.addWidget(self.selection_count_badge)
        header_actions_layout.addWidget(self.select_button)

        header_layout.addLayout(header_text_layout, 1)
        header_layout.addLayout(header_actions_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_browser_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([860, 420])

        outer_layout.addLayout(header_layout)
        outer_layout.addWidget(splitter, 1)

    def _build_browser_panel(self) -> QWidget:
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

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("thumbnailGrid")

        # Use icon mode so the list widget behaves like a simple thumbnail grid.
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(128, 128))
        self.list_widget.setGridSize(QSize(170, 190))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(12)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setWordWrap(True)

        # Extended selection allows:
        # 1. single click selection
        # 2. Ctrl click multi selection
        # 3. Shift click range selection
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)

        # Whenever the selection changes, update the right side panel so it
        # reflects either one selected file or a multi selection state.
        self.list_widget.itemSelectionChanged.connect(self.update_details_panel)

        # Use a custom context menu so right click actions can be added to
        # individual thumbnail items without cluttering the main UI.
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.browser_hint = QLabel(
            "No photos loaded yet. Use Open Photos to populate the grid."
        )
        self.browser_hint.setObjectName("browserHint")
        self.browser_hint.setWordWrap(True)

        layout.addWidget(section_heading)
        layout.addWidget(section_note)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.browser_hint)

        return panel

    def _build_right_panel(self) -> QWidget:
        """
        Create the right side panel.

        This panel is where the user will:
        1. choose the source GPS values
        2. review the destination files
        3. apply those values to one or many selected files
        """
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)

        # Add a little breathing room so the right panel feels less cramped.
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        inspector_title = QLabel("GPS Editor")
        inspector_title.setObjectName("sectionTitle")

        inspector_note = QLabel(
            "Choose the coordinates to apply, review the destination files, and then write metadata with a clear overwrite check."
        )
        inspector_note.setObjectName("sectionNote")
        inspector_note.setWordWrap(True)

        source_group = QGroupBox("GPS Source")
        source_layout = QVBoxLayout(source_group)
        source_layout.setSpacing(10)

        self.photo_source_radio = QRadioButton("Use Selected Photo")
        self.manual_source_radio = QRadioButton("Enter Coordinates Manually")
        self.photo_source_radio.setChecked(True)

        self.source_mode_group = QButtonGroup(self)
        self.source_mode_group.addButton(self.photo_source_radio)
        self.source_mode_group.addButton(self.manual_source_radio)
        self.photo_source_radio.toggled.connect(self._update_source_mode_ui)

        source_mode_layout = QVBoxLayout()
        source_mode_layout.setSpacing(6)
        source_mode_layout.addWidget(self.photo_source_radio)
        source_mode_layout.addWidget(self.manual_source_radio)

        self.source_preview_stack = QStackedWidget()

        empty_source_widget = QWidget()
        empty_source_layout = QVBoxLayout(empty_source_widget)
        empty_source_layout.setContentsMargins(0, 0, 0, 0)
        empty_source_layout.setSpacing(8)

        empty_source_label = QLabel(
            "No source photo selected yet. Pick a single photo in the library, then use the button below to lock it in as the GPS source."
        )
        empty_source_label.setObjectName("sourceHint")
        empty_source_label.setWordWrap(True)
        empty_source_layout.addWidget(empty_source_label)

        source_preview_widget = QWidget()
        source_preview_layout = QVBoxLayout(source_preview_widget)
        source_preview_layout.setContentsMargins(0, 0, 0, 0)
        source_preview_layout.setSpacing(8)

        self.source_thumbnail = QLabel()
        self.source_thumbnail.setObjectName("sourceThumbnail")
        self.source_thumbnail.setFixedSize(180, 180)
        self.source_thumbnail.setAlignment(Qt.AlignCenter)

        self.source_file_label = QLabel("No source photo selected")
        self.source_file_label.setObjectName("sourceFileLabel")
        self.source_file_label.setWordWrap(True)

        source_preview_layout.addWidget(self.source_file_label)
        source_preview_layout.addWidget(self.source_thumbnail, alignment=Qt.AlignCenter)

        self.source_preview_stack.addWidget(empty_source_widget)
        self.source_preview_stack.addWidget(source_preview_widget)

        self.set_source_button = QPushButton("Use Selected Photo as GPS Source")
        self.set_source_button.setEnabled(False)
        self.set_source_button.clicked.connect(self.set_selected_photo_as_source)

        self.clear_source_button = QPushButton("Clear Source")
        self.clear_source_button.setEnabled(False)
        self.clear_source_button.clicked.connect(self.clear_source_photo)

        photo_source_panel = QWidget()
        photo_source_layout = QVBoxLayout(photo_source_panel)
        photo_source_layout.setContentsMargins(0, 0, 0, 0)
        photo_source_layout.setSpacing(10)
        photo_source_layout.addWidget(self.source_preview_stack)

        source_button_row = QHBoxLayout()
        source_button_row.setSpacing(10)
        source_button_row.addWidget(self.set_source_button)
        source_button_row.addWidget(self.clear_source_button)
        photo_source_layout.addLayout(source_button_row)

        self.manual_source_panel = QWidget()
        manual_source_layout = QFormLayout(self.manual_source_panel)
        manual_source_layout.setContentsMargins(0, 0, 0, 0)
        manual_source_layout.setSpacing(10)

        self.latitude_input = QLineEdit()
        self.longitude_input = QLineEdit()
        self.latitude_input.setPlaceholderText("e.g. 40.486325")
        self.longitude_input.setPlaceholderText("e.g. -111.813415")
        self.latitude_input.editingFinished.connect(self.validate_latitude_field)
        self.longitude_input.editingFinished.connect(self.validate_longitude_field)
        self.latitude_input.textChanged.connect(self._handle_manual_coordinate_change)
        self.longitude_input.textChanged.connect(self._handle_manual_coordinate_change)

        self.paste_coordinates_button = QPushButton("Paste Coordinates")
        self.paste_coordinates_button.clicked.connect(
            self.paste_coordinates_from_clipboard
        )

        manual_source_layout.addRow("Latitude:", self.latitude_input)
        manual_source_layout.addRow("Longitude:", self.longitude_input)
        manual_source_layout.addRow("", self.paste_coordinates_button)

        self.source_mode_stack = QStackedWidget()
        self.source_mode_stack.addWidget(photo_source_panel)
        self.source_mode_stack.addWidget(self.manual_source_panel)

        self.active_source_coordinates = QLabel("Coordinates to Apply: Not set")
        self.active_source_coordinates.setObjectName("sourceSummary")
        self.active_source_coordinates.setWordWrap(True)

        source_layout.addLayout(source_mode_layout)
        source_layout.addWidget(self.source_mode_stack)
        source_layout.addWidget(self.active_source_coordinates)

        self.destination_list = QListWidget()
        self.destination_list.setObjectName("destinationList")
        self.destination_list.setSelectionMode(QListWidget.NoSelection)
        self.destination_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.destination_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.destination_list.setMaximumHeight(124)
        self.destination_list.setMinimumHeight(124)

        self.destination_title_label = QLabel("Destination Files")
        self.destination_title_label.setObjectName("sectionTitle")

        # The apply button is the primary action in the panel, so give it a bit
        # more visual weight without over-styling the UI.
        self.apply_button = QPushButton("Apply GPS to Destination Files")
        self.apply_button.setEnabled(False)
        self.apply_button.setMinimumHeight(34)
        self.apply_button.clicked.connect(self.apply_coordinates_to_selected)

        layout.addWidget(inspector_title)
        layout.addWidget(inspector_note)
        layout.addWidget(source_group)
        layout.addWidget(self.destination_title_label)
        layout.addWidget(self.destination_list)
        layout.addWidget(self.apply_button)
        layout.addStretch(1)

        self._update_source_mode_ui()
        return panel

    def _build_menu_bar(self) -> None:
        """
        Create a lightweight desktop menu for common actions.
        """
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("Open Photos...", self)
        open_action.triggered.connect(self.select_photos)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _apply_window_style(self) -> None:
        """
        Apply a consistent Fusion-based stylesheet so the app feels polished
        across Linux and Windows instead of inheriting platform defaults.
        """
        self.setStyleSheet(
            """
            QMainWindow, QWidget#centralSurface {
                background: #eef3f8;
                color: #162131;
            }
            QMenuBar {
                background: #f6f9fc;
                border-bottom: 1px solid #d6dfe8;
                padding: 4px 8px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QMenuBar::item:selected {
                background: #dde8f3;
            }
            QMenu {
                background: #ffffff;
                border: 1px solid #d4dde7;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #e4eef9;
            }
            QFrame#panel {
                background: #fbfdff;
                border: 1px solid #d6dfe8;
                border-radius: 18px;
            }
            QLabel#windowTitle {
                font-size: 28px;
                font-weight: 700;
                color: #102033;
            }
            QLabel#windowSubtitle {
                font-size: 13px;
                color: #556579;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 700;
                color: #112033;
            }
            QLabel#sourceFileLabel {
                font-size: 13px;
                font-weight: 700;
                color: #162131;
                min-height: 22px;
            }
            QLabel#sourceSummary {
                color: #26425f;
                background: #eef4fb;
                border: 1px solid #d8e4f0;
                border-radius: 10px;
                padding: 10px 12px;
                font-weight: 600;
            }
            QLabel#destinationSummary {
                color: #28425d;
                font-weight: 600;
            }
            QLabel#sectionNote {
                color: #5a697c;
                font-size: 12px;
                line-height: 1.4em;
            }
            QLabel#sourceHint {
                color: #617084;
                background: #f5f8fb;
                border: 1px dashed #ccd7e2;
                border-radius: 12px;
                padding: 12px 14px;
            }
            QLabel#metricBadge, QLabel#metricBadgeMuted {
                padding: 8px 12px;
                border-radius: 14px;
                font-weight: 600;
            }
            QLabel#metricBadge {
                background: #dcecff;
                color: #0f4d91;
                border: 1px solid #bfdbff;
            }
            QLabel#metricBadgeMuted {
                background: #edf2f7;
                color: #516174;
                border: 1px solid #dbe3eb;
            }
            QPushButton {
                background: #ffffff;
                color: #102033;
                border: 1px solid #cad6e2;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f3f8fe;
                border-color: #a9bfd7;
            }
            QPushButton:pressed {
                background: #e7f0fa;
            }
            QPushButton:disabled {
                color: #8c9aa8;
                background: #f5f7f9;
                border-color: #d7dee5;
            }
            QPushButton#primaryButton {
                background: #1f6feb;
                color: white;
                border-color: #1f6feb;
            }
            QPushButton#primaryButton:hover {
                background: #165dc5;
                border-color: #165dc5;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d8e1ea;
                border-radius: 14px;
                margin-top: 12px;
                padding: 14px 16px 16px 16px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #31445a;
            }
            QLineEdit {
                min-height: 36px;
                padding: 0 12px;
                background: #ffffff;
                border: 1px solid #cdd8e3;
                border-radius: 10px;
                selection-background-color: #c8ddff;
            }
            QLineEdit:focus {
                border: 1px solid #1f6feb;
            }
            QLabel#sourceThumbnail {
                background: #f7fafc;
                border: 1px solid #d8e1ea;
                border-radius: 14px;
                padding: 10px;
            }
            QRadioButton {
                color: #23384f;
                spacing: 8px;
                font-weight: 600;
            }
            QListWidget#destinationList {
                background: #ffffff;
                border: 1px solid #d8e1ea;
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }
            QListWidget#thumbnailGrid {
                background: #ffffff;
                border: 1px solid #d8e1ea;
                border-radius: 16px;
                padding: 12px;
                outline: none;
            }
            QListWidget#thumbnailGrid::item {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 14px;
                padding: 8px;
                margin: 4px;
            }
            QListWidget#thumbnailGrid::item:hover {
                background: #f4f8fc;
                border-color: #d5e2ef;
            }
            QListWidget#thumbnailGrid::item:selected {
                background: #dcebff;
                border-color: #8cb7f0;
                color: #0b2441;
            }
            QLabel#browserHint {
                color: #617084;
                background: #f5f8fb;
                border: 1px dashed #ccd7e2;
                border-radius: 12px;
                padding: 12px 14px;
            }
            QLabel#statusCard {
                border-radius: 14px;
                padding: 14px 16px;
                font-weight: 600;
                border: 1px solid #d6e1ec;
                background: #edf4fb;
                color: #21476b;
            }
            QLabel#statusCard[tone="success"] {
                background: #edf8f1;
                color: #1d6a3d;
                border-color: #cfe9d8;
            }
            QLabel#statusCard[tone="error"] {
                background: #fff1f1;
                color: #9d2b2b;
                border-color: #efc8c8;
            }
            QLabel#statusCard[tone="info"] {
                background: #edf4fb;
                color: #21476b;
                border-color: #d6e1ec;
            }
            QSplitter::handle {
                background: transparent;
                width: 10px;
            }
            """
        )
        self.apply_button.setObjectName("primaryButton")
        self._update_apply_button_text()

    def _update_source_mode_ui(self) -> None:
        """
        Switch the source editor between photo mode and manual coordinate mode.
        """
        using_photo_source = self.photo_source_radio.isChecked()
        self.source_mode_stack.setCurrentIndex(0 if using_photo_source else 1)
        self._update_apply_button_text()
        self._update_source_summary()
        self.update_details_panel()

    def _update_selection_metrics(self) -> None:
        """
        Keep the header badges in sync with the current list and selection state.
        """
        loaded_count = len(self.selected_paths)
        self.loaded_count_badge.setText(
            f"{loaded_count} loaded" if loaded_count else "0 loaded"
        )

        selected_count = len(self.list_widget.selectedItems())
        if selected_count == 0:
            self.selection_count_badge.setText("No selection")
        elif selected_count == 1:
            self.selection_count_badge.setText("1 selected")
        else:
            self.selection_count_badge.setText(f"{selected_count} selected")

        if loaded_count == 0:
            self.browser_hint.setText(
                "No photos loaded yet. Use Open Photos to populate the grid."
            )
        else:
            self.browser_hint.setText(
                "Tip: choose a source on the right, then use Shift or Ctrl to build the destination list on the left."
            )

        if self.photo_source_radio.isChecked() and self.source_photo_path is not None:
            self.selection_count_badge.setText(
                f"{self.selection_count_badge.text()} | source locked"
            )
        elif (
            self.manual_source_radio.isChecked()
            and self._has_valid_manual_coordinates()
        ):
            self.selection_count_badge.setText(
                f"{self.selection_count_badge.text()} | manual source"
            )

    def set_selected_photo_as_source(self) -> None:
        """
        Capture the currently selected single photo as the reusable GPS source.
        """
        selected_items = self.list_widget.selectedItems()

        if len(selected_items) != 1:
            return

        selected_item = selected_items[0]
        latitude = selected_item.data(Qt.UserRole + 1)
        longitude = selected_item.data(Qt.UserRole + 2)

        if latitude is None or longitude is None:
            return

        if self.source_photo_path == Path(selected_item.data(Qt.UserRole)):
            return

        self.source_photo_path = Path(selected_item.data(Qt.UserRole))
        self.source_latitude = latitude
        self.source_longitude = longitude

        self._refresh_source_preview(selected_item)
        self._update_source_summary()
        self._update_selection_metrics()
        selected_item.setSelected(False)
        self.update_details_panel()

    def _refresh_source_preview(self, item: QListWidgetItem | None = None) -> None:
        """
        Refresh the source preview block using the stored source data.
        """
        if (
            self.source_photo_path is None
            or self.source_latitude is None
            or self.source_longitude is None
        ):
            self.source_preview_stack.setCurrentIndex(0)
            self.clear_source_button.setEnabled(False)
            self.source_thumbnail.clear()
            self.source_file_label.setText("No source photo selected")
            return

        if item is None:
            for index in range(self.list_widget.count()):
                candidate = self.list_widget.item(index)
                if candidate.data(Qt.UserRole) == str(self.source_photo_path):
                    item = candidate
                    break

        if item is not None:
            pixmap = item.icon().pixmap(160, 160)
            self.source_thumbnail.setPixmap(pixmap)
        else:
            self.source_thumbnail.clear()

        self.source_file_label.setText(self.source_photo_path.name)
        self.source_preview_stack.setCurrentIndex(1)
        self.clear_source_button.setEnabled(True)

    def _handle_manual_coordinate_change(self) -> None:
        """
        Keep the active source summary in sync as manual coordinates are edited.
        """
        self._update_source_summary()
        self._update_selection_metrics()
        self.update_details_panel()

    def clear_source_photo(self) -> None:
        """
        Clear the locked photo source and return the panel to its empty state.
        """
        self.source_photo_path = None
        self.source_latitude = None
        self.source_longitude = None
        self._refresh_source_preview()
        self._update_source_summary()
        self._update_selection_metrics()
        self.update_details_panel()

    def _update_apply_button_text(self) -> None:
        """
        Make the primary action reflect the active source mode.
        """
        if self.photo_source_radio.isChecked():
            self.apply_button.setText("Apply Photo Source GPS to Destination Files")
        else:
            self.apply_button.setText("Apply Manual GPS to Destination Files")

    def _update_source_summary(self) -> None:
        """
        Show the coordinates that will be used for the apply step.
        """
        coordinates = self._get_active_source_coordinates()

        if self.photo_source_radio.isChecked():
            if self.source_photo_path is None or coordinates is None:
                self.active_source_coordinates.setText("Coordinates to Apply: Not set")
            else:
                self.active_source_coordinates.setText(
                    f"Coordinates to Apply: {coordinates[0]:.6f}, {coordinates[1]:.6f}"
                )
            return

        if coordinates is None:
            self.active_source_coordinates.setText("Coordinates to Apply: Not set")
        else:
            self.active_source_coordinates.setText(
                f"Coordinates to Apply: {coordinates[0]:.6f}, {coordinates[1]:.6f}"
            )

    def _has_valid_manual_coordinates(self) -> bool:
        """
        Return True when both manual coordinate fields contain valid values.
        """
        return self._get_manual_coordinates() is not None

    def _get_manual_coordinates(self) -> tuple[float, float] | None:
        """
        Parse and validate the manual coordinate fields.
        """
        latitude_text = self.latitude_input.text().strip()
        longitude_text = self.longitude_input.text().strip()

        if not latitude_text or not longitude_text:
            return None

        try:
            latitude, longitude = validate_coordinates(latitude_text, longitude_text)
        except ValueError:
            return None

        return latitude, longitude

    def _get_active_source_coordinates(self) -> tuple[float, float] | None:
        """
        Return the coordinates from the currently active source mode.
        """
        if self.photo_source_radio.isChecked():
            if self.source_latitude is None or self.source_longitude is None:
                return None
            return self.source_latitude, self.source_longitude

        return self._get_manual_coordinates()

    def _update_destination_list(self, target_paths: list[Path]) -> None:
        """
        Mirror the current destination selection in the right panel.
        """
        self.destination_list.clear()
        for path in target_paths:
            self.destination_list.addItem(path.name)

    def _get_overwrite_entries(self, target_paths: list[Path]) -> list[str]:
        """
        Return destination files that already contain GPS and would be overwritten.
        """
        overwrite_entries: list[str] = []

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item_path = Path(item.data(Qt.UserRole))
            if item_path not in target_paths:
                continue

            latitude = item.data(Qt.UserRole + 1)
            longitude = item.data(Qt.UserRole + 2)
            if latitude is None or longitude is None:
                continue

            overwrite_entries.append(
                f"{item_path.name} — {latitude:.6f}, {longitude:.6f}"
            )

        return overwrite_entries

    def select_photos(self) -> None:
        """
        Open a file dialog and allow user to select one or more images.
        """

        # Determine a sensible default directory in a cross-platform way.
        # Prefer the user's Pictures folder if it exists, otherwise fall back
        # to the home directory.
        pictures_dir = Path.home() / "Pictures"
        start_dir = pictures_dir if pictures_dir.exists() else Path.home()

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Photos",
            str(start_dir),
            # Qt file filters on Linux are case-sensitive, so we include both
            # lowercase and uppercase versions of each supported extension.
            "Images (*.jpg *.JPG *.jpeg *.JPEG *.cr2 *.CR2 *.cr3 *.CR3 *.dng *.DNG)",
        )

        if not file_paths:
            return

        self.selected_paths = [Path(p) for p in file_paths]

        if self.source_photo_path not in self.selected_paths:
            self.source_photo_path = None
            self.source_latitude = None
            self.source_longitude = None
            self._refresh_source_preview()
            self._update_apply_button_text()

        self.populate_list()

    def populate_list(self) -> None:
        """
        Fill the list widget with selected files.

        Current thumbnail tile content:
        1. thumbnail icon
        2. filename

        GPS details are available through:
        1. hover tooltip
        2. right click context menu
        3. right side detail panel
        """

        self.list_widget.clear()

        for path in self.selected_paths:
            info = self.loader.load_photo_info(path)
            icon = self.thumbnail_loader.load_icon(
                path,
                has_gps=(
                    info.current_latitude is not None
                    and info.current_longitude is not None
                ),
            )

            # Keep thumbnail labels visually clean by showing only the filename.
            item = QListWidgetItem(icon, path.name)

            # Store the full path on the item so later features like detail
            # panels, context menus, and write operations can find the real file
            # without trying to reconstruct it from the display text.
            item.setData(Qt.UserRole, str(path))

            # Store GPS values directly on the item so hover text and the
            # context menu can use them without reloading metadata.
            item.setData(Qt.UserRole + 1, info.current_latitude)
            item.setData(Qt.UserRole + 2, info.current_longitude)

            item.setToolTip(
                self._build_tooltip_text(
                    path.name,
                    info.current_latitude,
                    info.current_longitude,
                )
            )

            self.list_widget.addItem(item)

        # Clear and refresh the right side panel after loading a new batch so
        # stale information from a previous selection is not left on screen.
        self._refresh_source_preview()
        self.update_details_panel()
        self._update_selection_metrics()

    def get_selected_paths(self) -> list[Path]:
        """
        Return the full file paths for the currently selected thumbnail items.

        Returns:
            A list of Path objects for the selected items.
        """
        selected_items = self.list_widget.selectedItems()
        return [Path(item.data(Qt.UserRole)) for item in selected_items]

    def reselect_paths(self, paths_to_select: list[Path]) -> None:
        """
        Re-select items in the thumbnail grid after the list has been rebuilt.

        Why this exists:
            After writing metadata, we rebuild the thumbnail list so tooltips,
            badges, and current GPS values all refresh from disk. Rebuilding the
            list clears selection, so this helper restores the user's selection.

        Args:
            paths_to_select:
                Paths that should be re-selected if present in the list.
        """
        wanted = {str(path) for path in paths_to_select}

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item_path = item.data(Qt.UserRole)

            if item_path in wanted:
                item.setSelected(True)

        self._update_selection_metrics()

    def _build_tooltip_text(
        self,
        filename: str,
        latitude: float | None,
        longitude: float | None,
    ) -> str:
        """
        Build hover tooltip text for a thumbnail item.

        Args:
            filename:
                Name of the file being displayed.
            latitude:
                GPS latitude if present, otherwise None.
            longitude:
                GPS longitude if present, otherwise None.

        Returns:
            Human-readable tooltip text for the thumbnail.
        """
        if latitude is not None and longitude is not None:
            return f"{filename}\nGPS: {latitude:.6f}, {longitude:.6f}"

        return f"{filename}\nNo GPS"

    def show_context_menu(self, position) -> None:
        """
        Show the right click menu for the thumbnail under the mouse.

        Current action:
        1. Copy GPS Coordinates

        The action is enabled only when the clicked file has GPS metadata.
        """
        item = self.list_widget.itemAt(position)

        if item is None:
            return

        latitude = item.data(Qt.UserRole + 1)
        longitude = item.data(Qt.UserRole + 2)

        menu = QMenu(self)

        copy_action = QAction("Copy GPS Coordinates", self)
        copy_action.setEnabled(latitude is not None and longitude is not None)
        copy_action.triggered.connect(
            lambda: self.copy_gps_coordinates(latitude, longitude)
        )

        menu.addAction(copy_action)
        menu.exec(self.list_widget.viewport().mapToGlobal(position))

    def copy_gps_coordinates(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> None:
        """
        Copy GPS coordinates to the clipboard in decimal format.

        Example copied text:
            40.486325, -111.813415
        """
        if latitude is None or longitude is None:
            return

        QApplication.clipboard().setText(f"{latitude:.6f}, {longitude:.6f}")

    def paste_coordinates_from_clipboard(self) -> None:
        """
        Read a combined coordinate string from the clipboard and split it into
        the latitude and longitude input fields.

        Expected format:
            40.486325, -111.813415
        """
        clipboard_text = QApplication.clipboard().text().strip()
        parsed = self.parse_coordinate_text(clipboard_text)

        if parsed is None:
            self._set_status_message(
                "Clipboard text could not be parsed as coordinates. Expected format: 40.486325, -111.813415",
                "error",
            )
            return

        latitude, longitude = parsed
        self.manual_source_radio.setChecked(True)
        self.latitude_input.setText(latitude)
        self.longitude_input.setText(longitude)
        self.set_input_error_state(self.latitude_input, False)
        self.set_input_error_state(self.longitude_input, False)
        self._update_source_summary()

    def parse_coordinate_text(self, text: str) -> tuple[str, str] | None:
        """
        Parse a combined coordinate string into separate latitude and longitude
        strings for the two input fields.

        Supported format:
            latitude, longitude

        Returns:
            A tuple of string values if parsing succeeds, otherwise None.
        """
        parts = [part.strip() for part in text.split(",")]

        if len(parts) != 2:
            return None

        try:
            float(parts[0])
            float(parts[1])
        except ValueError:
            return None

        return parts[0], parts[1]

    def set_input_error_state(self, field: QLineEdit, has_error: bool) -> None:
        """
        Visually mark a coordinate input field as either valid or invalid.

        Why this exists:
        1. Validation messages in the status field are helpful
        2. Highlighting the actual bad field makes the problem easier to spot
        3. A tooltip gives the user the valid numeric range when a field is invalid

        Args:
            field:
                The QLineEdit to style
            has_error:
                True to show an error state, False to return to normal styling
        """
        if has_error:
            field.setStyleSheet(
                "QLineEdit {"
                "border: 1px solid #c62828;"
                "background-color: #fff5f5;"
                "}"
            )

            if field is self.latitude_input:
                field.setToolTip("Invalid latitude. Enter a number between -90 and 90")
            elif field is self.longitude_input:
                field.setToolTip("Invalid longitude. Enter a number between -180 and 180")
        else:
            field.setStyleSheet("")
            field.setToolTip("")

    def validate_latitude_field(self) -> None:
        """
        Re-check the latitude field when editing finishes.

        Behavior:
        1. Empty field stays neutral until Apply is clicked
        2. Valid value clears any red error styling
        3. Invalid value keeps or applies red error styling
        """
        text = self.latitude_input.text().strip()

        if not text:
            self.set_input_error_state(self.latitude_input, False)
            return

        try:
            value = float(text)
            self.set_input_error_state(
                self.latitude_input,
                not (-90 <= value <= 90),
            )
        except ValueError:
            self.set_input_error_state(self.latitude_input, True)

    def validate_longitude_field(self) -> None:
        """
        Re-check the longitude field when editing finishes.

        Behavior:
        1. Empty field stays neutral until Apply is clicked
        2. Valid value clears any red error styling
        3. Invalid value keeps or applies red error styling
        """
        text = self.longitude_input.text().strip()

        if not text:
            self.set_input_error_state(self.longitude_input, False)
            return

        try:
            value = float(text)
            self.set_input_error_state(
                self.longitude_input,
                not (-180 <= value <= 180),
            )
        except ValueError:
            self.set_input_error_state(self.longitude_input, True)

    def apply_coordinates_to_selected(self) -> None:
        """
        Validate the active source coordinates and write them to selected files.

        Workflow:
        1. Make sure one or more destination files are selected
        2. Validate the active source coordinates
        3. Write metadata to each selected file
        4. Refresh the thumbnail list so GPS values, tooltips, and badges update
        5. Restore selection and show a summary message
        """
        target_paths = self.get_selected_paths()

        if not target_paths:
            return

        if self.photo_source_radio.isChecked() and self.source_photo_path in target_paths:
            return

        if self.manual_source_radio.isChecked():
            self.validate_latitude_field()
            self.validate_longitude_field()

        coordinates = self._get_active_source_coordinates()
        if coordinates is None:
            return

        latitude, longitude = coordinates
        overwrite_entries = self._get_overwrite_entries(target_paths)

        if overwrite_entries:
            confirmation_dialog = QMessageBox(self)
            confirmation_dialog.setIcon(QMessageBox.Warning)
            confirmation_dialog.setWindowTitle("Existing GPS Will Change")
            confirmation_dialog.setText(
                f"{len(overwrite_entries)} destination file(s) already contain GPS and will be overwritten."
            )
            confirmation_dialog.setInformativeText(
                "Review the files below and choose OK to continue or Cancel to stop."
            )
            confirmation_dialog.setDetailedText("\n".join(overwrite_entries))
            confirmation_dialog.setStandardButtons(
                QMessageBox.Ok | QMessageBox.Cancel
            )
            confirmation_dialog.setDefaultButton(QMessageBox.Cancel)

            if confirmation_dialog.exec() != QMessageBox.Ok:
                return

        success_count = 0
        failed_paths: list[str] = []

        for path in target_paths:
            try:
                self.exiftool.write_gps(path, latitude, longitude)
                success_count += 1
            except Exception as exc:
                failed_paths.append(f"{path.name}: {exc}")

        self.populate_list()
        self.reselect_paths(target_paths)
        self.update_details_panel()

    def update_details_panel(self) -> None:
        """
        Update the right side panel based on the current selection state.
        """
        target_paths = self.get_selected_paths()
        selected_count = len(target_paths)
        self._update_selection_metrics()
        self._update_source_summary()
        self._update_destination_list(target_paths)

        selected_items = self.list_widget.selectedItems()
        can_set_source = False
        if len(selected_items) == 1:
            selected_path = Path(selected_items[0].data(Qt.UserRole))
            latitude = selected_items[0].data(Qt.UserRole + 1)
            longitude = selected_items[0].data(Qt.UserRole + 2)
            can_set_source = (
                latitude is not None
                and longitude is not None
                and selected_path != self.source_photo_path
            )

        self.set_source_button.setEnabled(
            self.photo_source_radio.isChecked() and can_set_source
        )
        self.clear_source_button.setEnabled(self.source_photo_path is not None)

        if selected_count == 0:
            self.apply_button.setEnabled(False)
            return

        if self.photo_source_radio.isChecked() and self.source_photo_path in target_paths:
            self.apply_button.setEnabled(False)
            return

        source_ready = self._get_active_source_coordinates() is not None
        self.apply_button.setEnabled(source_ready)
