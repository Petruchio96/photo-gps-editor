"""
Browser panel UI builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QItemSelectionModel, QPoint, QRect, QSignalBlocker, QSize, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRubberBand,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.loading_indicator import LoadingIndicator
from gui.widgets.thumbnail_delegate import PICK_DISABLED_ROLE, ThumbnailDelegate
from gui.window_mixins.photo_list import THUMBNAIL_PATH_ROLE

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ThumbnailGrid(QListWidget):
    """
    The photo grid, with click-to-add selection.

    Selection rules (the photos selected are the photos to change):
        - Click (or Ctrl+click) a photo: add it, or remove it if selected.
        - Shift+click: add every photo shown between the last clicked photo
          and this one (photos hidden by the Show filter are skipped).
        - Drag a box from empty space: add the photos inside it.
        - Click empty space: nothing. Ctrl+A: select every photo shown.
        - Arrow keys move the focus without changing the selection; Space
          adds or removes the focused photo.
    Pick mode and right-click are handled separately and never change the
    selection.

    It also keeps full-width section rows sized correctly after resizing.
    """

    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self._window = window
        # Shown in the middle of the grid when no photos are visible.
        self.empty_message = ""
        # Shift+click ranges start here: the path of the last photo clicked.
        self._anchor_path: str | None = None
        # Drag-box state.
        self._band: QRubberBand | None = None
        self._band_origin: QPoint | None = None
        self._band_base: set[str] = set()

    # --- Mouse --------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        # Pick mode: a click chooses the location source and never changes
        # which photos are selected for updating.
        if self._window.is_picking_location and event.button() == Qt.LeftButton:
            self._window.pick_location_from_item(self.itemAt(event.position().toPoint()))
            event.accept()
            return
        # Right-click opens the context menu for the photo under the cursor
        # without changing the selection (Qt would normally select it).
        if event.button() == Qt.RightButton:
            event.accept()
            return
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        position = event.position().toPoint()
        item = self._photo_item_at(position)
        self.setFocus(Qt.MouseFocusReason)
        if item is None:
            # Empty space (or a heading): keep the selection; maybe a drag box.
            self._band_origin = position
            self._band_base = self._selected_path_set()
        elif event.modifiers() & Qt.ShiftModifier:
            self._add_range_to(item)
        else:
            self._toggle(item)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        position = event.position().toPoint()
        # While picking, show a "not allowed" cursor over dimmed photos.
        if self._window.is_picking_location:
            item = self.itemAt(position)
            unpickable = item is not None and item.data(PICK_DISABLED_ROLE)
            self.viewport().setCursor(Qt.ForbiddenCursor if unpickable else Qt.CrossCursor)
            event.accept()
            return
        if self._band_origin is not None and event.buttons() & Qt.LeftButton:
            self._update_band(position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            # Our press handling already decided the selection; Qt's release
            # logic would otherwise collapse it to a single photo.
            self._end_band()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._window.is_picking_location or event.button() != Qt.LeftButton:
            event.accept()
            return
        # A double-click is two clicks: treat the second one like a click.
        self.mousePressEvent(event)

    # --- Keyboard -----------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        # Esc leaves pick mode when the grid has focus (the window-wide Esc
        # shortcut covers the rest of the window).
        if self._window.is_picking_location and event.key() == Qt.Key_Escape:
            self._window.stop_picking_location()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            if not self._window.is_picking_location:
                # Only photos currently shown, like the Select All button.
                self._window.select_all_photos()
            event.accept()
            return
        if event.key() == Qt.Key_Space and not self._window.is_picking_location:
            item = self.currentItem()
            if item is not None and item.data(THUMBNAIL_PATH_ROLE) is not None and not item.isHidden():
                self._toggle(item)
            event.accept()
            return
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                           Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown):
            # Move the focus only; never replace the selection.
            index = self.moveCursor(self._cursor_action_for(event.key()), event.modifiers())
            if index.isValid():
                self.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                self.scrollTo(index)
            event.accept()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _cursor_action_for(key):
        return {
            Qt.Key_Left: QAbstractItemView.MoveLeft,
            Qt.Key_Right: QAbstractItemView.MoveRight,
            Qt.Key_Up: QAbstractItemView.MoveUp,
            Qt.Key_Down: QAbstractItemView.MoveDown,
            Qt.Key_Home: QAbstractItemView.MoveHome,
            Qt.Key_End: QAbstractItemView.MoveEnd,
            Qt.Key_PageUp: QAbstractItemView.MovePageUp,
            Qt.Key_PageDown: QAbstractItemView.MovePageDown,
        }[key]

    # --- Selection helpers ---------------------------------------------------

    def _photo_item_at(self, position: QPoint) -> QListWidgetItem | None:
        item = self.itemAt(position)
        if item is None or item.isHidden() or item.data(THUMBNAIL_PATH_ROLE) is None:
            return None
        return item

    def _visible_photo_items(self) -> list[QListWidgetItem]:
        # Rows are in on-screen order (no-GPS group first, then GPS group).
        return [
            self.item(row)
            for row in range(self.count())
            if self.item(row).data(THUMBNAIL_PATH_ROLE) is not None and not self.item(row).isHidden()
        ]

    def _selected_path_set(self) -> set[str]:
        return {
            item.data(THUMBNAIL_PATH_ROLE)
            for item in self.selectedItems()
            if item.data(THUMBNAIL_PATH_ROLE) is not None
        }

    def _toggle(self, item: QListWidgetItem) -> None:
        self._anchor_path = item.data(THUMBNAIL_PATH_ROLE)
        self.setCurrentItem(item, QItemSelectionModel.NoUpdate)
        self._set_selected([item], not item.isSelected())

    def _add_range_to(self, item: QListWidgetItem) -> None:
        items = self._visible_photo_items()
        anchor = next(
            (candidate for candidate in items if candidate.data(THUMBNAIL_PATH_ROLE) == self._anchor_path),
            None,
        )
        self.setCurrentItem(item, QItemSelectionModel.NoUpdate)
        if anchor is None:
            # No starting photo (or it is hidden): just add this photo.
            self._anchor_path = item.data(THUMBNAIL_PATH_ROLE)
            self._set_selected([item], True)
            return
        first, last = sorted((items.index(anchor), items.index(item)))
        self._set_selected(items[first:last + 1], True)

    def _set_selected(self, items: list[QListWidgetItem], selected: bool) -> None:
        """
        Change several items at once, then update the window once.
        """
        changed = False
        with QSignalBlocker(self):
            for item in items:
                if item.isSelected() != selected:
                    item.setSelected(selected)
                    changed = True
        if changed:
            self.viewport().update()
            self._window.update_details_panel()

    def _update_band(self, position: QPoint) -> None:
        rect = QRect(self._band_origin, position).normalized()
        if self._band is None:
            if rect.width() < 4 and rect.height() < 4:
                return  # Not a drag yet, just a slightly wobbly click.
            self._band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self._band.setGeometry(rect)
        self._band.show()

        # Selection = what was selected before the drag + photos in the box.
        changed = False
        with QSignalBlocker(self):
            for item in self._visible_photo_items():
                wanted = (
                    item.data(THUMBNAIL_PATH_ROLE) in self._band_base
                    or self.visualItemRect(item).intersects(rect)
                )
                if item.isSelected() != wanted:
                    item.setSelected(wanted)
                    changed = True
        if changed:
            self.viewport().update()
            self._window.update_details_panel()

    def _end_band(self) -> None:
        if self._band is not None:
            self._band.hide()
            self._band.deleteLater()
            self._band = None
        self._band_origin = None
        self._band_base = set()

    def set_empty_message(self, message: str) -> None:
        if message != self.empty_message:
            self.empty_message = message
            self.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._window._refresh_thumbnail_group_header_sizes()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.empty_message:
            return
        painter = QPainter(self.viewport())
        painter.setPen(QColor("#7a8899"))
        font = QFont(painter.font())
        font.setPointSize(font.pointSize() + 2)
        painter.setFont(font)
        painter.drawText(self.viewport().rect(), Qt.AlignCenter | Qt.TextWordWrap, self.empty_message)
        painter.end()


# Show filter values, in button order.
GRID_FILTERS = (
    ("all", "All"),
    ("needs", "Needs GPS"),
    ("has", "Has GPS"),
)


def build_browser_panel(window: "MainWindow") -> QWidget:
    """
    Create the photo grid panel shown on the left side.
    """
    panel = QFrame()
    panel.setObjectName("panel")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)

    section_heading = QLabel("Photos")
    section_heading.setObjectName("sectionTitle")

    # Row 1: add/remove photos, and selection shortcuts.
    header_row = QHBoxLayout()
    header_row.setSpacing(10)
    window.select_button.setProperty("tone", "primary")
    header_row.addWidget(window.select_button)
    window.remove_loaded_photos_button = QPushButton("Remove All from List")
    window.remove_loaded_photos_button.setProperty("tone", "neutral")
    window.remove_loaded_photos_button.setEnabled(False)
    window.remove_loaded_photos_button.setToolTip(
        "Removes photos from this list only. Files are not changed or deleted."
    )
    window.remove_loaded_photos_button.clicked.connect(window.remove_photos_from_browser_list)
    header_row.addWidget(window.remove_loaded_photos_button)
    header_row.addStretch(1)

    window.select_all_button = QPushButton("Select All")
    window.select_all_button.setProperty("tone", "neutral")
    window.select_all_button.setToolTip("Select every photo currently shown")
    window.select_all_button.clicked.connect(window.select_all_photos)
    window.clear_selection_button = QPushButton("Clear Selection")
    window.clear_selection_button.setProperty("tone", "neutral")
    window.clear_selection_button.clicked.connect(window.clear_photo_selection)
    header_row.addWidget(window.select_all_button)
    header_row.addWidget(window.clear_selection_button)

    # Row 2: Show filter (All / Needs GPS / Has GPS), a segmented control.
    filter_row = QHBoxLayout()
    filter_row.setSpacing(0)
    show_label = QLabel("Show:")
    show_label.setObjectName("filterLabel")
    filter_row.addWidget(show_label)
    filter_row.addSpacing(10)
    window.grid_filter_group = QButtonGroup(panel)
    window.grid_filter_group.setExclusive(True)
    window.grid_filter_buttons = {}
    for position, (key, text) in enumerate(GRID_FILTERS):
        button = QPushButton(text)
        button.setObjectName("filterButton")
        button.setProperty("filter", key)
        button.setCheckable(True)
        button.setProperty(
            "segment",
            "first" if position == 0 else "last" if position == len(GRID_FILTERS) - 1 else "middle",
        )
        button.clicked.connect(lambda _checked=False, key=key: window.set_grid_filter(key))
        window.grid_filter_group.addButton(button)
        window.grid_filter_buttons[key] = button
        filter_row.addWidget(button)
    window.grid_filter_buttons["all"].setChecked(True)
    filter_row.addStretch(1)

    # Banner shown while picking a location source from the grid.
    window.pick_banner = QFrame()
    window.pick_banner.setObjectName("pickBanner")
    banner_layout = QHBoxLayout(window.pick_banner)
    banner_layout.setContentsMargins(14, 8, 8, 8)
    window.pick_banner_label = QLabel()
    window.pick_banner_label.setObjectName("pickBannerText")
    window.pick_banner_label.setWordWrap(True)
    banner_layout.addWidget(window.pick_banner_label, 1)
    window.pick_banner.hide()

    window.list_widget = ThumbnailGrid(window)
    window.list_widget.setObjectName("thumbnailGrid")
    window.list_widget.setViewMode(QListWidget.IconMode)
    window.list_widget.setIconSize(QSize(128, 128))
    window.list_widget.setResizeMode(QListWidget.Adjust)
    window.list_widget.setSpacing(12)
    window.list_widget.setWordWrap(True)
    window.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
    window.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
    # Mouse moves are needed (not just drags) for the pick-mode cursor.
    window.list_widget.setMouseTracking(True)
    # Tiles stay in place: no dragging them around the grid.
    window.list_widget.setMovement(QListWidget.Static)
    window.list_widget.setDragEnabled(False)
    window.list_widget.setDragDropMode(QListWidget.NoDragDrop)
    window.list_widget.itemSelectionChanged.connect(window.update_details_panel)
    window.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
    window.list_widget.customContextMenuRequested.connect(window.show_context_menu)
    window.list_widget.verticalScrollBar().setSingleStep(24)
    # Draws shimmering placeholders for thumbnails that are still loading.
    window.thumbnail_delegate = ThumbnailDelegate(window.list_widget)
    window.list_widget.setItemDelegate(window.thumbnail_delegate)

    # Status row under the grid: photo counts, action feedback (with Undo),
    # and the loading progress row, which takes its place while loading.
    window.browser_hint = QLabel(
        "No photos loaded yet. Use Choose Photos to add some."
    )
    window.browser_hint.setObjectName("browserHint")
    window.browser_hint.setWordWrap(True)
    window.browser_hint.setTextFormat(Qt.RichText)
    window.browser_hint.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
    window.browser_hint.linkActivated.connect(window._handle_status_link)

    window.loading_indicator = LoadingIndicator(window.browser_hint)
    window.loading_indicator.cancel_requested.connect(window.cancel_loading)

    layout.addWidget(section_heading)
    layout.addLayout(header_row)
    layout.addLayout(filter_row)
    layout.addWidget(window.pick_banner)
    layout.addWidget(window.list_widget, 1)
    layout.addWidget(window.loading_indicator)

    return panel
