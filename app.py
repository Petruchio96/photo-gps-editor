import sys
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel("Photo GPS Editor is ready")
label.resize(320, 80)
label.show()
sys.exit(app.exec())