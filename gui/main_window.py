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
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QTextEdit,
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

        # Use a custom context menu so right click actions can be added to
        # individual thumbnail items without cluttering the main UI.
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

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

        # This button gives the user an obvious way to copy the current GPS from
        # a single selected image without needing to use the thumbnail context menu.
        self.copy_current_gps_button = QPushButton("Copy Current GPS")
        self.copy_current_gps_button.setEnabled(False)
        self.copy_current_gps_button.clicked.connect(self.copy_current_gps_from_panel)

        selection_form.addRow("", self.copy_current_gps_button)

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

        # This button reads a combined "latitude, longitude" value from the
        # clipboard and splits it into the two edit fields automatically.
        self.paste_coordinates_button = QPushButton("Paste Coordinates")
        self.paste_coordinates_button.clicked.connect(self.paste_coordinates_from_clipboard)

        edit_form.addRow("", self.paste_coordinates_button)

        # The apply button is visible now so the shape of the final UI is
        # already in place. We will wire it up in the next implementation step.
        self.apply_button = QPushButton("Apply to Selected")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_coordinates_to_selected)

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
        self.update_details_panel()

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

    def copy_current_gps_from_panel(self) -> None:
        """
        Copy the current GPS from the right side panel when exactly one file is
        selected and that file has GPS metadata.
        """
        selected_items = self.list_widget.selectedItems()

        if len(selected_items) != 1:
            return

        latitude = selected_items[0].data(Qt.UserRole + 1)
        longitude = selected_items[0].data(Qt.UserRole + 2)

        self.copy_gps_coordinates(latitude, longitude)

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
            self.selection_notes.setPlainText(
                "Clipboard text could not be parsed as coordinates.\n\n"
                "Expected format:\n"
                "40.486325, -111.813415"
            )
            return

        latitude, longitude = parsed
        self.latitude_input.setText(latitude)
        self.longitude_input.setText(longitude)

        self.selection_notes.setPlainText(
            "Coordinates pasted from clipboard.\n\n"
            f"Latitude: {latitude}\n"
            f"Longitude: {longitude}"
        )

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

    def apply_coordinates_to_selected(self) -> None:
        """
        Validate the coordinate inputs and write them to all selected files.

        Workflow:
        1. Make sure one or more files are selected
        2. Validate latitude and longitude
        3. Write metadata to each selected file
        4. Refresh the thumbnail list so GPS values, tooltips, and badges update
        5. Restore selection and show a summary message
        """
        target_paths = self.get_selected_paths()

        if not target_paths:
            self.selection_notes.setPlainText(
                "No files selected.\n\n"
                "Select one or more photos before applying coordinates."
            )
            return

        try:
            latitude, longitude = validate_coordinates(
                self.latitude_input.text().strip(),
                self.longitude_input.text().strip(),
            )
        except ValueError as exc:
            self.selection_notes.setPlainText(
                "Coordinate validation failed.\n\n"
                f"{exc}"
            )
            return

        success_count = 0
        failed_paths: list[str] = []

        for path in target_paths:
            try:
                self.exiftool.write_gps(path, latitude, longitude)
                success_count += 1
            except Exception as exc:
                failed_paths.append(f"{path.name}: {exc}")

        # Rebuild the list so every visual element that depends on GPS metadata
        # is refreshed from disk.
        self.populate_list()
        self.reselect_paths(target_paths)
        self.update_details_panel()

        if failed_paths:
            failure_text = "\n".join(failed_paths)
            self.selection_notes.setPlainText(
                "Apply completed with some failures.\n\n"
                f"Successful writes: {success_count}\n"
                f"Failed writes: {len(failed_paths)}\n\n"
                f"{failure_text}"
            )
            return

        self.selection_notes.setPlainText(
            "Coordinates applied successfully.\n\n"
            f"Updated files: {success_count}\n"
            f"Latitude: {latitude:.6f}\n"
            f"Longitude: {longitude:.6f}"
        )

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
            self.copy_current_gps_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.selection_notes.setPlainText(
                "Select one photo to view its current GPS.\n"
                "Select multiple photos to prepare a batch update."
            )
            return

        if selected_count == 1:
            selected_path = Path(selected_items[0].data(Qt.UserRole))
            info = self.loader.load_photo_info(selected_path)

            self.selection_summary.setText("1 file")

            # Re-enable the current GPS display because a single selection has
            # one clear value we can show to the user.
            self.current_gps_display.setEnabled(True)

            if info.current_latitude is not None and info.current_longitude is not None:
                self.current_gps_display.setText(
                    f"{info.current_latitude:.6f}, {info.current_longitude:.6f}"
                )
                self.copy_current_gps_button.setEnabled(True)
            else:
                self.current_gps_display.setText("No GPS")
                self.copy_current_gps_button.setEnabled(False)

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
        self.copy_current_gps_button.setEnabled(False)

        self.apply_button.setEnabled(True)
        self.selection_notes.setPlainText(
            "Multiple files selected.\n\n"
            "Enter new latitude and longitude values to apply the same GPS "
            "coordinates to all selected files."
        )