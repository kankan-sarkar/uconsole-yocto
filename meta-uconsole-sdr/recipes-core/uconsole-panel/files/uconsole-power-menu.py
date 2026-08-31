#!/usr/bin/env python3
import subprocess
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

import uconsole_theme

# ---------------------------------------------------------
# UConsole Power Menu
# ---------------------------------------------------------
# Summoned by the hotkey daemon on a short press of the physical power
# button (uconsole-hotkey.py). Runs as root (same trust model as
# uconsole-panel) so Shut Down/Restart can call systemctl directly.


class PowerMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Power")
        self.setFixedWidth(320)
        self.setStyleSheet(uconsole_theme.build_qss())

        layout = QVBoxLayout()

        title = QLabel("POWER")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        shutdown_btn = QPushButton("Shut Down")
        shutdown_btn.clicked.connect(self._shutdown)
        layout.addWidget(shutdown_btn)

        restart_btn = QPushButton("Restart")
        restart_btn.clicked.connect(self._restart)
        layout.addWidget(restart_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        layout.addWidget(cancel_btn)

        self.setLayout(layout)

    def _shutdown(self):
        subprocess.run(["systemctl", "poweroff"], check=False)
        self.close()

    def _restart(self):
        subprocess.run(["systemctl", "reboot"], check=False)
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    menu = PowerMenu()
    menu.show()
    sys.exit(app.exec())
