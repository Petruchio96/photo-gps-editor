import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyleFactory

from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Photo GPS Editor")
    app.setOrganizationName("Photo GPS Editor")
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setWindowIcon(QIcon("assets/app_icon_128.png"))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
