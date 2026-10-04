import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory

from core.exiftool_wrapper import ExifToolWrapper
from core.runtime_paths import resource_path
from gui.main_window import MainWindow

MISSING_EXIFTOOL_MESSAGE = (
    "Photo GPS Editor needs ExifTool to read and write photo metadata, "
    "but ExifTool could not be found.\n\n"
    "Install ExifTool from https://exiftool.org "
    "(on Debian, Ubuntu, or Linux Mint: sudo apt install libimage-exiftool-perl), "
    "then start Photo GPS Editor again."
)


def exiftool_is_ready() -> bool:
    """
    Check for ExifTool before the main window opens.

    Without ExifTool every photo would fail to load with a low-level
    "file not found" error, so show one clear message instead.
    """
    if ExifToolWrapper().is_available():
        return True

    QMessageBox.critical(None, "ExifTool Not Found", MISSING_EXIFTOOL_MESSAGE)
    return False


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Photo GPS Editor")
    app.setOrganizationName("Photo GPS Editor")
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setWindowIcon(QIcon(str(resource_path("assets/app_icon_128.png"))))

    if not exiftool_is_ready():
        return 1

    window = MainWindow()
    window.show()
    # Backstop for quits that skip the window's close (e.g. system logout):
    # background work must stop before Qt shuts down.
    app.aboutToQuit.connect(window.stop_background_work)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
