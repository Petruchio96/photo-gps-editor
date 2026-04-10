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

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.exiftool_wrapper import ExifToolWrapper
from core.photo_loader import PhotoLoader
from core.thumbnail_loader import ThumbnailLoader
from gui.services.coordinate_text import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
    parse_manual_coordinates,
)
from gui.services.selection import get_destination_paths, get_overwrite_entries
from gui.services.thumbnail_items import build_tooltip_text, reselect_paths
from gui.styles import APP_STYLESHEET
from gui.widgets.browser_panel import build_browser_panel
from gui.widgets.editor_panel import build_editor_panel


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
        self._is_splitting_manual_coordinates = False

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

        self.select_button = QPushButton("Select Photos")
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

        header_layout.addLayout(header_text_layout, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(build_browser_panel(self))
        splitter.addWidget(build_editor_panel(self))
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([860, 420])

        outer_layout.addLayout(header_layout)
        outer_layout.addWidget(splitter, 1)

    def _build_menu_bar(self) -> None:
        """
        Create a lightweight desktop menu for common actions.
        """
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("Select Photos...", self)
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
        self.setStyleSheet(APP_STYLESHEET)
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
        Keep the destination badges in sync with the current list and selection state.
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
                "No destination photos loaded yet. Use Select Photos to populate the grid."
            )
        else:
            self.browser_hint.setText(
                "Tip: choose a source on the right, then use Shift or Ctrl to build the destination list on the left."
            )

        self.select_all_button.setEnabled(loaded_count > 0)
        self.clear_selection_button.setEnabled(selected_count > 0)

    def choose_source_photo(self) -> None:
        """
        Open a file dialog and load a single photo as the GPS source.
        """
        source_path = self._pick_photo_file("Choose Source Photo")
        if source_path is None:
            return

        self._load_source_photo(source_path)

    def _load_source_photo(self, source_path: Path) -> None:
        """
        Load a single source photo and cache its GPS data for apply actions.
        """
        info = self.loader.load_photo_info(source_path)

        self.source_photo_path = source_path
        self.source_latitude = info.current_latitude
        self.source_longitude = info.current_longitude

        self._refresh_source_preview()
        self._update_source_summary()
        self.update_details_panel()

        if info.gps_error:
            self._set_status_message(
                f"Source photo could not load GPS data: {info.gps_error}",
                "error",
            )
        elif info.current_latitude is None or info.current_longitude is None:
            self._set_status_message(
                "Source photo loaded, but it does not contain GPS coordinates.",
                "info",
            )
        else:
            self._set_status_message(
                "Source photo loaded and ready to apply.",
                "success",
            )

    def _refresh_source_preview(self, item: QListWidgetItem | None = None) -> None:
        """
        Refresh the source preview block using the stored source data.
        """
        if self.source_photo_path is None:
            self.source_preview_stack.setCurrentIndex(0)
            self.clear_source_button.setEnabled(False)
            self.source_thumbnail.clear()
            self.source_file_label.setText("No source photo selected")
            self.source_gps_label.setText("Source GPS: Not loaded")
            return

        if item is None:
            for index in range(self.list_widget.count()):
                candidate = self.list_widget.item(index)
                if candidate.data(Qt.UserRole) == str(self.source_photo_path):
                    item = candidate
                    break

        if item is not None:
            pixmap = item.icon().pixmap(160, 160)
        else:
            icon = self.thumbnail_loader.load_icon(
                self.source_photo_path,
                has_gps=(
                    self.source_latitude is not None
                    and self.source_longitude is not None
                ),
            )
            pixmap = icon.pixmap(160, 160)

        self.source_thumbnail.setPixmap(pixmap)

        self.source_file_label.setText(self.source_photo_path.name)
        if self.source_latitude is None or self.source_longitude is None:
            self.source_gps_label.setText("Source GPS: Not found in this photo")
        else:
            self.source_gps_label.setText(
                f"Source GPS: {self.source_latitude:.6f}, {self.source_longitude:.6f}"
            )
        self.source_preview_stack.setCurrentIndex(1)
        self.clear_source_button.setEnabled(True)

    def _handle_manual_coordinate_change(self) -> None:
        """
        Keep the active source summary in sync as manual coordinates are edited.
        """
        self._update_source_summary()
        self._update_selection_metrics()
        self.update_details_panel()

    def _handle_manual_coordinate_input_change(
        self,
        text: str,
    ) -> None:
        """
        Split a pasted coordinate pair across both manual input fields.
        """
        if self._is_splitting_manual_coordinates:
            self._handle_manual_coordinate_change()
            return

        parsed = self.parse_coordinate_text(text)
        if parsed is None:
            self._handle_manual_coordinate_change()
            return

        latitude, longitude = parsed
        self._is_splitting_manual_coordinates = True

        try:
            self.manual_source_radio.setChecked(True)
            self.latitude_input.setText(latitude)
            self.longitude_input.setText(longitude)
            self.set_input_error_state(self.latitude_input, False)
            self.set_input_error_state(self.longitude_input, False)
        finally:
            self._is_splitting_manual_coordinates = False

        self._handle_manual_coordinate_change()

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
        self._set_status_message("Source photo cleared.", "info")

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
            if self.source_photo_path is None:
                self.active_source_coordinates.setText("Coordinates to Apply: Not set")
            elif coordinates is None:
                self.active_source_coordinates.setText(
                    "Coordinates to Apply: Source photo has no GPS"
                )
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
        return parse_manual_coordinates(
            self.latitude_input.text(),
            self.longitude_input.text(),
        )

    def _get_active_source_coordinates(self) -> tuple[float, float] | None:
        """
        Return the coordinates from the currently active source mode.
        """
        if self.photo_source_radio.isChecked():
            if self.source_latitude is None or self.source_longitude is None:
                return None
            return self.source_latitude, self.source_longitude

        return self._get_manual_coordinates()

    def _get_destination_paths(
        self,
        selected_paths: list[Path] | None = None,
    ) -> list[Path]:
        """
        Return selected files that should receive GPS updates.
        """
        if selected_paths is None:
            selected_paths = self.get_selected_paths()

        return get_destination_paths(
            selected_paths,
            self.photo_source_radio.isChecked(),
            self.source_photo_path,
        )

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
        return get_overwrite_entries(self.list_widget, target_paths)

    def _set_status_message(self, message: str, tone: str = "info") -> None:
        """
        Update the editor status card with a message and visual tone.
        """
        self.status_message.setText(message)
        self.status_message.setProperty("tone", tone)
        self.status_message.style().unpolish(self.status_message)
        self.status_message.style().polish(self.status_message)
        self.status_message.update()

    def _default_photo_directory(self) -> Path:
        """
        Return the default directory used by source and destination file pickers.
        """
        pictures_dir = Path.home() / "Pictures"
        return pictures_dir if pictures_dir.exists() else Path.home()

    def _photo_file_filter(self) -> str:
        """
        Return the Qt file filter for supported image types.
        """
        return "Images (*.jpg *.JPG *.jpeg *.JPEG *.cr2 *.CR2 *.cr3 *.CR3 *.dng *.DNG)"

    def _pick_photo_files(self, title: str) -> list[Path]:
        """
        Open the multi-file picker used for destination photo selection.
        """
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            title,
            str(self._default_photo_directory()),
            self._photo_file_filter(),
        )
        return [Path(path) for path in file_paths]

    def _pick_photo_file(self, title: str) -> Path | None:
        """
        Open the single-file picker used for the source photo workflow.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(self._default_photo_directory()),
            self._photo_file_filter(),
        )
        if not file_path:
            return None

        return Path(file_path)

    def select_all_photos(self) -> None:
        """
        Select every photo currently shown in the thumbnail grid.
        """
        self.list_widget.selectAll()
        self.update_details_panel()

    def clear_photo_selection(self) -> None:
        """
        Clear the current thumbnail selection.
        """
        self.list_widget.clearSelection()
        self.update_details_panel()

    def select_photos(self) -> None:
        """
        Open a file dialog and allow user to select one or more images.
        """
        file_paths = self._pick_photo_files("Select Destination Photos")

        if not file_paths:
            return

        self.selected_paths = file_paths
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
        reselect_paths(self.list_widget, paths_to_select)
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
        return build_tooltip_text(filename, latitude, longitude)

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
        self._set_status_message(
            "Coordinates pasted into the manual source fields.",
            "success",
        )

    def parse_coordinate_text(self, text: str) -> tuple[str, str] | None:
        """
        Parse a combined coordinate string into separate latitude and longitude
        strings for the two input fields.

        Supported format:
            latitude, longitude
            latitude longitude

        Returns:
            A tuple of string values if parsing succeeds, otherwise None.
        """
        return parse_coordinate_text(text)

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
                field.setToolTip(
                    "Invalid latitude. Use decimal, DMS, or DDM within -90 to 90"
                )
            elif field is self.longitude_input:
                field.setToolTip(
                    "Invalid longitude. Use decimal, DMS, or DDM within -180 to 180"
                )
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
            parse_latitude_text(text)
            self.set_input_error_state(self.latitude_input, False)
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
            parse_longitude_text(text)
            self.set_input_error_state(self.longitude_input, False)
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
        selected_paths = self.get_selected_paths()
        target_paths = self._get_destination_paths(selected_paths)

        if not target_paths:
            self._set_status_message(
                "Select one or more destination photos before applying GPS.",
                "error",
            )
            return

        if self.manual_source_radio.isChecked():
            self.validate_latitude_field()
            self.validate_longitude_field()

        coordinates = self._get_active_source_coordinates()
        if coordinates is None:
            if self.photo_source_radio.isChecked():
                self._set_status_message(
                    "Choose a source photo with GPS coordinates before applying.",
                    "error",
                )
            else:
                self._set_status_message(
                    "Enter valid latitude and longitude values before applying.",
                    "error",
                )
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
                self._set_status_message(
                    "GPS write cancelled. Existing destination coordinates were left unchanged.",
                    "info",
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

        self.populate_list()
        self.reselect_paths(selected_paths)
        self.update_details_panel()

        if failed_paths and success_count:
            self._set_status_message(
                f"Updated GPS on {success_count} destination file(s). Failed: {'; '.join(failed_paths)}",
                "error",
            )
        elif failed_paths:
            self._set_status_message(
                f"Failed to update destination files: {'; '.join(failed_paths)}",
                "error",
            )
        else:
            self._set_status_message(
                f"Updated GPS on {success_count} destination file(s).",
                "success",
            )

    def update_details_panel(self) -> None:
        """
        Update the right side panel based on the current selection state.
        """
        selected_paths = self.get_selected_paths()
        target_paths = self._get_destination_paths(selected_paths)
        self._update_selection_metrics()
        self._update_source_summary()
        self._update_destination_list(target_paths)
        self.clear_source_button.setEnabled(self.source_photo_path is not None)

        if not target_paths:
            self.apply_button.setEnabled(False)
            return

        source_ready = self._get_active_source_coordinates() is not None
        self.apply_button.setEnabled(source_ready)
