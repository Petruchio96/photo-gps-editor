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
QLabel#destinationSummary {
    color: #28425d;
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
QLabel#metricBadge, QLabel#metricBadgeMuted {
    padding: 8px 12px;
    border-radius: 14px;
    font-weight: 600;
}
QLabel#metricBadge {
    background: #dcecff;
    color: #0f4d91;
    border: 1px solid #bfdbff;
}
QLabel#metricBadgeMuted {
    background: #edf2f7;
    color: #516174;
    border: 1px solid #dbe3eb;
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
QPushButton#primaryButton {
    background: #1f6feb;
    color: white;
    border-color: #1f6feb;
}
QPushButton#primaryButton:hover {
    background: #165dc5;
    border-color: #165dc5;
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
QListWidget#destinationList {
    background: #ffffff;
    border: 1px solid #d8e1ea;
    border-radius: 12px;
    padding: 8px;
    outline: none;
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
QSplitter::handle {
    background: transparent;
    width: 10px;
}
"""
