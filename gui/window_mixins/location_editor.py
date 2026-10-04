"""
The New Location fields in the inspector panel.

Two separate jobs, kept visually separate:
    - The photos selected in the grid are the photos to change.
    - The New Location is where their new coordinates come from: typed,
      pasted, read from a photo file ("From a Photo…"), or picked from the
      grid with the "Pick from Grid" eyedropper or the right-click menu.
      Picking never changes the selection.

When the location came from a photo, that photo is the "location source":
the New Location box shows it on a blue card and the grid marks it in blue.
Whatever is in the fields is what Apply writes to the selected photos.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QListWidgetItem

from core.models import GpsCoordinates
from gui.presenters.inspector_state import format_coordinates
from gui.widgets.thumbnail_delegate import SOURCE_ROLE
from services.coordinate_service import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
    parse_manual_coordinates,
)

PICK_PROMPT = "Click a photo that has GPS to use its location. Press Esc or Cancel to stop."


class LocationEditorMixin:
    def set_location_fields(
        self,
        latitude: str,
        longitude: str,
        *,
        source: Path | None = None,
    ) -> None:
        """
        Fill both fields, without the auto-split of pasted pairs kicking in.

        Args:
            source:
                The photo the coordinates came from, or None if they did not
                come from a photo (typed, pasted, cleared).
        """
        self._is_splitting_manual_coordinates = True
        try:
            self.latitude_input.setText(latitude)
            self.longitude_input.setText(longitude)
        finally:
            self._is_splitting_manual_coordinates = False
        self.set_input_error_state(self.latitude_input, False)
        self.set_input_error_state(self.longitude_input, False)
        self._set_location_source(source)
        self.update_details_panel()

    def clear_location_fields(self) -> None:
        self.set_location_fields("", "")

    def use_location_from_path(self, path: Path) -> bool:
        """
        Make a loaded photo the location source. Returns False if it has no GPS.
        """
        info = self.session.loaded_photo_infos.get(path)
        if info is None or info.current_latitude is None or info.current_longitude is None:
            return False

        self.set_location_fields(
            f"{info.current_latitude:.6f}",
            f"{info.current_longitude:.6f}",
            source=path,
        )
        self._set_status_message(
            f"Using the location from {path.name}. "
            "Now select the photos to change and click Apply.",
            "success",
        )
        return True

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
            source=path,
        )
        self._set_status_message(
            f"Using the location from {path.name}: "
            f"{format_coordinates(GpsCoordinates(info.current_latitude, info.current_longitude))}.",
            "success",
        )

    # --- Pick from Grid (eyedropper) -----------------------------------------

    @property
    def is_picking_location(self) -> bool:
        return self._picking_location

    def toggle_picking_location(self, checked: bool = False) -> None:
        if self._picking_location:
            self.stop_picking_location()
        else:
            self.start_picking_location()

    def start_picking_location(self) -> None:
        """
        Enter pick mode: the next click on a photo sets the location source.
        """
        self._picking_location = True
        self.pick_location_button.setChecked(True)
        self.pick_location_button.setText("Picking… (Esc to cancel)")
        self.pick_banner_label.setText(PICK_PROMPT)
        self.pick_banner.show()
        self.list_widget.viewport().setCursor(Qt.CrossCursor)
        self._pick_escape_shortcut.setEnabled(True)

    def stop_picking_location(self) -> None:
        self._picking_location = False
        self.pick_location_button.setChecked(False)
        self.pick_location_button.setText("Pick from Grid")
        self.pick_banner.hide()
        self.list_widget.viewport().unsetCursor()
        self._pick_escape_shortcut.setEnabled(False)

    def pick_location_from_item(self, item: QListWidgetItem | None) -> None:
        """
        Called for a click on the grid while picking.
        """
        if item is None:
            return
        path_text = item.data(Qt.UserRole)
        if path_text is None:
            # A group heading, not a photo.
            return

        path = Path(path_text)
        if self.use_location_from_path(path):
            self.stop_picking_location()
        else:
            self.pick_banner_label.setText(
                f"{path.name} has no GPS. Click a photo that has GPS "
                "(the Has GPS filter shows them), or press Esc to stop."
            )

    # --- Location source display ---------------------------------------------

    def _set_location_source(self, source: Path | None) -> None:
        self._location_source = source
        self._refresh_source_card()
        self._refresh_source_marker()

    def _refresh_source_card(self) -> None:
        source = self._location_source
        if source is None:
            self.source_card.hide()
            return

        self.source_card_title.setText(f"From {source.name}")
        location = parse_manual_coordinates(self.latitude_input.text(), self.longitude_input.text())
        self.source_card_detail.setText(
            format_coordinates(GpsCoordinates(*location)) if location else ""
        )
        item = self._grid_items_by_path.get(str(source))
        icon = item.icon() if item is not None else self.thumbnail_loader.load_icon(source, has_gps=True)
        self.source_card_thumbnail.setPixmap(icon.pixmap(52, 52))
        self.source_card.show()

    def _refresh_source_marker(self) -> None:
        """
        Mark the location source photo in the grid (blue outline).
        """
        source_text = str(self._location_source) if self._location_source else None
        for path_text, item in self._grid_items_by_path.items():
            is_source = path_text == source_text
            if bool(item.data(SOURCE_ROLE)) != is_source:
                item.setData(SOURCE_ROLE, is_source)

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
        into the two fields automatically. Editing the fields by hand means
        the location no longer comes from the source photo.
        """
        if self._is_splitting_manual_coordinates:
            return

        parsed = self.parse_coordinate_text(text)
        if parsed is not None:
            self.set_location_fields(*parsed)
            return

        if self._location_source is not None:
            self._set_location_source(None)
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

