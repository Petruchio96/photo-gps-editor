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

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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
        self.resize(1200, 750)

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

        # Build the UI
        self._build_ui()

    def _build_ui(self) -> None:
        """
        Create and arrange all UI elements.
        """

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        outer_layout = QVBoxLayout(central_widget)

        self.select_button = QPushButton("Select Photos")
        self.select_button.clicked.connect(self.select_photos)

        # Main content area:
        # left side = thumbnail browser
        # right side = metadata / editing panel
        content_layout = QHBoxLayout()

        self.list_widget = QListWidget()

        # Use icon mode so the list widget behaves like a simple thumbnail grid.
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(128, 128))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(12)

        # Extended selection allows:
        # 1. single click selection
        # 2. Ctrl click multi selection
        # 3. Shift click range selection
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)

        # Whenever the selection changes, update the right side panel so it
        # reflects either one selected file or a multi selection state.
        self.list_widget.itemSelectionChanged.connect(self.update_details_panel)

        content_layout.addWidget(self.list_widget, 3)
        content_layout.addWidget(self._build_right_panel(), 2)

        outer_layout.addWidget(self.select_button)
        outer_layout.addLayout(content_layout)

    def _build_right_panel(self) -> QWidget:
        """
        Create the right side panel.

        This panel is where the user will:
        1. inspect current GPS details
        2. enter new latitude / longitude values
        3. later apply those values to one or many selected files
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        selection_group = QGroupBox("Selection")
        selection_form = QFormLayout(selection_group)

        # Read only box showing how many files are currently selected.
        self.selection_summary = QLineEdit()
        self.selection_summary.setReadOnly(True)
        self.selection_summary.setText("No files selected")

        # Read only box showing the current GPS for a single selected image.
        # This will be disabled when multiple images are selected.
        self.current_gps_display = QLineEdit()
        self.current_gps_display.setReadOnly(True)
        self.current_gps_display.setText("No file selected")

        selection_form.addRow("Selected:", self.selection_summary)
        selection_form.addRow("Current GPS:", self.current_gps_display)

        edit_group = QGroupBox("New GPS Coordinates")
        edit_form = QFormLayout(edit_group)

        # These fields will later be used for applying new coordinates to the
        # selected file or files.
        self.latitude_input = QLineEdit()
        self.longitude_input = QLineEdit()

        self.latitude_input.setPlaceholderText("Latitude")
        self.longitude_input.setPlaceholderText("Longitude")

        edit_form.addRow("Latitude:", self.latitude_input)
        edit_form.addRow("Longitude:", self.longitude_input)

        # The apply button is visible now so the shape of the final UI is
        # already in place. We will wire it up in the next implementation step.
        self.apply_button = QPushButton("Apply to Selected")
        self.apply_button.setEnabled(False)

        # Optional read only notes area.
        # This gives us a clean place to explain what the current selection
        # means without cluttering the thumbnail area.
        self.selection_notes = QTextEdit()
        self.selection_notes.setReadOnly(True)
        self.selection_notes.setPlainText(
            "Select one photo to view its current GPS.\n"
            "Select multiple photos to prepare a batch update."
        )

        layout.addWidget(selection_group)
        layout.addWidget(edit_group)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.selection_notes)

        return panel

    def select_photos(self) -> None:
        """
        Open a file dialog and allow user to select one or more images.
        """

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Photos",
            "",
            # Qt file filters on Linux are case-sensitive, so we include both
            # lowercase and uppercase versions of each supported extension.
            "Images (*.jpg *.JPG *.jpeg *.JPEG *.cr2 *.CR2 *.cr3 *.CR3 *.dng *.DNG)",
        )

        if not file_paths:
            return

        self.selected_paths = [Path(p) for p in file_paths]

        self.populate_list()

    def populate_list(self) -> None:
        """
        Fill the list widget with selected files.

        For now:
        1. shows thumbnail icon
        2. shows filename
        3. shows a simple GPS / No GPS status line
        """

        self.list_widget.clear()

        for path in self.selected_paths:
            info = self.loader.load_photo_info(path)
            icon = self.thumbnail_loader.load_icon(path)

            if info.current_latitude is not None and info.current_longitude is not None:
                text = (
                    f"{path.name}\n"
                    f"GPS: {info.current_latitude:.6f}, {info.current_longitude:.6f}"
                )
            else:
                text = f"{path.name}\nNo GPS"

            item = QListWidgetItem(icon, text)

            # Store the full path on the item so later features like detail
            # panels, context menus, and write operations can find the real file
            # without trying to reconstruct it from the display text.
            item.setData(256, str(path))

            self.list_widget.addItem(item)

        # Clear and refresh the right side panel after loading a new batch so
        # stale information from a previous selection is not left on screen.
        self.update_details_panel()

    def update_details_panel(self) -> None:
        """
        Update the right side panel based on the current selection state.

        Behavior:
        1. No selection:
           show neutral placeholders
        2. One selection:
           show the current GPS for that file
        3. Multiple selection:
           grey out current GPS and show a multi selection message
        """
        selected_items = self.list_widget.selectedItems()
        selected_count = len(selected_items)

        if selected_count == 0:
            self.selection_summary.setText("No files selected")
            self.current_gps_display.setEnabled(True)
            self.current_gps_display.setText("No file selected")
            self.apply_button.setEnabled(False)
            self.selection_notes.setPlainText(
                "Select one photo to view its current GPS.\n"
                "Select multiple photos to prepare a batch update."
            )
            return

        if selected_count == 1:
            selected_path = Path(selected_items[0].data(256))
            info = self.loader.load_photo_info(selected_path)

            self.selection_summary.setText("1 file")

            # Re-enable the current GPS display because a single selection has
            # one clear value we can show to the user.
            self.current_gps_display.setEnabled(True)

            if info.current_latitude is not None and info.current_longitude is not None:
                self.current_gps_display.setText(
                    f"{info.current_latitude:.6f}, {info.current_longitude:.6f}"
                )
            else:
                self.current_gps_display.setText("No GPS")

            self.apply_button.setEnabled(True)
            self.selection_notes.setPlainText(
                f"Selected file:\n{selected_path.name}\n\n"
                "You can inspect the current GPS and prepare new coordinates."
            )
            return

        self.selection_summary.setText(f"{selected_count} files")

        # Disable the current GPS display for multi selection because there is
        # no single authoritative value to show when multiple files are selected.
        self.current_gps_display.setEnabled(False)
        self.current_gps_display.setText("(Multiple selection)")

        self.apply_button.setEnabled(True)
        self.selection_notes.setPlainText(
            "Multiple files selected.\n\n"
            "Enter new latitude and longitude values to apply the same GPS "
            "coordinates to all selected files."
        )