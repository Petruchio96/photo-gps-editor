"""
Apply and Remove GPS: the two actions on the photos selected in the grid.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox


def _photos(count: int) -> str:
    return f"{count} photo" if count == 1 else f"{count} photos"


class ApplyWorkflowMixin:
    def apply_coordinates_to_selected(self) -> None:
        """
        Write the New Location coordinates to every selected photo.
        """
        selected_paths = self.get_selected_paths()
        if not selected_paths:
            self._set_status_message("Select the photos to update in the grid first.", "error")
            return

        self.validate_latitude_field()
        self.validate_longitude_field()

        preparation = self.workflow.prepare_apply_workflow(
            session=self.session,
            selected_paths=selected_paths,
            using_photo_source=False,
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
            confirmation_dialog.setWindowTitle("Replace Existing GPS?")
            confirmation_dialog.setText(
                f"{_photos(len(overwrite_entries)).capitalize()} already "
                f"{'has' if len(overwrite_entries) == 1 else 'have'} GPS coordinates. "
                "Replace them with the new location?"
            )
            confirmation_dialog.setInformativeText(
                "Show Details lists each photo and its current coordinates. "
                "You can undo this afterwards."
            )
            confirmation_dialog.setDetailedText(
                "\n".join(self._format_overwrite_entries(overwrite_entries))
            )
            confirmation_dialog.setStandardButtons(
                QMessageBox.Ok | QMessageBox.Cancel
            )
            confirmation_dialog.button(QMessageBox.Ok).setText("Replace")
            confirmation_dialog.setDefaultButton(QMessageBox.Cancel)

            if confirmation_dialog.exec() != QMessageBox.Ok:
                self._set_status_message(
                    "Nothing was changed.",
                    "info",
                )
                return

        before_states = self._gps_states_for_paths(preparation.target_paths)
        apply_result = self.workflow.execute_apply_workflow(
            session=self.session,
            preparation=preparation,
        )
        self.session = apply_result.session

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

        self._rerender_keeping_selection(selected_paths)
        if result.successful_paths:
            self._set_status_message(
                f"Applied GPS to {_photos(len(result.successful_paths))}.",
                "success",
                undo=True,
            )
        self._report_write_failures("apply GPS to", list(result.failed_paths))

    def remove_gps_from_selected(self) -> None:
        """
        Delete the GPS coordinates stored in the selected photos (after asking).
        """
        paths_with_gps = [
            path
            for path in self.get_selected_paths()
            if (info := self.session.loaded_photo_infos.get(path)) is not None
            and info.current_latitude is not None
            and info.current_longitude is not None
        ]
        if not paths_with_gps:
            return

        confirmation_dialog = QMessageBox(self)
        confirmation_dialog.setIcon(QMessageBox.Warning)
        confirmation_dialog.setWindowTitle("Remove GPS?")
        confirmation_dialog.setText(
            f"Remove the GPS coordinates from {_photos(len(paths_with_gps))}?"
        )
        confirmation_dialog.setInformativeText(
            "Show Details lists the photos. You can undo this afterwards."
        )
        confirmation_dialog.setDetailedText("\n".join(path.name for path in paths_with_gps))
        confirmation_dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirmation_dialog.button(QMessageBox.Ok).setText("Remove GPS")
        confirmation_dialog.setDefaultButton(QMessageBox.Cancel)

        if confirmation_dialog.exec() != QMessageBox.Ok:
            return

        selected_paths = self.get_selected_paths()
        before_states = self._gps_states_for_paths(paths_with_gps)
        # The backend attempts every file and reports failures instead of
        # stopping at the first one.
        clear_result = self.workflow.clear_gps_workflow(
            session=self.session,
            target_paths=paths_with_gps,
        )
        self.session = clear_result.session
        result = clear_result.execution_result

        if result.successful_paths:
            self._remember_gps_edit(
                before_states=before_states,
                after_states={path: (None, None) for path in result.successful_paths},
            )
        else:
            self._clear_gps_edit_history()

        self._rerender_keeping_selection(selected_paths)
        if result.successful_paths:
            self._set_status_message(
                f"Removed GPS from {_photos(len(result.successful_paths))}.",
                "success",
                undo=True,
            )
        self._report_write_failures("remove GPS from", list(result.failed_paths))

    def _rerender_keeping_selection(self, paths: list[Path]) -> None:
        """
        Redraw the grid after a change (photos may move between groups) and
        keep the same photos selected where they are still shown.
        """
        self._render_current_photo_session()
        self.reselect_paths(paths)
        self.update_details_panel()
