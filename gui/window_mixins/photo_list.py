from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.background import CancelToken
from gui.presenters.thumbnail_items import build_thumbnail_item_data_list, reselect_paths
from gui.widgets.thumbnail_delegate import SHIMMER_ROLE
from services.models import WorkflowSession

THUMBNAIL_PATH_ROLE = Qt.UserRole
THUMBNAIL_LATITUDE_ROLE = Qt.UserRole + 1
THUMBNAIL_LONGITUDE_ROLE = Qt.UserRole + 2
# On group heading items: "no_gps" or "gps", so the Show filter can hide them.
GROUP_HEADER_ROLE = Qt.UserRole + 4
THUMBNAIL_ITEM_SIZE = QSize(170, 190)
GPS_HEADER_HEIGHT = 52
GPS_HEADER_MIN_WIDTH = THUMBNAIL_ITEM_SIZE.width()

# Thumbnails are built in batches so the grid fills in steadily and Cancel
# takes effect quickly. RAW previews within a batch are read in one go.
THUMBNAIL_BATCH_SIZE = 24

# Placeholder tiles only appear for thumbnails not ready after this long, so
# quick loads show thumbnails directly with no placeholder flash (milliseconds).
PLACEHOLDER_DELAY_MS = 300

# Shimmer animation frame interval (milliseconds); 40 ms is 25 frames a second.
SHIMMER_FRAME_MS = 40


