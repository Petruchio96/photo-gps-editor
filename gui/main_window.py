"""
Main application window.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
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
from gui.window_mixins.destination_list import DestinationListMixin
from gui.window_mixins.source_editor import SourceEditorMixin
from services.models import OverwriteEntry, WorkflowSession


class MainWindow(
    SourceEditorMixin,
    DestinationListMixin,
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
        self._update_selection_metrics()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralSurface")
        self.setCentralWidget(central_widget)

        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(18)

        self.select_button = QPushButton("Select Photos")
        self.select_button.clicked.connect(self.select_photos)

        self.loaded_count_badge = QLabel("0 loaded")
        self.loaded_count_badge.setObjectName("metricBadge")

        self.selection_count_badge = QLabel("No selection")
        self.selection_count_badge.setObjectName("metricBadgeMuted")

        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        title_label = QLabel("Photo GPS Editor")
        title_label.setObjectName("windowTitle")

        subtitle_label = QLabel(
            "Review thumbnails, inspect coordinates, and write precise GPS metadata with a desktop-grade workflow."
        )
        subtitle_label.setObjectName("windowSubtitle")
        subtitle_label.setWordWrap(True)

        header_text_layout.addWidget(title_label)
        header_text_layout.addWidget(subtitle_label)
        header_layout.addLayout(header_text_layout, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(build_browser_panel(self))
        splitter.addWidget(build_editor_panel(self))
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([860, 420])

        outer_layout.addLayout(header_layout)
        outer_layout.addWidget(splitter, 1)

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("Select Photos...", self)
        open_action.triggered.connect(self.select_photos)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _apply_window_style(self) -> None:
        self.setStyleSheet(APP_STYLESHEET)
        self.apply_button.setObjectName("primaryButton")
        self._update_apply_button_text()

    def _update_source_mode_ui(self) -> None:
        using_photo_source = self.photo_source_radio.isChecked()
        self.source_mode_stack.setCurrentIndex(0 if using_photo_source else 1)
        self._update_apply_button_text()
        self.update_details_panel()

    def _update_selection_metrics(self) -> None:
        loaded_count = len(self.session.selected_paths)
        self.loaded_count_badge.setText(
            f"{loaded_count} loaded" if loaded_count else "0 loaded"
        )

        selected_count = len(self.list_widget.selectedItems())
        if selected_count == 0:
            self.selection_count_badge.setText("No selection")
        elif selected_count == 1:
            self.selection_count_badge.setText("1 selected")
        else:
            self.selection_count_badge.setText(f"{selected_count} selected")

        if loaded_count == 0:
            self.browser_hint.setText(
                "No destination photos loaded yet. Use Select Photos to populate the grid."
            )
        else:
            self.browser_hint.setText(
                "Tip: choose a source on the right, then use Shift or Ctrl to build the destination list on the left."
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
