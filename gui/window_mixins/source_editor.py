from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QListWidgetItem

from gui.presenters.editor_state import build_editor_panel_state
from gui.presenters.source_preview import build_source_preview_state
from services.coordinate_service import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
    parse_manual_coordinates,
)
from services.destination_service import get_destination_paths
from services.workflow_controller import clear_source_workflow, load_source_workflow


class SourceEditorMixin:
    def choose_source_photo(self) -> None:
        source_path = self._pick_photo_file("Choose Source Photo")
        if source_path is None:
            return

        self._load_source_photo(source_path)

    def _load_source_photo(self, source_path: Path) -> None:
        load_result = load_source_workflow(self.session, source_path, self.loader)

        self._refresh_source_preview()
        self.update_details_panel()
        self._set_status_message(
            load_result.message.text,
            load_result.message.tone,
        )

    def _refresh_source_preview(self, item: QListWidgetItem | None = None) -> None:
        preview_state = build_source_preview_state(self.session)

        if preview_state.is_empty:
            self.source_preview_stack.setCurrentIndex(0)
            self.clear_source_button.setEnabled(preview_state.can_clear_source)
            self.source_thumbnail.clear()
            self.source_file_label.setText(preview_state.filename_text)
            self.source_gps_label.setText(preview_state.gps_text)
            return

        if item is None:
            for index in range(self.list_widget.count()):
                candidate = self.list_widget.item(index)
                if candidate.data(Qt.UserRole) == str(self.session.source_photo_path):
                    item = candidate
                    break

        if item is not None:
            pixmap = item.icon().pixmap(160, 160)
        else:
            icon = self.thumbnail_loader.load_icon(
                self.session.source_photo_path,
                has_gps=preview_state.has_gps,
            )
            pixmap = icon.pixmap(160, 160)

        self.source_thumbnail.setPixmap(pixmap)
        self.source_file_label.setText(preview_state.filename_text)
        self.source_gps_label.setText(preview_state.gps_text)
        self.source_preview_stack.setCurrentIndex(1)
        self.clear_source_button.setEnabled(preview_state.can_clear_source)

    def _handle_manual_coordinate_change(self) -> None:
        self._update_selection_metrics()
        self.update_details_panel()

    def _handle_manual_coordinate_input_change(self, text: str) -> None:
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
        message = clear_source_workflow(self.session)
        self._refresh_source_preview()
        self._update_selection_metrics()
        self.update_details_panel()
        self._set_status_message(message.text, message.tone)

    def _update_apply_button_text(self) -> None:
        if self.photo_source_radio.isChecked():
            self.apply_button.setText("Apply Photo Source GPS to Destination Files")
        else:
            self.apply_button.setText("Apply Manual GPS to Destination Files")

    def _get_manual_coordinates(self) -> tuple[float, float] | None:
        return parse_manual_coordinates(
            self.latitude_input.text(),
            self.longitude_input.text(),
        )

    def _build_editor_panel_state(self):
        return build_editor_panel_state(
            session=self.session,
            selected_paths=self.get_selected_paths(),
            using_photo_source=self.photo_source_radio.isChecked(),
            latitude_text=self.latitude_input.text(),
            longitude_text=self.longitude_input.text(),
        )

    def _get_destination_paths(
        self,
        selected_paths: list[Path] | None = None,
    ) -> list[Path]:
        if selected_paths is None:
            selected_paths = self.get_selected_paths()

        return get_destination_paths(
            selected_paths,
            self.photo_source_radio.isChecked(),
            self.session.source_photo_path,
        )

    def _apply_editor_panel_state(self) -> None:
        panel_state = self._build_editor_panel_state()
        self.active_source_coordinates.setText(panel_state.source_summary)
        self.destination_list.clear()
        for destination_name in panel_state.destination_names:
            self.destination_list.addItem(destination_name)
        self.clear_source_button.setEnabled(panel_state.can_clear_source)
        self.apply_button.setEnabled(panel_state.can_apply)

    def _set_status_message(self, message: str, tone: str = "info") -> None:
        self.status_message.setText(message)
        self.status_message.setProperty("tone", tone)
        self.status_message.style().unpolish(self.status_message)
        self.status_message.style().polish(self.status_message)
        self.status_message.update()

    def paste_coordinates_from_clipboard(self) -> None:
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
        self._apply_editor_panel_state()
        self._set_status_message(
            "Coordinates pasted into the manual source fields.",
            "success",
        )

    def parse_coordinate_text(self, text: str) -> tuple[str, str] | None:
        return parse_coordinate_text(text)

    def set_input_error_state(self, field: QLineEdit, has_error: bool) -> None:
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
        text = self.longitude_input.text().strip()

        if not text:
            self.set_input_error_state(self.longitude_input, False)
            return

        try:
            parse_longitude_text(text)
            self.set_input_error_state(self.longitude_input, False)
        except ValueError:
            self.set_input_error_state(self.longitude_input, True)

    def update_details_panel(self) -> None:
        self._update_selection_metrics()
        self._apply_editor_panel_state()
