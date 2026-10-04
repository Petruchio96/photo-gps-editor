"""
Application stylesheet constants.
"""

APP_STYLESHEET = """
QMainWindow, QWidget#centralSurface {
    background: #eef3f8;
    color: #162131;
}
QMenuBar {
    background: #f6f9fc;
    border-bottom: 1px solid #d6dfe8;
    padding: 4px 8px;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #dde8f3;
}
QMenu {
    background: #ffffff;
    border: 1px solid #d4dde7;
    padding: 6px;
}
QMenu::item {
    padding: 8px 16px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: #e4eef9;
}
QFrame#panel {
    background: #fbfdff;
    border: 1px solid #d6dfe8;
    border-radius: 18px;
}
QLabel#windowTitle {
    font-size: 28px;
    font-weight: 700;
    color: #102033;
}
QLabel#windowSubtitle {
    font-size: 13px;
    color: #556579;
}
QLabel#sectionTitle {
    font-size: 18px;
    font-weight: 700;
    color: #112033;
}
QLabel#sourceFileLabel {
    font-size: 13px;
    font-weight: 700;
    color: #162131;
    min-height: 22px;
}
QLabel#sourceSummary {
    color: #26425f;
    background: #eef4fb;
    border: 1px solid #d8e4f0;
    border-radius: 10px;
    padding: 10px 12px;
    font-weight: 600;
}
QLabel#sectionNote {
    color: #5a697c;
    font-size: 12px;
    line-height: 1.4em;
}
QLabel#sourceHint {
    color: #617084;
    background: #f5f8fb;
    border: 1px dashed #ccd7e2;
    border-radius: 12px;
    padding: 12px 14px;
}
QPushButton {
    background: #ffffff;
    color: #102033;
    border: 1px solid #cad6e2;
    border-radius: 10px;
    padding: 10px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #f3f8fe;
    border-color: #a9bfd7;
}
QPushButton:pressed {
    background: #e7f0fa;
}
QPushButton:disabled {
    color: #8c9aa8;
    background: #f5f7f9;
    border-color: #d7dee5;
}
QPushButton#accentButton {
    background: #d97706;
    color: white;
    border: 1px solid #d97706;
    padding: 12px 18px;
}
QPushButton#accentButton:disabled {
    color: #8c9aa8;
    background: #f5f7f9;
    border-color: #d7dee5;
}
QPushButton#accentButton:hover {
    background: #b85f00;
    border-color: #b85f00;
}
QPushButton#accentButton:pressed {
    background: #9a4f00;
    border-color: #9a4f00;
}
QPushButton#applyButton[tone="safe"] {
    background: #1f6feb;
    color: white;
    border-color: #1f6feb;
}
QPushButton#applyButton[tone="safe"]:disabled,
QPushButton#applyButton[tone="warning"]:disabled {
    color: #8c9aa8;
    background: #f5f7f9;
    border-color: #d7dee5;
}
QPushButton#applyButton[tone="safe"]:hover {
    background: #165dc5;
    border-color: #165dc5;
}
QPushButton#applyButton[tone="warning"] {
    background: #c24141;
    color: white;
    border-color: #c24141;
}
QPushButton#applyButton[tone="warning"]:hover {
    background: #a83333;
    border-color: #a83333;
}
QPushButton#applyButton[tone="warning"]:pressed {
    background: #8f2a2a;
    border-color: #8f2a2a;
}
QPushButton[tone="danger"] {
    background: #c24141;
    color: white;
    border-color: #c24141;
}
QPushButton[tone="danger"]:hover {
    background: #a83333;
    border-color: #a83333;
}
QPushButton[tone="danger"]:pressed {
    background: #8f2a2a;
    border-color: #8f2a2a;
}
QPushButton[tone="danger"]:disabled,
QPushButton[tone="primary"]:disabled,
QPushButton[tone="neutral"]:disabled {
    color: #8c9aa8;
    background: #f5f7f9;
    border-color: #d7dee5;
}
QPushButton[tone="primary"] {
    background: #e8f1ff;
    color: #1459bd;
    border-color: #8cb7f0;
}
QPushButton[tone="primary"]:hover {
    background: #dcebff;
    border-color: #6ea1e8;
}
QPushButton[tone="primary"]:pressed {
    background: #c8ddff;
    border-color: #4f8be0;
}
QPushButton[tone="neutral"] {
    background: #ffffff;
    color: #102033;
    border: 1px solid #cad6e2;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #d8e1ea;
    border-radius: 14px;
    margin-top: 12px;
    padding: 14px 16px 16px 16px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #31445a;
}
QLineEdit {
    min-height: 36px;
    padding: 0 12px;
    background: #ffffff;
    border: 1px solid #cdd8e3;
    border-radius: 10px;
    selection-background-color: #c8ddff;
}
QLineEdit:focus {
    border: 1px solid #1f6feb;
}
QLabel#sourceThumbnail {
    background: #f7fafc;
    border: 1px solid #d8e1ea;
    border-radius: 14px;
    padding: 10px;
}
QRadioButton {
    color: #23384f;
    spacing: 8px;
    font-weight: 600;
}
QListWidget#selectedPhotosList {
    background: #ffffff;
    border: 1px solid #d8e1ea;
    border-radius: 12px;
    padding: 8px;
    outline: none;
}
QLabel#selectedPhotosEmpty {
    color: #617084;
    background: #ffffff;
    border: 1px dashed #ccd7e2;
    border-radius: 12px;
    padding: 16px;
}
QListWidget#thumbnailGrid {
    background: #ffffff;
    border: 1px solid #d8e1ea;
    border-radius: 16px;
    padding: 12px;
    outline: none;
}
QListWidget#thumbnailGrid::item {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px;
    margin: 4px;
}
QListWidget#thumbnailGrid::item:hover {
    background: #f4f8fc;
    border-color: #d5e2ef;
}
QListWidget#thumbnailGrid::item:selected {
    background: #dcebff;
    border-color: #8cb7f0;
    color: #0b2441;
}
QLabel#thumbnailGroupHeader {
    color: #4d6177;
    font-weight: 600;
    padding-left: 2px;
}
QListWidget#thumbnailGrid QScrollBar:vertical,
QListWidget#selectedPhotosList QScrollBar:vertical {
    background: #eef3f8;
    width: 14px;
    margin: 8px 2px 8px 2px;
    border-radius: 7px;
}
QListWidget#thumbnailGrid QScrollBar::handle:vertical,
QListWidget#selectedPhotosList QScrollBar::handle:vertical {
    background: #c4cfdb;
    min-height: 36px;
    border-radius: 7px;
}
QListWidget#thumbnailGrid QScrollBar::handle:vertical:hover,
QListWidget#selectedPhotosList QScrollBar::handle:vertical:hover {
    background: #b3c0ce;
}
QListWidget#thumbnailGrid QScrollBar::add-line:vertical,
QListWidget#thumbnailGrid QScrollBar::sub-line:vertical,
QListWidget#selectedPhotosList QScrollBar::add-line:vertical,
QListWidget#selectedPhotosList QScrollBar::sub-line:vertical {
    background: transparent;
    height: 0px;
}
QListWidget#thumbnailGrid QScrollBar::add-page:vertical,
QListWidget#thumbnailGrid QScrollBar::sub-page:vertical,
QListWidget#selectedPhotosList QScrollBar::add-page:vertical,
QListWidget#selectedPhotosList QScrollBar::sub-page:vertical {
    background: transparent;
}
QListWidget#thumbnailGrid QScrollBar:horizontal,
QListWidget#selectedPhotosList QScrollBar:horizontal {
    background: #eef3f8;
    height: 14px;
    margin: 2px 8px 2px 8px;
    border-radius: 7px;
}
QListWidget#thumbnailGrid QScrollBar::handle:horizontal,
QListWidget#selectedPhotosList QScrollBar::handle:horizontal {
    background: #c4cfdb;
    min-width: 36px;
    border-radius: 7px;
}
QListWidget#thumbnailGrid QScrollBar::handle:horizontal:hover,
QListWidget#selectedPhotosList QScrollBar::handle:horizontal:hover {
    background: #b3c0ce;
}
QListWidget#thumbnailGrid QScrollBar::add-line:horizontal,
QListWidget#thumbnailGrid QScrollBar::sub-line:horizontal,
QListWidget#selectedPhotosList QScrollBar::add-line:horizontal,
QListWidget#selectedPhotosList QScrollBar::sub-line:horizontal {
    background: transparent;
    width: 0px;
}
QListWidget#thumbnailGrid QScrollBar::add-page:horizontal,
QListWidget#thumbnailGrid QScrollBar::sub-page:horizontal,
QListWidget#selectedPhotosList QScrollBar::add-page:horizontal,
QListWidget#selectedPhotosList QScrollBar::sub-page:horizontal {
    background: transparent;
}
QLabel#browserHint {
    color: #617084;
    background: #f5f8fb;
    border: 1px dashed #ccd7e2;
    border-radius: 12px;
    padding: 12px 14px;
}
QLabel#statusCard {
    border-radius: 14px;
    padding: 14px 16px;
    font-weight: 600;
    border: 1px solid #d6e1ec;
    background: #edf4fb;
    color: #21476b;
}
QLabel#statusCard[tone="success"] {
    background: #edf8f1;
    color: #1d6a3d;
    border-color: #cfe9d8;
}
QLabel#statusCard[tone="error"] {
    background: #fff1f1;
    color: #9d2b2b;
    border-color: #efc8c8;
}
QLabel#statusCard[tone="info"] {
    background: #edf4fb;
    color: #21476b;
    border-color: #d6e1ec;
}
QLabel#browserHint[tone="success"] {
    color: #1f6b3a;
    background: #edf8f1;
    border: 1px solid #b9dfc6;
}
QLabel#browserHint[tone="error"] {
    color: #9b2c2c;
    background: #fdf1f1;
    border: 1px solid #efc4c4;
}
QLabel#filterLabel {
    color: #556579;
    font-weight: 600;
}
QPushButton#filterButton {
    background: #ffffff;
    color: #31445a;
    border: 1px solid #cad6e2;
    border-radius: 0px;
    padding: 6px 14px;
    font-weight: 600;
}
QPushButton#filterButton[segment="first"] {
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
}
QPushButton#filterButton[segment="middle"],
QPushButton#filterButton[segment="last"] {
    border-left: none;
}
QPushButton#filterButton[segment="last"] {
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QPushButton#filterButton:hover {
    background: #f3f8fe;
}
QPushButton#filterButton:checked {
    background: #26425f;
    color: #ffffff;
    border-color: #26425f;
}
QLabel#selectionPreview {
    background: #f5f8fb;
    border: 1px solid #e1e8ef;
    border-radius: 12px;
}
QLabel#selectionPreview[empty="true"] {
    border: 1px dashed #ccd7e2;
}
QLabel#selectionGps {
    color: #31445a;
    font-size: 13px;
}
QLabel#applyHint {
    font-size: 12px;
    padding: 2px 2px;
}
QLabel#applyHint[tone="info"] {
    color: #617084;
}
QLabel#applyHint[tone="warning"] {
    color: #8a5300;
}
QLabel#applyHint[tone="error"] {
    color: #9b2c2c;
}
QPushButton#removeGpsButton {
    background: #ffffff;
    color: #b42f2f;
    border: 1px solid #e3b3b3;
    padding: 8px 14px;
}
QPushButton#removeGpsButton:hover {
    background: #fdf1f1;
    border-color: #c24141;
}
QPushButton#removeGpsButton:pressed {
    background: #f9e2e2;
}
QPushButton#removeGpsButton:disabled {
    color: #8c9aa8;
    background: #f5f7f9;
    border-color: #d7dee5;
}
QLabel#loadingText {
    color: #556579;
    font-size: 12px;
}
QProgressBar#loadingBar {
    background: #e3e9f0;
    border: none;
    border-radius: 3px;
}
QProgressBar#loadingBar::chunk {
    background: #d97706;
    border-radius: 3px;
}
QPushButton#loadingCancel {
    padding: 4px 12px;
}
QSplitter::handle {
    background: transparent;
    width: 10px;
}
"""
