"""
Main application window.
"""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.file_types import file_dialog_patterns
from core.runtime_paths import resource_path
from gui.background import BackgroundRunner
from gui.styles import APP_STYLESHEET
from gui.thumbnail_loader import ThumbnailLoader
from gui.widgets.browser_panel import build_browser_panel
from gui.widgets.editor_panel import build_editor_panel
from gui.window_mixins.apply_workflow import ApplyWorkflowMixin
from gui.window_mixins.inspector import InspectorMixin
from gui.window_mixins.location_editor import LocationEditorMixin
from gui.window_mixins.photo_list import THUMBNAIL_BATCH_SIZE, PhotoListMixin
from services.gps_edit_history import GpsEditHistory
from services.models import OverwriteEntry, WorkflowSession
from services.workflow_facade import PhotoWorkflowFacade

APP_VERSION = "1.1"

# QSettings key for the "Keep Backup Copies of Originals" option.
KEEP_BACKUPS_SETTING = "keep_backup_copies"

# How long an action message (e.g. "Applied GPS to 3 photos. Undo") stays in
# the status row under the grid before the photo counts come back.
STATUS_MESSAGE_MS = 12000


class MainWindow(
    InspectorMixin,
    LocationEditorMixin,
    PhotoListMixin,
    ApplyWorkflowMixin,
    QMainWindow,
):
    """
    Main application window.

    This class focuses on window setup and shared Qt-level concerns while
    mixins handle the larger groups of UI actions.
    """

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()

        # Saved preferences. Tests pass their own QSettings to stay isolated.
        self.settings = settings if settings is not None else QSettings()

        self.setWindowTitle("Photo GPS Editor")
        self.resize(1500, 920)
        self.setMinimumSize(1280, 820)

        self.workflow = PhotoWorkflowFacade()
        self.exiftool = self.workflow.writer
        self.loader = self.workflow.loader
        self.thumbnail_loader = ThumbnailLoader(
            thumbnail_size=128,
            preview_reader=self.workflow.read_embedded_previews,
        )

        self.session = WorkflowSession()
        self._is_splitting_manual_coordinates = False
        # Where the New Location came from (a photo), and pick-mode state.
        self._location_source = None
        self._picking_location = False
        self._filter_before_pick = None
        # While picking: True when some photos lack GPS, so "All" is disabled.
        self._pick_hides_all_filter = False
        self._last_status_message = ""
        self._last_status_tone = "info"
        self._status_undo_link = False
        self.gps_history = GpsEditHistory()

        # Photo grid state: Show filter ("all", "needs", "has") and the items.
        self._grid_filter = "all"
        self._grid_items_by_path = {}
        self._group_header_items = []

        # Background loading state (see PhotoListMixin.load_photos and
        # _start_thumbnail_job). Generation numbers let late results from a
        # cancelled or replaced load be recognized and ignored.
        self.background = BackgroundRunner()
        self.thumbnail_batch_size = THUMBNAIL_BATCH_SIZE
        self._gps_load_generation = 0
        self._gps_load_token = None
        self._thumbnail_generation = 0
        self._thumbnail_token = None
        self._thumbnail_total = 0
        self._pending_thumbnail_items = {}
        self._blank_icon = None

        self._build_ui()
        self._build_menu_bar()
        self._build_loading_timers()

        # Esc leaves pick mode (Copy from Photo on Left; only active while picking).
        self._pick_escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._pick_escape_shortcut.setEnabled(False)
        self._pick_escape_shortcut.activated.connect(self.stop_picking_location)
        self._apply_window_style()
        self._clipboard = self.clipboard()
        self._clipboard.dataChanged.connect(self._update_clipboard_buttons)
        self._apply_backup_setting()
        self._apply_grid_filter()
        self.update_details_panel()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralSurface")
        self.setCentralWidget(central_widget)

        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(20, 18, 20, 20)
        outer_layout.setSpacing(12)

        self.select_button = QPushButton("Choose Photos")
        self.select_button.clicked.connect(self.select_photos)

        outer_layout.addWidget(self._build_app_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(build_browser_panel(self))
        splitter.addWidget(build_editor_panel(self))
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([860, 420])

        outer_layout.addWidget(splitter, 1)

    def _build_app_header(self) -> QFrame:
        """
        Slim navy bar across the top with the app icon and name.
        """
        header = QFrame()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setPixmap(QIcon(str(resource_path("assets/app_icon_128.png"))).pixmap(32, 32))
        title = QLabel("Photo GPS Editor")
        title.setObjectName("appHeaderTitle")
        subtitle = QLabel("Select photos, set a location, apply.")
        subtitle.setObjectName("appHeaderSubtitle")

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        return header

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self.open_action = QAction("Choose Photos...", self)
        self.open_action.triggered.connect(self.select_photos)
        file_menu.addAction(self.open_action)

        self.remove_photos_action = QAction("Remove Photos", self)
        self.remove_photos_action.setEnabled(False)
        self.remove_photos_action.triggered.connect(self.remove_all_photos_from_browser_list)
        file_menu.addAction(self.remove_photos_action)

        file_menu.addSeparator()

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcuts(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        edit_menu = self.menuBar().addMenu("&Edit")

        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcuts(QKeySequence.StandardKey.Undo)
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo_gps_edit)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcuts(QKeySequence.StandardKey.Redo)
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.redo_gps_edit)
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        self.select_all_action = QAction("Select All Photos", self)
        self.select_all_action.setEnabled(False)
        self.select_all_action.triggered.connect(self.select_all_photos)
        edit_menu.addAction(self.select_all_action)

        edit_menu.addSeparator()

        self.copy_action = QAction("Copy GPS Coordinates", self)
        self.copy_action.setEnabled(False)
        self.copy_action.triggered.connect(self.copy_selected_photo_gps_coordinates)
        edit_menu.addAction(self.copy_action)

        self.paste_action = QAction("Paste Coordinates", self)
        self.paste_action.setEnabled(False)
        self.paste_action.triggered.connect(self.paste_coordinates_from_clipboard)
        edit_menu.addAction(self.paste_action)

        edit_menu.addSeparator()

        self.keep_backups_action = QAction("Keep Backup Copies of Originals", self)
        self.keep_backups_action.setCheckable(True)
        self.keep_backups_action.setToolTip(
            "Before a photo is first changed, save an untouched copy next to it "
            'with "_original" added to the file name.'
        )
        self.keep_backups_action.setChecked(
            self.settings.value(KEEP_BACKUPS_SETTING, False, type=bool)
        )
        self.keep_backups_action.toggled.connect(self.set_keep_backups)
        edit_menu.addAction(self.keep_backups_action)

        help_menu = self.menuBar().addMenu("&Help")

        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(self.about_action)

    def _build_loading_timers(self) -> None:
        # Shows placeholder tiles if thumbnails are not ready quickly.
        self._placeholder_timer = QTimer(self)
        self._placeholder_timer.setSingleShot(True)
        self._placeholder_timer.timeout.connect(self._show_thumbnail_placeholders)

        # Drives the shimmer animation while placeholders are shown.
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.timeout.connect(self._advance_shimmer)
        self._shimmer_clock = QElapsedTimer()

    def closeEvent(self, event) -> None:
        self.stop_background_work()
        super().closeEvent(event)

    def stop_background_work(self) -> None:
        """
        Stop background loading and wait for the batch in progress, so no
        background work is still using Qt when the app shuts down.
        """
        self.cancel_loading(update_indicator=False)
        self.background.shutdown()

    def _apply_window_style(self) -> None:
        self.setStyleSheet(APP_STYLESHEET)

        # Clears an action message from the status row after a while.
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status_message)

    def _set_status_message(self, message: str, tone: str = "info", *, undo: bool = False) -> None:
        """
        Show a message in the status row under the grid.

        Args:
            message:
                What happened, for example "Applied GPS to 3 photos."
            tone:
                "success", "error", or "info"; sets the color.
            undo:
                True to add an Undo link after the message.
        """
        self._last_status_message = message
        self._last_status_tone = tone
        self._status_undo_link = undo
        self._status_timer.start(STATUS_MESSAGE_MS)
        self._update_status_row()

    def _clear_status_message(self) -> None:
        self._last_status_message = ""
        self._last_status_tone = "info"
        self._status_undo_link = False
        self._update_status_row()

    def _handle_status_link(self, link: str) -> None:
        if link == "undo":
            self.undo_gps_edit()

    def _update_status_row(self) -> None:
        """
        Show the latest action message, or the photo counts if there is none.
        """
        if self._last_status_message:
            text = html.escape(self._last_status_message, quote=False)
            if self._status_undo_link and self.gps_history.can_undo:
                text += '&nbsp;&nbsp;<a href="undo">Undo</a>'
            tone = self._last_status_tone
        else:
            text = html.escape(self._photo_count_summary(), quote=False)
            tone = "info"

        self.browser_hint.setText(text)
        if self.browser_hint.property("tone") != tone:
            self.browser_hint.setProperty("tone", tone)
            self.browser_hint.style().unpolish(self.browser_hint)
            self.browser_hint.style().polish(self.browser_hint)

    def _photo_count_summary(self) -> str:
        loaded_count = len(self.session.selected_paths)
        if loaded_count == 0:
            return "No photos loaded yet. Use Choose Photos to add some."

        gps_count = sum(1 for item in self.session.thumbnail_items if item.has_gps)
        needs_gps_count = max(0, loaded_count - gps_count)
        return (
            f"{loaded_count} photos loaded: {needs_gps_count} need GPS, "
            f"{gps_count} have GPS. Shift-click or Ctrl-click to select several."
        )

    def _update_selection_metrics(self) -> None:
        loaded_count = len(self.session.selected_paths)
        selected_count = len(self.get_selected_paths())
        removes_partial_selection = 0 < selected_count < loaded_count
        gps_count = sum(1 for item in self.session.thumbnail_items if item.has_gps)
        needs_gps_count = max(0, loaded_count - gps_count)

        self._update_status_row()
        for key, label, count in (
            ("all", "All", loaded_count),
            ("needs", "Needs GPS", needs_gps_count),
            ("has", "Has GPS", gps_count),
        ):
            self.grid_filter_buttons[key].setText(f"{label} ({count})")

        self.select_all_button.setEnabled(loaded_count > 0)
        if hasattr(self, "select_all_action"):
            self.select_all_action.setEnabled(loaded_count > 0)
        self.clear_selection_button.setEnabled(selected_count > 0)
        if hasattr(self, "remove_photos_action"):
            self.remove_photos_action.setEnabled(loaded_count > 0)
        if hasattr(self, "copy_action"):
            self.copy_action.setEnabled(self._selected_browser_gps_coordinates() is not None)
        self.remove_loaded_photos_button.setEnabled(loaded_count > 0)
        self.remove_loaded_photos_button.setText(
            "Remove Selected from List" if removes_partial_selection else "Remove All from List"
        )
        self._update_undo_redo_actions()

    def _gps_states_for_paths(
        self,
        paths: list[Path],
    ) -> dict[Path, tuple[float | None, float | None]]:
        states: dict[Path, tuple[float | None, float | None]] = {}
        for path in paths:
            info = self.session.loaded_photo_infos.get(path)
            if info is None:
                states[path] = (None, None)
            else:
                states[path] = (info.current_latitude, info.current_longitude)
        return states

    def _remember_gps_edit(
        self,
        *,
        before_states: dict[Path, tuple[float | None, float | None]],
        after_states: dict[Path, tuple[float | None, float | None]],
    ) -> None:
        self.gps_history.record(before=before_states, after=after_states)
        self._update_undo_redo_actions()

    def _clear_gps_edit_history(self) -> None:
        self.gps_history.clear()
        self._update_undo_redo_actions()

    def _update_undo_redo_actions(self) -> None:
        if hasattr(self, "undo_action"):
            self.undo_action.setEnabled(self.gps_history.can_undo)
        if hasattr(self, "redo_action"):
            self.redo_action.setEnabled(self.gps_history.can_redo)
        self._apply_pick_mode_lock()

    def undo_gps_edit(self) -> None:
        states = self.gps_history.undo_states()
        if not states:
            return

        failed_paths = self._restore_gps_states(states)
        self.gps_history.mark_undone()
        self._update_undo_redo_actions()
        self._report_write_failures("undo the GPS change for", failed_paths)
        self._set_status_message("GPS change undone.", "info")

    def redo_gps_edit(self) -> None:
        states = self.gps_history.redo_states()
        if not states:
            return

        failed_paths = self._restore_gps_states(states)
        self.gps_history.mark_redone()
        self._update_undo_redo_actions()
        self._report_write_failures("redo the GPS change for", failed_paths)
        self._set_status_message("GPS change redone.", "info")

    def _restore_gps_states(
        self,
        states: dict[Path, tuple[float | None, float | None]],
    ) -> list[str]:
        """
        Write remembered GPS states back to files. Returns failure messages.
        """
        result = self.workflow.restore_gps_states_workflow(
            session=self.session,
            states=states,
        )
        self.session = result.session
        self._render_current_photo_session()
        self.list_widget.clearSelection()
        self.update_details_panel()
        return list(result.execution_result.failed_paths)

    def _report_write_failures(self, action: str, failed_paths: list[str]) -> None:
        """
        Tell the user which files could not be changed, if any.

        Args:
            action:
                Completes the sentence "Could not <action> N photo(s).",
                for example "apply GPS to".
            failed_paths:
                One "file name: reason" entry per failed file.
        """
        if not failed_paths:
            return

        self._set_status_message(
            f"Could not {action} {len(failed_paths)} photo(s).",
            "error",
        )
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Some Photos Were Not Changed")
        dialog.setText(f"Could not {action} {len(failed_paths)} photo(s).")
        dialog.setInformativeText(
            "The other photos were changed. Show Details lists each file and the reason."
        )
        dialog.setDetailedText("\n".join(failed_paths))
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec()

    def set_keep_backups(self, keep_backups: bool) -> None:
        """
        Turn backup copies on or off, and remember the choice.
        """
        self.settings.setValue(KEEP_BACKUPS_SETTING, keep_backups)
        self._apply_backup_setting()

    def _apply_backup_setting(self) -> None:
        # The writer is ExifToolWrapper in the app; test fakes simply ignore it.
        self.workflow.writer.keep_backups = self.keep_backups_action.isChecked()

    def _default_photo_directory(self) -> Path:
        pictures_dir = Path.home() / "Pictures"
        return pictures_dir if pictures_dir.exists() else Path.home()

    def _photo_file_filter(self) -> str:
        return f"Images ({file_dialog_patterns()})"

    def _pick_photo_files(self, title: str) -> list[Path]:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            title,
            str(self._default_photo_directory()),
            self._photo_file_filter(),
        )
        return [Path(path) for path in file_paths]

    def _pick_photo_file(self, title: str) -> Path | None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(self._default_photo_directory()),
            self._photo_file_filter(),
        )
        if not file_path:
            return None

        return Path(file_path)

    def _format_overwrite_entries(
        self,
        overwrite_entries: list[OverwriteEntry],
    ) -> list[str]:
        return [entry.display_text() for entry in overwrite_entries]

    def show_about_dialog(self) -> None:
        self._build_about_dialog().exec()

    def _build_about_dialog(self) -> QMessageBox:
        repo_url = "https://github.com/Petruchio96/photo-gps-editor"
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle(f"About Photo GPS Editor {APP_VERSION}")
        about_dialog.setIconPixmap(
            QIcon(str(resource_path("assets/app_icon_128.png"))).pixmap(64, 64)
        )
        about_dialog.setStandardButtons(QMessageBox.Ok)

        link_label = QLabel(
            (
                f"<p><strong>Photo GPS Editor {APP_VERSION}</strong></p>"
                "<p>A desktop application for viewing photo GPS metadata, "
                "copying coordinates, and applying GPS data to one or more selected files.</p>"
                "<p>Instructions and more information:<br>"
                f'<a href="{repo_url}">{repo_url}</a></p>'
            )
        )
        link_label.setObjectName("aboutRepositoryLink")
        link_label.setTextFormat(Qt.RichText)
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_label.setOpenExternalLinks(True)
        link_label.setWordWrap(True)
        link_label.setMinimumWidth(360)

        about_dialog.layout().addWidget(
            link_label,
            0,
            1,
            1,
            about_dialog.layout().columnCount(),
        )
        about_dialog.setMinimumWidth(520)
        return about_dialog

    def clipboard(self):
        return QApplication.clipboard()
