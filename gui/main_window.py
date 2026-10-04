"""
Main application window.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
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
from gui.styles import APP_STYLESHEET
from gui.thumbnail_loader import ThumbnailLoader
from gui.widgets.browser_panel import build_browser_panel
from gui.widgets.editor_panel import build_editor_panel
from gui.window_mixins.apply_workflow import ApplyWorkflowMixin
from gui.window_mixins.photo_list import PhotoListMixin
from gui.window_mixins.source_editor import SourceEditorMixin
from services.gps_edit_history import GpsEditHistory
from services.models import OverwriteEntry, WorkflowSession
from services.workflow_facade import PhotoWorkflowFacade

APP_VERSION = "1.1"

# QSettings key for the "Keep Backup Copies of Originals" option.
KEEP_BACKUPS_SETTING = "keep_backup_copies"


class MainWindow(
    SourceEditorMixin,
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
        self._syncing_target_selection = False
        self._last_status_message = ""
        self._last_status_tone = "info"
        self.gps_history = GpsEditHistory()

        self._build_ui()
        self._build_menu_bar()
        self._apply_window_style()
        self._clipboard = self.clipboard()
        self._clipboard.dataChanged.connect(self._update_clipboard_buttons)
        self._update_selection_metrics()
        self._update_clipboard_buttons()
        self._apply_backup_setting()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralSurface")
        self.setCentralWidget(central_widget)

        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(20, 18, 20, 20)
        outer_layout.setSpacing(12)

        self.select_button = QPushButton("Choose Photos")
        self.select_button.setObjectName("accentButton")
        self.select_button.clicked.connect(self.select_photos)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(build_browser_panel(self))
        splitter.addWidget(build_editor_panel(self))
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([860, 420])

        outer_layout.addWidget(splitter, 1)

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

        self.copy_action = QAction("Copy", self)
        self.copy_action.setEnabled(False)
        self.copy_action.triggered.connect(self.copy_selected_photo_gps_coordinates)
        edit_menu.addAction(self.copy_action)

        self.paste_action = QAction("Paste", self)
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

    def _apply_window_style(self) -> None:
        self.setStyleSheet(APP_STYLESHEET)
        self._update_apply_button_text()

    def _update_source_mode_ui(self) -> None:
        using_photo_source = self.photo_source_radio.isChecked()
        self.source_mode_stack.setCurrentIndex(0 if using_photo_source else 1)
        self._update_apply_button_text()
        self.update_details_panel()

    def _update_selection_metrics(self) -> None:
        loaded_count = len(self.session.selected_paths)
        selected_count = len(self.get_selected_paths())
        removes_partial_selection = 0 < selected_count < loaded_count
        gps_count = sum(1 for item in self.session.thumbnail_items if item.has_gps)
        needs_gps_count = max(0, loaded_count - gps_count)

        if loaded_count == 0:
            self.browser_hint.setText(
                "No photos loaded yet. Use Choose Photos to populate the grid."
            )
        else:
            self.browser_hint.setText(
                f"{loaded_count} photos loaded. {needs_gps_count} need GPS; "
                f"{gps_count} already have GPS. Use Shift or Ctrl to select photos."
            )

        self.select_all_button.setEnabled(loaded_count > 0)
        self.clear_selection_button.setEnabled(selected_count > 0)
        if hasattr(self, "remove_photos_action"):
            self.remove_photos_action.setEnabled(loaded_count > 0)
        if hasattr(self, "copy_action"):
            self.copy_action.setEnabled(self._selected_browser_gps_coordinates() is not None)
        self.remove_loaded_photos_button.setEnabled(loaded_count > 0)
        self.remove_loaded_photos_button.setProperty(
            "tone",
            "primary" if loaded_count > 0 else "neutral",
        )
        self.remove_loaded_photos_button.setText(
            "Remove Selected Photos" if removes_partial_selection else "Remove All Photos"
        )
        self.remove_loaded_photos_button.style().unpolish(self.remove_loaded_photos_button)
        self.remove_loaded_photos_button.style().polish(self.remove_loaded_photos_button)
        self.remove_loaded_photos_button.update()
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
