from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from services.target_paths_service import get_target_paths


class ApplyWorkflowMixin:
    def apply_coordinates_to_selected(self) -> None:
        selected_paths = list(self.session.target_paths)
        target_paths = get_target_paths(
            selected_paths,
            self.photo_source_radio.isChecked(),
            self.session.source_photo_path,
        )

        if not target_paths:
            self._set_status_message(
                "Select one or more photos before applying GPS.",
                "error",
            )
            return

        if self.manual_source_radio.isChecked():
            self.validate_latitude_field()
            self.validate_longitude_field()

        preparation = self.workflow.prepare_apply_workflow(
            session=self.session,
            selected_paths=selected_paths,
            using_photo_source=self.photo_source_radio.isChecked(),
            latitude_text=self.latitude_input.text(),
            longitude_text=self.longitude_input.text(),
        )
        if preparation.error_message is not None:
            self._set_status_message(preparation.error_message, "error")
            return

        overwrite_entries = preparation.overwrite_entries

        if overwrite_entries:
            confirmation_dialog = QMessageBox(self)
            confirmation_dialog.setIcon(QMessageBox.Warning)
            confirmation_dialog.setWindowTitle("Existing GPS Will Change")
            confirmation_dialog.setText(
                f"{len(overwrite_entries)} selected file(s) already contain GPS and will be overwritten."
            )
            confirmation_dialog.setInformativeText(
                "Review the files below and choose OK to continue or Cancel to stop."
            )
            confirmation_dialog.setDetailedText(
                "\n".join(self._format_overwrite_entries(overwrite_entries))
            )
            confirmation_dialog.setStandardButtons(
                QMessageBox.Ok | QMessageBox.Cancel
            )
            confirmation_dialog.setDefaultButton(QMessageBox.Cancel)

            if confirmation_dialog.exec() != QMessageBox.Ok:
                self._set_status_message(
                    "GPS write cancelled. Existing file coordinates were left unchanged.",
                    "info",
                )
                return

        before_states = self._gps_states_for_paths(preparation.target_paths)
        apply_result = self.workflow.execute_apply_workflow(
            session=self.session,
            preparation=preparation,
        )
        self.session = apply_result.session
        self._clear_target_list()
        self._render_current_photo_session()

        result = apply_result.execution_result
        if result.successful_paths:
            coordinates = preparation.coordinates
            self._remember_gps_edit(
                before_states={
                    path: before_states[path] for path in result.successful_paths
                },
                after_states={
                    path: (coordinates.latitude, coordinates.longitude)
                    for path in result.successful_paths
                },
            )
        else:
            self._clear_gps_edit_history()

        if result.failed_paths:
            self._last_apply_failures = list(result.failed_paths)
