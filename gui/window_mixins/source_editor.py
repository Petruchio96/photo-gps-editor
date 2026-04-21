from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QLineEdit, QListWidgetItem, QMessageBox

from gui.presenters.editor_state import build_editor_panel_state
from gui.presenters.source_preview import build_source_preview_state
from gui.window_mixins.photo_list import THUMBNAIL_PATH_ROLE
from services.coordinate_service import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
    parse_manual_coordinates,
)
from services.target_paths_service import get_target_paths


class SourceEditorMixin:
    def _selection_has_gps(self, paths: list[Path]) -> bool:
        return any(
            (
                info := self.session.loaded_photo_infos.get(path)
            ) is not None
            and info.current_latitude is not None
            and info.current_longitude is not None
            for path in paths
        )

    def _update_target_selection_actions(self) -> None:
        target_paths = self._get_target_paths()
        has_target_photos = bool(target_paths)
        selected_count = len(self.get_selected_target_paths())
        removes_partial_selection = 0 < selected_count < len(target_paths)

        self.remove_selected_photos_button.setEnabled(has_target_photos)
        self.remove_selected_photos_button.setProperty(
            "tone",
            "primary" if has_target_photos else "neutral",
        )
        self.remove_selected_photos_button.setText(
            "Remove Selected Photos" if removes_partial_selection else "Remove All Photos"
        )
        self.remove_selected_photos_button.style().unpolish(self.remove_selected_photos_button)
        self.remove_selected_photos_button.style().polish(self.remove_selected_photos_button)
        self.remove_selected_photos_button.update()

    def _clipboard_has_valid_coordinates(self) -> bool:
        clipboard_text = QApplication.clipboard().text().strip()
        return self.parse_coordinate_text(clipboard_text) is not None

    def _update_clipboard_buttons(self) -> None:
        can_paste_coordinates = self._clipboard_has_valid_coordinates()
        self.paste_coordinates_button.setEnabled(can_paste_coordinates)
        if hasattr(self, "paste_action"):
            self.paste_action.setEnabled(can_paste_coordinates)

    def choose_source_photo(self) -> None:
        source_path = self._pick_photo_file("Choose Source Photo")
        if source_path is None:
            return

        self._load_source_photo(source_path)

    def _load_source_photo(self, source_path: Path) -> None:
        load_result = self.workflow.load_source_workflow(self.session, source_path)
        if self.photo_source_radio.isChecked():
            self.session.target_paths = [
                path for path in self.session.target_paths if path != source_path
            ]

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
            return

        if item is None:
            for index in range(self.list_widget.count()):
                candidate = self.list_widget.item(index)
                if candidate.data(THUMBNAIL_PATH_ROLE) == str(self.session.source_photo_path):
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
        message = self.workflow.clear_source_workflow(self.session)
        self._refresh_source_preview()
        self._update_selection_metrics()
        self.update_details_panel()
        self._set_status_message(message.text, message.tone)

    def _update_apply_button_text(self) -> None:
        self.apply_button.setText("Apply New GPS Coordinates to Photos")

    def _get_manual_coordinates(self) -> tuple[float, float] | None:
        return parse_manual_coordinates(
            self.latitude_input.text(),
            self.longitude_input.text(),
        )

    def _build_editor_panel_state(self):
        return build_editor_panel_state(
            session=self.session,
            browser_selected_paths=self.get_selected_paths(),
            target_selected_paths=self.get_selected_target_paths(),
            using_photo_source=self.photo_source_radio.isChecked(),
            latitude_text=self.latitude_input.text(),
            longitude_text=self.longitude_input.text(),
        )

    def _get_target_paths(
        self,
        target_paths: list[Path] | None = None,
    ) -> list[Path]:
        if target_paths is None:
            target_paths = list(self.session.target_paths)

        return get_target_paths(
            target_paths,
            self.photo_source_radio.isChecked(),
            self.session.source_photo_path,
        )

    def get_selected_target_paths(self) -> list[Path]:
        selected_items = self.selected_photos_list.selectedItems()
        return [Path(item.data(Qt.UserRole)) for item in selected_items]

    def handle_target_list_selection_changed(self) -> None:
        if getattr(self, "_syncing_target_selection", False):
            return

        self.select_browser_paths(
            self.get_selected_target_paths(),
            update_details=False,
        )
        self._update_selection_metrics()
        self._update_target_selection_actions()

    def remove_selected_photos_from_target_list(self) -> None:
        paths_to_remove = set(self.get_selected_target_paths())
        if not paths_to_remove:
            paths_to_remove = set(self._get_target_paths())

        if not paths_to_remove:
            return

        self.session.target_paths = [
            path for path in self.session.target_paths if path not in paths_to_remove
        ]
        self.list_widget.clearSelection()
        self._refresh_target_list_selection([])
        self.update_details_panel()

    def _refresh_target_list_selection(self, paths_to_select: list[Path]) -> None:
        wanted = {str(path) for path in paths_to_select}
        self._syncing_target_selection = True
        try:
            with QSignalBlocker(self.selected_photos_list):
                self.selected_photos_list.clearSelection()
                for index in range(self.selected_photos_list.count()):
                    item = self.selected_photos_list.item(index)
                    item.setSelected(item.data(Qt.UserRole) in wanted)
        finally:
            self._syncing_target_selection = False
        self._update_target_selection_actions()

    def clear_selected_target_coordinates(self) -> None:
        target_paths = list(self._get_target_paths())
        paths_with_gps = [
            path
            for path in target_paths
            if (
                info := self.session.loaded_photo_infos.get(path)
            ) is not None
            and info.current_latitude is not None
            and info.current_longitude is not None
        ]

        if not paths_with_gps:
            return

        confirmation_dialog = QMessageBox(self)
        confirmation_dialog.setIcon(QMessageBox.Warning)
        confirmation_dialog.setWindowTitle("GPS Data Will Be Deleted")
        confirmation_dialog.setText(
            "The following file(s) will have their GPS metadata deleted:"
        )
        confirmation_dialog.setInformativeText(
            "\n".join(path.name for path in paths_with_gps)
        )
        continue_button = confirmation_dialog.addButton(
            "Continue",
            QMessageBox.AcceptRole,
        )
        cancel_button = confirmation_dialog.addButton(
            "Cancel",
            QMessageBox.RejectRole,
        )
        confirmation_dialog.setDefaultButton(cancel_button)
        confirmation_dialog.exec()

        if confirmation_dialog.clickedButton() is not continue_button:
            return

        before_states = self._gps_states_for_paths(paths_with_gps)
        for path in paths_with_gps:
            self.exiftool.clear_gps(path)

        self._remember_gps_edit(
            before_states=before_states,
            after_states={path: (None, None) for path in paths_with_gps},
        )
        self._clear_target_list()
        self.session = self.workflow.refresh_photo_workflow(self.session)
        self._render_current_photo_session()
        self.list_widget.clearSelection()
        self.update_details_panel()

    def _clear_target_list(self) -> None:
        self.session.target_paths = []
        self._syncing_target_selection = True
        try:
            with QSignalBlocker(self.selected_photos_list):
                self.selected_photos_list.clear()
        finally:
            self._syncing_target_selection = False
        self._update_target_selection_actions()

    def _apply_editor_panel_state(self) -> None:
        panel_state = self._build_editor_panel_state()
        selected_target_paths = self.get_selected_target_paths()
        self.selected_photos_title_label.setText(
            f"Selected Photos to Change GPS Coordinates ({panel_state.selected_photo_count})"
        )
        self.selected_photos_stack.setCurrentIndex(
            1 if panel_state.selected_photo_count else 0
        )
        self.active_source_coordinates.setText(panel_state.source_summary)
        self._syncing_target_selection = True
        try:
            with QSignalBlocker(self.selected_photos_list):
                self.selected_photos_list.clear()
                for path in self._get_target_paths():
                    item = QListWidgetItem(path.name)
                    item.setData(Qt.UserRole, str(path))
                    info = self.session.loaded_photo_infos.get(path)
                    if (
                        info is not None
                        and info.current_latitude is not None
                        and info.current_longitude is not None
                    ):
                        item.setBackground(QColor("#fff4d6"))
                        item.setToolTip(
                            f"Existing GPS: {info.current_latitude:.6f}, {info.current_longitude:.6f}"
                        )
                    self.selected_photos_list.addItem(item)
        finally:
            self._syncing_target_selection = False
        self.clear_source_button.setEnabled(panel_state.can_clear_source)
        self.clear_source_button.setProperty(
            "tone",
            "primary" if panel_state.can_clear_source else "neutral",
        )
        self.clear_source_button.style().unpolish(self.clear_source_button)
        self.clear_source_button.style().polish(self.clear_source_button)
        self.clear_source_button.update()
        can_clear_manual_coordinates = bool(
            self.latitude_input.text().strip() or self.longitude_input.text().strip()
        )
        self.clear_manual_coordinates_button.setEnabled(can_clear_manual_coordinates)
        self.clear_manual_coordinates_button.setProperty(
            "tone",
            "primary" if can_clear_manual_coordinates else "neutral",
        )
        self.clear_manual_coordinates_button.style().unpolish(
            self.clear_manual_coordinates_button
        )
        self.clear_manual_coordinates_button.style().polish(
            self.clear_manual_coordinates_button
        )
        self.clear_manual_coordinates_button.update()
        self._update_clipboard_buttons()
        self.add_selected_button.setEnabled(panel_state.can_add_selected_photos)
        self.clear_selected_gps_button.setEnabled(panel_state.can_clear_list_gps)
        self.clear_selected_gps_button.setProperty(
            "tone",
            "danger" if panel_state.can_clear_list_gps else "neutral",
        )
        self.clear_selected_gps_button.style().unpolish(self.clear_selected_gps_button)
        self.clear_selected_gps_button.style().polish(self.clear_selected_gps_button)
        self.clear_selected_gps_button.update()
        self.apply_button.setEnabled(panel_state.can_apply)
        self.apply_button.setProperty("tone", panel_state.apply_tone)
        self.apply_button.style().unpolish(self.apply_button)
        self.apply_button.style().polish(self.apply_button)
        self.apply_button.update()
        self._refresh_target_list_selection(selected_target_paths)

    def _set_status_message(self, message: str, tone: str = "info") -> None:
        self._last_status_message = message
        self._last_status_tone = tone

    def paste_coordinates_from_clipboard(self) -> None:
        clipboard_text = QApplication.clipboard().text().strip()
        parsed = self.parse_coordinate_text(clipboard_text)

        if parsed is None:
            self._update_clipboard_buttons()
            return

        latitude, longitude = parsed
        self.manual_source_radio.setChecked(True)
        self.latitude_input.setText(latitude)
        self.longitude_input.setText(longitude)
        self.set_input_error_state(self.latitude_input, False)
        self.set_input_error_state(self.longitude_input, False)
        self._apply_editor_panel_state()

    def clear_manual_coordinates(self) -> None:
        self.manual_source_radio.setChecked(True)
        self.latitude_input.clear()
        self.longitude_input.clear()
        self.set_input_error_state(self.latitude_input, False)
        self.set_input_error_state(self.longitude_input, False)
        self._apply_editor_panel_state()

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
