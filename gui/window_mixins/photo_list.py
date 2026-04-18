from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QListWidgetItem,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from gui.presenters.thumbnail_items import build_thumbnail_item_data_list, reselect_paths
from services.workflow_controller import refresh_photo_workflow

THUMBNAIL_PATH_ROLE = Qt.UserRole
THUMBNAIL_LATITUDE_ROLE = Qt.UserRole + 1
THUMBNAIL_LONGITUDE_ROLE = Qt.UserRole + 2
THUMBNAIL_ITEM_SIZE = QSize(170, 190)
GPS_HEADER_HEIGHT = 52


class PhotoListMixin:
    def add_selected_photos_to_target_list(self) -> None:
        staged_paths = list(self.session.target_paths)

        for path in self.get_selected_paths():
            if path not in staged_paths:
                staged_paths.append(path)

        self.session.target_paths = staged_paths
        self.list_widget.clearSelection()
        self.update_details_panel()

    def select_all_photos(self) -> None:
        self.list_widget.selectAll()
        self.update_details_panel()

    def clear_photo_selection(self) -> None:
        self.list_widget.clearSelection()
        self.update_details_panel()

    def select_photos(self) -> None:
        file_paths = self._pick_photo_files("Choose Photos")

        if not file_paths:
            return

        self.session.selected_paths = file_paths
        self.populate_list()

    def populate_list(self) -> None:
        self.session = refresh_photo_workflow(
            self.session,
            self.loader,
        )
        self.session.thumbnail_items = build_thumbnail_item_data_list(
            self.session.loaded_photos
        )
        self._render_photo_list()

    def _render_photo_list(self) -> None:
        self.list_widget.clear()
        gps_header_added = False

        for item_data in self.session.thumbnail_items:
            if item_data.has_gps and not gps_header_added:
                self._build_gps_group_header_item()
                gps_header_added = True

            path = item_data.path
            icon = self.thumbnail_loader.load_icon(
                path,
                has_gps=item_data.has_gps,
            )

            item = QListWidgetItem(icon, item_data.filename)
            item.setData(THUMBNAIL_PATH_ROLE, str(path))
            item.setData(THUMBNAIL_LATITUDE_ROLE, item_data.latitude)
            item.setData(THUMBNAIL_LONGITUDE_ROLE, item_data.longitude)
            item.setToolTip(item_data.tooltip)
            item.setSizeHint(THUMBNAIL_ITEM_SIZE)
            self.list_widget.addItem(item)

        self._refresh_source_preview()
        self.update_details_panel()
        self._update_selection_metrics()

    def get_selected_paths(self) -> list[Path]:
        selected_items = self.list_widget.selectedItems()
        return [
            Path(path_text)
            for item in selected_items
            if (path_text := item.data(THUMBNAIL_PATH_ROLE)) is not None
        ]

    def _build_gps_group_header_item(self) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        item.setSizeHint(
            QSize(
                max(self.list_widget.viewport().width() - 24, THUMBNAIL_ITEM_SIZE.width()),
                GPS_HEADER_HEIGHT,
            )
        )
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, self._build_gps_group_header_widget())
        return item

    def _build_gps_group_header_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setFixedHeight(1)

        label = QLabel("Photos with GPS Coordinates")
        label.setObjectName("thumbnailGroupHeader")
        label.setWordWrap(False)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(line)
        layout.addWidget(label)
        return widget

    def reselect_paths(self, paths_to_select: list[Path]) -> None:
        reselect_paths(self.list_widget, paths_to_select)
        self._update_selection_metrics()

    def select_browser_paths(
        self,
        paths_to_select: list[Path],
        *,
        update_details: bool = True,
    ) -> None:
        self.reselect_paths(paths_to_select)
        if update_details:
            self.update_details_panel()

    def show_context_menu(self, position) -> None:
        item = self.list_widget.itemAt(position)

        if item is None:
            return

        if item.data(THUMBNAIL_PATH_ROLE) is None:
            return

        latitude = item.data(THUMBNAIL_LATITUDE_ROLE)
        longitude = item.data(THUMBNAIL_LONGITUDE_ROLE)

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
