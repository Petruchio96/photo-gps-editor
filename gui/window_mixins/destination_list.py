from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QListWidgetItem, QMenu

from gui.presenters.thumbnail_items import build_thumbnail_item_data_list, reselect_paths
from services.workflow_controller import refresh_destination_workflow


class DestinationListMixin:
    def select_all_photos(self) -> None:
        self.list_widget.selectAll()
        self.update_details_panel()

    def clear_photo_selection(self) -> None:
        self.list_widget.clearSelection()
        self.update_details_panel()

    def select_photos(self) -> None:
        file_paths = self._pick_photo_files("Select Destination Photos")

        if not file_paths:
            return

        self.session.selected_paths = file_paths
        self.populate_list()

    def populate_list(self) -> None:
        self.session = refresh_destination_workflow(
            self.session,
            self.loader,
        )
        self.session.thumbnail_items = build_thumbnail_item_data_list(
            self.session.loaded_photos
        )
        self._render_destination_list()

    def _render_destination_list(self) -> None:
        self.list_widget.clear()

        for item_data in self.session.thumbnail_items:
            path = item_data.path
            icon = self.thumbnail_loader.load_icon(
                path,
                has_gps=item_data.has_gps,
            )

            item = QListWidgetItem(icon, item_data.filename)
            item.setData(Qt.UserRole, str(path))
            item.setData(Qt.UserRole + 1, item_data.latitude)
            item.setData(Qt.UserRole + 2, item_data.longitude)
            item.setToolTip(item_data.tooltip)
            self.list_widget.addItem(item)

        self._refresh_source_preview()
        self.update_details_panel()
        self._update_selection_metrics()

    def get_selected_paths(self) -> list[Path]:
        selected_items = self.list_widget.selectedItems()
        return [Path(item.data(Qt.UserRole)) for item in selected_items]

    def reselect_paths(self, paths_to_select: list[Path]) -> None:
        reselect_paths(self.list_widget, paths_to_select)
        self._update_selection_metrics()

    def show_context_menu(self, position) -> None:
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
        if latitude is None or longitude is None:
            return

        QApplication.clipboard().setText(f"{latitude:.6f}, {longitude:.6f}")
