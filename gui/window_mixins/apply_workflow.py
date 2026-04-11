from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from gui.presenters.thumbnail_items import build_thumbnail_item_data_list
from services.destination_service import get_destination_paths
from services.workflow_controller import execute_apply_workflow, prepare_apply_workflow


class ApplyWorkflowMixin:
    def apply_coordinates_to_selected(self) -> None:
        selected_paths = self.get_selected_paths()
        target_paths = get_destination_paths(
            selected_paths,
            self.photo_source_radio.isChecked(),
            self.session.source_photo_path,
        )

        if not target_paths:
            self._set_status_message(
                "Select one or more destination photos before applying GPS.",
                "error",
            )
            return

        if self.manual_source_radio.isChecked():
            self.validate_latitude_field()
            self.validate_longitude_field()

        preparation = prepare_apply_workflow(
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
                f"{len(overwrite_entries)} destination file(s) already contain GPS and will be overwritten."
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
                    "GPS write cancelled. Existing destination coordinates were left unchanged.",
                    "info",
                )
                return

        apply_result = execute_apply_workflow(
            session=self.session,
            preparation=preparation,
            writer=self.exiftool,
            loader=self.loader,
        )
        self.session = apply_result.session
        self.session.thumbnail_items = build_thumbnail_item_data_list(
            self.session.loaded_photos
        )
        self._render_destination_list()
        self.reselect_paths(selected_paths)
        self.update_details_panel()

        result = apply_result.execution_result

        if result.failed_paths and result.success_count:
            self._set_status_message(
                f"Updated GPS on {result.success_count} destination file(s). Failed: {'; '.join(result.failed_paths)}",
                "error",
            )
        elif result.failed_paths:
            self._set_status_message(
                f"Failed to update destination files: {'; '.join(result.failed_paths)}",
                "error",
            )
        else:
            self._set_status_message(
                f"Updated GPS on {result.success_count} destination file(s).",
                "success",
            )