class PhotoListMixin:
    def select_all_photos(self) -> None:
        """
        Select every photo currently shown (photos hidden by Show are skipped).
        """
        with QSignalBlocker(self.list_widget):
            self.list_widget.clearSelection()
            for item in self._photo_items():
                if not item.isHidden():
                    item.setSelected(True)
        self.update_details_panel()

    def clear_photo_selection(self) -> None:
        self.list_widget.clearSelection()
        self.update_details_panel()

    def remove_photos_from_browser_list(self) -> None:
        paths_to_remove = set(self.get_selected_paths())
        if not paths_to_remove:
            paths_to_remove = set(self.session.selected_paths)

        self._remove_browser_paths(paths_to_remove)

    def remove_all_photos_from_browser_list(self) -> None:
        self._remove_browser_paths(set(self.session.selected_paths))

    def _remove_browser_paths(self, paths_to_remove: set[Path]) -> None:
        if not paths_to_remove:
            return

        self.session.selected_paths = [
            path for path in self.session.selected_paths if path not in paths_to_remove
        ]
        self.session.target_paths = [
            path for path in self.session.target_paths if path not in paths_to_remove
        ]
        self.populate_list()

    def select_photos(self) -> None:
        file_paths = self._pick_photo_files("Choose Photos")

        if not file_paths:
            return

        self._clear_gps_edit_history()
        self.load_photos(file_paths)

    def load_photos(self, file_paths: list[Path]) -> None:
        """
        Read GPS data for newly chosen photos in the background, then show them.

        The current grid stays usable while this runs. Thumbnails are loaded
        afterwards, also in the background (see _start_thumbnail_job).
        """
        self.cancel_loading(update_indicator=False)
        self._gps_load_generation += 1
        generation = self._gps_load_generation
        token = CancelToken()
        self._gps_load_token = token
        paths = list(file_paths)
        workflow = self.workflow

        self.loading_indicator.begin(f"Reading GPS data for {len(paths)} photos…")

        def work() -> WorkflowSession | None:
            if token.cancelled:
                return None
            return workflow.refresh_photo_workflow(WorkflowSession(selected_paths=paths))

        def done(new_session: WorkflowSession | None) -> None:
            if generation != self._gps_load_generation or new_session is None:
                return
            self._gps_load_token = None
            # Keep the update list and source photo as they are now, including
            # any changes made while GPS data was being read.
            new_session.target_paths = list(self.session.target_paths)
            new_session.source_photo_info = self.session.source_photo_info
            new_session.source_photo_path = self.session.source_photo_path
            self.session = new_session
            self._render_current_photo_session()

        def failed(exc: BaseException) -> None:
            if generation != self._gps_load_generation:
                return
            self._gps_load_token = None
            self.loading_indicator.finish()
            QMessageBox.warning(
                self,
                "Could Not Load Photos",
                f"The photos could not be read:\n\n{exc}",
            )

        self.background.submit(work, done, failed)

    def cancel_loading(self, update_indicator: bool = True) -> None:
        """
        Stop any background loading. Thumbnails not loaded yet get a plain icon.
        """
        if self._gps_load_token is not None:
            self._gps_load_token.cancel()
            self._gps_load_token = None
            # Ignore the result if it arrives anyway.
            self._gps_load_generation += 1

        self._cancel_thumbnail_job(use_fallback_icons=True)
        if update_indicator:
            self.loading_indicator.finish()

    def populate_list(self) -> None:
        self._refresh_photo_session()
        self._render_current_photo_session()

    def _refresh_photo_session(self) -> None:
        self.session = self.workflow.refresh_photo_workflow(self.session)

    def _render_current_photo_session(self) -> None:
        self.session.thumbnail_items = build_thumbnail_item_data_list(
            self.session.loaded_photos
        )
        self._render_photo_list()

    def _render_photo_list(self) -> None:
        # The items are about to be replaced, so forget any still-loading ones.
        self._cancel_thumbnail_job(use_fallback_icons=False)
        pending: list[tuple[Path, QListWidgetItem, bool]] = []

        self.list_widget.setUpdatesEnabled(False)
        try:
            self.list_widget.clear()
            self._group_header_items = []
            self._grid_items_by_path = {}
            gps_header_added = False
            gps_count = sum(1 for item_data in self.session.thumbnail_items if item_data.has_gps)
            no_gps_count = len(self.session.thumbnail_items) - gps_count

            # Photos without GPS are listed first, under their own heading.
            if no_gps_count:
                self._build_group_header_item(
                    f"Photos without GPS Coordinates ({no_gps_count})",
                    with_divider=False,
                    group="no_gps",
                )

            for item_data in self.session.thumbnail_items:
                if item_data.has_gps and not gps_header_added:
                    self._build_group_header_item(
                        f"Photos with GPS Coordinates ({gps_count})",
                        with_divider=True,
                        group="gps",
                    )
                    gps_header_added = True

                path = item_data.path
                # Thumbnails already built are shown right away; the rest start
                # blank and are filled in by the background job.
                icon = self.thumbnail_loader.cached_icon(path, has_gps=item_data.has_gps)

                item = QListWidgetItem(
                    icon if icon is not None else self._blank_thumbnail_icon(),
                    item_data.filename,
                )
                if icon is None:
                    pending.append((path, item, item_data.has_gps))
                item.setData(THUMBNAIL_PATH_ROLE, str(path))
                self._grid_items_by_path[str(path)] = item
                item.setData(THUMBNAIL_LATITUDE_ROLE, item_data.latitude)
                item.setData(THUMBNAIL_LONGITUDE_ROLE, item_data.longitude)
                item.setToolTip(item_data.tooltip)
                item.setSizeHint(THUMBNAIL_ITEM_SIZE)
                self.list_widget.addItem(item)
        finally:
            self.list_widget.setUpdatesEnabled(True)

        self._apply_grid_filter()
        self._refresh_source_marker()
        self._refresh_pick_marks()
        self.update_details_panel()
        self._start_thumbnail_job(pending)

    def set_grid_filter(self, key: str) -> None:
        """
        Show all photos, only those needing GPS, or only those that have it.
        """
        self._grid_filter = key
        button = self.grid_filter_buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)
        self._apply_grid_filter()
        self.update_details_panel()

    def _apply_grid_filter(self) -> None:
        show_no_gps = self._grid_filter in ("all", "needs")
        show_gps = self._grid_filter in ("all", "has")

        with QSignalBlocker(self.list_widget):
            for item in self._photo_items():
                has_gps = item.data(THUMBNAIL_LATITUDE_ROLE) is not None
                hidden = not (show_gps if has_gps else show_no_gps)
                item.setHidden(hidden)
                if hidden:
                    # Hidden photos are never acted on, so don't keep them selected.
                    item.setSelected(False)

        for header in self._group_header_items:
            group = header.data(GROUP_HEADER_ROLE)
            header.setHidden(not (show_gps if group == "gps" else show_no_gps))

        self._refresh_thumbnail_group_header_sizes()

        # Say why the grid is empty instead of showing a blank box.
        any_visible = any(not item.isHidden() for item in self._photo_items())
        if any_visible:
            message = ""
        elif not self._grid_items_by_path:
            message = "No photos yet. Use Choose Photos to add some."
        elif self._grid_filter == "needs":
            message = "No photos need GPS. Every photo shown here has coordinates."
        else:
            message = "None of these photos have GPS yet."
        self.list_widget.set_empty_message(message)

    def _photo_items(self) -> list[QListWidgetItem]:
        return list(self._grid_items_by_path.values())

    def _selected_photo_items(self) -> list[QListWidgetItem]:
        return [
            item
            for item in self.list_widget.selectedItems()
            if item.data(THUMBNAIL_PATH_ROLE) is not None and not item.isHidden()
        ]

    def _start_thumbnail_job(self, pending: list[tuple[Path, QListWidgetItem, bool]]) -> None:
        """
        Build missing thumbnails in the background, filling in the grid batch
        by batch.
        """
        if not pending:
            if self._gps_load_token is None:
                self.loading_indicator.finish()
            return

        self._thumbnail_generation += 1
        generation = self._thumbnail_generation
        token = CancelToken()
        self._thumbnail_token = token
        self._pending_thumbnail_items = {
            str(path): (item, has_gps) for path, item, has_gps in pending
        }
        self._thumbnail_total = len(pending)

        self.loading_indicator.begin(
            f"Loading thumbnails… 0 of {self._thumbnail_total}",
            total=self._thumbnail_total,
        )
        self._placeholder_timer.start(PLACEHOLDER_DELAY_MS)

        paths = [path for path, _, _ in pending]
        batch_size = self.thumbnail_batch_size
        loader = self.thumbnail_loader
        background = self.background

        def work() -> None:
            # Runs on the background thread: only reads files and builds QImages.
            for start in range(0, len(paths), batch_size):
                if token.cancelled:
                    return
                images = loader.load_images(paths[start:start + batch_size])
                background.post(self._apply_thumbnail_batch, (generation, images))

        def finished(_result: object) -> None:
            self._thumbnail_job_finished(generation)

        background.submit(work, finished, finished)

    def _apply_thumbnail_batch(self, payload) -> None:
        """
        Put a batch of finished thumbnails into the grid (GUI thread).
        """
        generation, images = payload
        if generation != self._thumbnail_generation:
            return

        refresh_preview = False
        for path, image in images.items():
            entry = self._pending_thumbnail_items.pop(str(path), None)
            if entry is None:
                continue
            item, has_gps = entry
            item.setIcon(self.thumbnail_loader.icon_from_image(path, has_gps, image))
            item.setData(SHIMMER_ROLE, False)
            if item.isSelected():
                refresh_preview = True
            if path == self._location_source:
                self._refresh_source_card()

        done = self._thumbnail_total - len(self._pending_thumbnail_items)
        self.loading_indicator.set_progress(
            done,
            self._thumbnail_total,
            f"Loading thumbnails… {done} of {self._thumbnail_total}",
        )
        if not self._pending_thumbnail_items:
            self._stop_thumbnail_animation()
        if refresh_preview:
            # A selected photo's thumbnail arrived: update the inspector preview.
            self._refresh_selection_preview()

    def _thumbnail_job_finished(self, generation: int) -> None:
        if generation != self._thumbnail_generation:
            return
        # Anything still waiting (the job failed) gets a plain icon.
        self._cancel_thumbnail_job(use_fallback_icons=True)
        if self._gps_load_token is None:
            self.loading_indicator.finish()

    def _cancel_thumbnail_job(self, *, use_fallback_icons: bool) -> None:
        """
        Stop the thumbnail job and stop tracking its items.

        Args:
            use_fallback_icons:
                True to give items still waiting a plain icon. False when the
                items are about to be deleted anyway.
        """
        if self._thumbnail_token is not None:
            self._thumbnail_token.cancel()
            self._thumbnail_token = None
        # Ignore any batches that arrive later.
        self._thumbnail_generation += 1

        if use_fallback_icons:
            for item, has_gps in self._pending_thumbnail_items.values():
                item.setIcon(self.thumbnail_loader.fallback_icon_for(has_gps))
                item.setData(SHIMMER_ROLE, False)
        self._pending_thumbnail_items = {}
        self._stop_thumbnail_animation()

    def _show_thumbnail_placeholders(self) -> None:
        """
        Thumbnails are taking a while: show shimmering placeholder tiles.
        """
        if not self._pending_thumbnail_items:
            return
        for item, _ in self._pending_thumbnail_items.values():
            item.setData(SHIMMER_ROLE, True)
        self._shimmer_clock.start()
        self._shimmer_timer.start(SHIMMER_FRAME_MS)

    def _advance_shimmer(self) -> None:
        self.thumbnail_delegate.advance(self._shimmer_clock.restart())
        self.list_widget.viewport().update()

    def _stop_thumbnail_animation(self) -> None:
        self._placeholder_timer.stop()
        self._shimmer_timer.stop()

    def _blank_thumbnail_icon(self) -> QIcon:
        """
        A transparent icon, so waiting items keep their size in the grid.
        """
        if self._blank_icon is None:
            pixmap = QPixmap(self.list_widget.iconSize())
            pixmap.fill(Qt.transparent)
            self._blank_icon = QIcon(pixmap)
        return self._blank_icon

    def get_selected_paths(self) -> list[Path]:
        """
        The photos to act on: selected and currently shown in the grid.
        """
        return [
            Path(item.data(THUMBNAIL_PATH_ROLE))
            for item in self._selected_photo_items()
        ]

    def _build_group_header_item(
        self,
        title: str,
        *,
        with_divider: bool,
        group: str,
    ) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        item.setData(GROUP_HEADER_ROLE, group)
        item.setSizeHint(self._thumbnail_group_header_size())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(
            item,
            self._build_group_header_widget(title, with_divider=with_divider, group=group),
        )
        self._group_header_items.append(item)
        return item

    def _thumbnail_group_header_size(self) -> QSize:
        return QSize(
            max(self.list_widget.viewport().width(), GPS_HEADER_MIN_WIDTH),
            GPS_HEADER_HEIGHT,
        )

    def _refresh_thumbnail_group_header_sizes(self) -> None:
        for item in getattr(self, "_group_header_items", []):
            item.setSizeHint(self._thumbnail_group_header_size())
        self.list_widget.doItemsLayout()

    def _build_group_header_widget(
        self,
        title: str,
        *,
        with_divider: bool,
        group: str,
    ) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        # The divider separates a group from the one above it, so the first
        # group on the page goes without one.
        if with_divider:
            line = QFrame()
            line.setObjectName("groupDivider")
            line.setFixedHeight(1)
            layout.addWidget(line)

        # Green for "has GPS", amber for "needs GPS" (see styles.py).
        dot = QLabel("●")
        dot.setObjectName("groupDot")
        dot.setProperty("group", group)
        label = QLabel(title)
        label.setObjectName("thumbnailGroupHeader")
        label.setProperty("group", group)
        label.setWordWrap(False)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        title_row.addWidget(dot)
        title_row.addWidget(label)
        title_row.addStretch(1)
        layout.addLayout(title_row)
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

        has_gps = latitude is not None and longitude is not None

        copy_action = QAction("Copy GPS Coordinates", self)
        copy_action.setEnabled(has_gps)
        copy_action.triggered.connect(
            lambda: self.copy_gps_coordinates(latitude, longitude)
        )

        path = Path(item.data(THUMBNAIL_PATH_ROLE))
        use_action = QAction("Use This Location", self)
        use_action.setEnabled(has_gps)
        use_action.setToolTip("Put this photo's coordinates in New Location")
        use_action.triggered.connect(lambda: self.use_location_from_path(path))

        menu.addAction(copy_action)
        menu.addAction(use_action)
        menu.exec(self.list_widget.viewport().mapToGlobal(position))

    def copy_gps_coordinates(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> None:
        if latitude is None or longitude is None:
            return

        QApplication.clipboard().setText(f"{latitude:.6f}, {longitude:.6f}")

    def copy_selected_photo_gps_coordinates(self) -> None:
        coordinates = self._selected_browser_gps_coordinates()
        if coordinates is None:
            return

        latitude, longitude = coordinates
        self.copy_gps_coordinates(latitude, longitude)

    def _selected_browser_gps_coordinates(self) -> tuple[float, float] | None:
        selected_paths = self.get_selected_paths()
        if len(selected_paths) != 1:
            return None

        info = self.session.loaded_photo_infos.get(selected_paths[0])
        if (
            info is None
            or info.current_latitude is None
            or info.current_longitude is None
        ):
            return None

        return info.current_latitude, info.current_longitude
