"""
The New Location fields in the inspector panel.

Coordinates can be typed, pasted, taken from a selected photo ("Use This
Location"), or read from any photo file ("From a Photo…"). Whatever is in the
fields is what Apply writes to the selected photos.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLineEdit

from core.models import GpsCoordinates
from gui.presenters.inspector_state import format_coordinates
from services.coordinate_service import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
)


class LocationEditorMixin:
    def set_location_fields(self, latitude: str, longitude: str) -> None:
        """
        Fill both fields, without the auto-split of pasted pairs kicking in.
        """
        self._is_splitting_manual_coordinates = True
        try:
            self.latitude_input.setText(latitude)
            self.longitude_input.setText(longitude)
        finally:
            self._is_splitting_manual_coordinates = False
        self.set_input_error_state(self.latitude_input, False)
        self.set_input_error_state(self.longitude_input, False)
        self.update_details_panel()

    def clear_location_fields(self) -> None:
        self.set_location_fields("", "")

    def use_selected_photo_location(self) -> None:
        """
        Copy the selected photo's GPS into New Location, ready to apply elsewhere.
        """
        coordinates = self._selected_browser_gps_coordinates()
        if coordinates is None:
            return

        latitude, longitude = coordinates
        self.set_location_fields(f"{latitude:.6f}", f"{longitude:.6f}")
        selected = self.get_selected_paths()
        name = selected[0].name if selected else "the photo"
        self._set_status_message(
            f"Using the location from {name}. Now select the photos to update.",
            "success",
        )

    def choose_location_from_photo(self) -> None:
        """
        Read the GPS coordinates of any photo file into New Location.
        """
        path = self._pick_photo_file("Use the Location from a Photo")
        if path is None:
            return

        info = self.workflow.read_photo_info(path)
        if info.gps_error:
            self._set_status_message(
                f"Could not read GPS from {path.name}: {info.gps_error}",
                "error",
            )
            return
        if info.current_latitude is None or info.current_longitude is None:
            self._set_status_message(f"{path.name} has no GPS coordinates.", "error")
            return

        self.set_location_fields(
            f"{info.current_latitude:.6f}",
            f"{info.current_longitude:.6f}",
        )
        self._set_status_message(
            f"Using the location from {path.name}: "
            f"{format_coordinates(GpsCoordinates(info.current_latitude, info.current_longitude))}.",
            "success",
        )

    def paste_coordinates_from_clipboard(self) -> None:
        clipboard_text = QApplication.clipboard().text().strip()
        parsed = self.parse_coordinate_text(clipboard_text)

        if parsed is None:
            self._update_clipboard_buttons()
            self._set_status_message(
                "The clipboard doesn't contain coordinates.",
                "error",
            )
            return

        latitude, longitude = parsed
        self.set_location_fields(latitude, longitude)

    def _handle_location_input_change(self, text: str) -> None:
        """
        Typing or pasting "40.5865, -111.6558" into either field splits it
        into the two fields automatically.
        """
        if self._is_splitting_manual_coordinates:
            return

        parsed = self.parse_coordinate_text(text)
        if parsed is not None:
            self.set_location_fields(*parsed)
            return

        self.update_details_panel()

    def _clipboard_has_valid_coordinates(self) -> bool:
        clipboard_text = QApplication.clipboard().text().strip()
        return self.parse_coordinate_text(clipboard_text) is not None

    def _update_clipboard_buttons(self) -> None:
        can_paste_coordinates = self._clipboard_has_valid_coordinates()
        self.paste_coordinates_button.setEnabled(can_paste_coordinates)
        self.paste_coordinates_button.setToolTip(
            "Paste coordinates copied from a map or another photo"
            if can_paste_coordinates
            else "Copy coordinates (for example from a map) to paste them here"
        )
        if hasattr(self, "paste_action"):
            self.paste_action.setEnabled(can_paste_coordinates)

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

