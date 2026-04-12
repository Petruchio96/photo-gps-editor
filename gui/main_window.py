"""
Main application window.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
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

from core.exiftool_wrapper import ExifToolWrapper
from core.photo_loader import PhotoLoader
from core.thumbnail_loader import ThumbnailLoader
from gui.styles import APP_STYLESHEET
from gui.widgets.browser_panel import build_browser_panel
from gui.widgets.editor_panel import build_editor_panel
from gui.window_mixins.apply_workflow import ApplyWorkflowMixin
from gui.window_mixins.photo_list import PhotoListMixin
from gui.window_mixins.source_editor import SourceEditorMixin
from services.models import OverwriteEntry, WorkflowSession

APP_VERSION = "1.0"


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

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Photo GPS Editor")
        self.resize(1500, 920)
        self.setMinimumSize(1280, 820)

        self.exiftool = ExifToolWrapper()
        self.loader = PhotoLoader(self.exiftool)
        self.thumbnail_loader = ThumbnailLoader(thumbnail_size=128)

        self.session = WorkflowSession()
        self._is_splitting_manual_coordinates = False

        self._build_ui()
        self._build_menu_bar()
        self._apply_window_style()
        self._clipboard = self.clipboard()
        self._clipboard.dataChanged.connect(self._update_clipboard_buttons)
        self._update_selection_metrics()
        self._update_clipboard_buttons()

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

        file_menu.addSeparator()

        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

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
        selected_count = len(self.list_widget.selectedItems())

        if loaded_count == 0:
            self.browser_hint.setText(
                "No photos loaded yet. Use Choose Photos to populate the grid."
            )
        else:
            self.browser_hint.setText(
                "Tip: choose a source on the right, then use Shift or Ctrl to select the photos on the left."
            )

        self.select_all_button.setEnabled(loaded_count > 0)
        self.clear_selection_button.setEnabled(selected_count > 0)

    def _default_photo_directory(self) -> Path:
        pictures_dir = Path.home() / "Pictures"
        return pictures_dir if pictures_dir.exists() else Path.home()

    def _photo_file_filter(self) -> str:
        return "Images (*.jpg *.JPG *.jpeg *.JPEG *.cr2 *.CR2 *.cr3 *.CR3 *.dng *.DNG)"

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
        QMessageBox.about(
            self,
            f"About Photo GPS Editor {APP_VERSION}",
            (
                f"Photo GPS Editor {APP_VERSION}\n\n"
                "A desktop application for viewing photo GPS metadata, "
                "copying coordinates, and applying GPS data to one or more selected files."
            ),
        )

    def clipboard(self):
        return QApplication.clipboard()
