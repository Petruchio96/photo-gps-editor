"""
Apply and Remove GPS: the two actions on the photos selected in the grid.
"""

from __future__ import annotations

from dataclasses import replace
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
            self._set_status_message("Select the photos to change in the Photo List first.", "error")
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
        skipped_count = 0

        if overwrite_entries:
            choice = self._ask_overwrite_choice(
                overwrite_entries,
                other_count=len(preparation.target_paths) - len(overwrite_entries),
            )
            if choice == "cancel":
                self._set_status_message("Nothing was changed.", "info")
                return
            if choice == "skip":
                # Leave photos that already have GPS untouched.
                keep = {entry.path for entry in overwrite_entries}
                preparation = replace(
                    preparation,
                    target_paths=[path for path in preparation.target_paths if path not in keep],
                    overwrite_entries=[],
                )
                skipped_count = len(keep)

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
            message = f"Applied GPS to {_photos(len(result.successful_paths))}."
            if skipped_count:
                message += (
                    f" Skipped {skipped_count} that already "
                    f"{'has' if skipped_count == 1 else 'had'} GPS."
                )
            self._set_status_message(message, "success", undo=True)
        self._report_write_failures("apply GPS to", list(result.failed_paths))

    def _ask_overwrite_choice(self, overwrite_entries, *, other_count: int) -> str:
        """
        Ask what to do when some selected photos already have GPS.

        Args:
            overwrite_entries:
                The selected photos that already have GPS.
            other_count:
                How many selected photos have no GPS yet.

        Returns:
            "replace" (update all), "skip" (update only photos without GPS),
            or "cancel" (change nothing).
        """
        count = len(overwrite_entries)
        have = "has" if count == 1 else "have"

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Replace Existing GPS?")
        already = f"{_photos(count).capitalize()} already {have} GPS Coordinates."
        undo_tip = "Click Edit → Undo if you accidentally overwrite GPS data."
        if other_count:
            dialog.setText(
                f"{already} Choose Skip to keep the existing GPS data, "
                f"Replace to overwrite them. {undo_tip}"
            )
        else:
            # Every selected photo has GPS, so there is nothing to skip to.
            dialog.setText(f"{already} Choose Replace to overwrite them. {undo_tip}")
        # Show Details still lists each photo and its current coordinates.
        dialog.setDetailedText("\n".join(self._format_overwrite_entries(overwrite_entries)))

        cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
        # Skip only makes sense when some photos have no GPS yet.
        skip_button = (
            dialog.addButton("Skip Photos with GPS", QMessageBox.AcceptRole)
            if other_count
            else None
        )
        replace_button = dialog.addButton("Replace", QMessageBox.DestructiveRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is replace_button:
            return "replace"
        if skip_button is not None and clicked is skip_button:
            return "skip"
        return "cancel"

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
