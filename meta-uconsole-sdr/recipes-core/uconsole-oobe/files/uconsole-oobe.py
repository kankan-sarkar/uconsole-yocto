#!/usr/bin/env python3
import sys
import os
import json
import shutil
import hashlib
import subprocess
import urllib.request

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QStackedWidget, QComboBox, QRadioButton,
    QButtonGroup, QFileDialog,
)
from PyQt6.QtCore import Qt

import uconsole_theme

PIN_FILE = "/etc/uconsole_pin.sha256"
FLAG_FILE = "/etc/.oobe_completed"
SETTINGS_FILE = uconsole_theme.SETTINGS_FILE
PROFILE_IMAGE_FILE = uconsole_theme.PROFILE_IMAGE_FILE
SPLASH_IMAGE_FILE = uconsole_theme.SPLASH_IMAGE_FILE

ACCENT_COLORS = {
    "Cyan": "#66fcf1",
    "Amber": "#f5a623",
    "Magenta": "#e91e8c",
    "Green": "#3ddc84",
}

SDR_APPS = ["GQRX", "SDRangel", "CubicSDR", "SDR++"]

# The wizard runs before settings.json exists, so this just renders
# uconsole_theme's default palette -- but it's the same call the lock
# screen and control panel make, so there's one definition of "the
# theme," not three copies that can drift.
THEME_QSS = uconsole_theme.build_qss()


def fetch_asset(source, dest):
    """Copy a local file or download a URL into dest. Best-effort."""
    if not source:
        return False
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if source.startswith("http://") or source.startswith("https://"):
            with urllib.request.urlopen(source, timeout=15) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out)
        else:
            shutil.copy(source, dest)
        return True
    except Exception as e:
        print(f"Failed to fetch asset {source}: {e}")
        return False


def sync_unix_password(plaintext_pin):
    """Make the root account password match the PIN, so unmodified
    sudo/PAM/polkit prompts ARE the PIN prompt (requirement.md 7.2)
    without needing a bespoke PAM module."""
    try:
        proc = subprocess.run(
            ["chpasswd"], input=f"root:{plaintext_pin}\n", text=True, check=True
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"Failed to sync unix password to PIN: {e}")
        return False


def connect_wifi(ssid, password):
    if not ssid:
        return
    try:
        subprocess.run(["nmcli", "device", "wifi", "connect", ssid, "password", password], check=False)
    except Exception as e:
        print(f"Failed to connect Wi-Fi: {e}")


class WizardPage(QWidget):
    def __init__(self, title, subtitle=""):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(20)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet("font-size: 14px; color: #c5c6c7;")
            sub_label.setWordWrap(True)
            self.layout.addWidget(sub_label)

        self.setLayout(self.layout)


class PinPage(WizardPage):
    def __init__(self):
        super().__init__(
            "UCONSOLE SYSTEM INITIALIZATION",
            "Establish your 5+ digit local root authority PIN. This also becomes "
            "your sudo/system password -- if it's lost, local administration is "
            "permanently locked out.",
        )
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setPlaceholderText("Enter 5+ digits")
        self.layout.addWidget(self.pin_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Confirm PIN")
        self.layout.addWidget(self.confirm_input)

    def validate(self):
        pin1, pin2 = self.pin_input.text(), self.confirm_input.text()
        if len(pin1) < 5 or not pin1.isdigit():
            QMessageBox.critical(self, "Error", "PIN must be at least 5 digits.")
            return None
        if pin1 != pin2:
            QMessageBox.critical(self, "Error", "PINs do not match.")
            return None
        return pin1


class ProfileImagePage(WizardPage):
    def __init__(self):
        super().__init__("PROFILE IMAGE", "Shown on the lock screen. Optional.")
        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("File path or https:// URL")
        row.addWidget(self.path_input)
        browse = QPushButton("BROWSE")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        self.layout.addLayout(row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select profile image")
        if path:
            self.path_input.setText(path)


class SplashPage(WizardPage):
    def __init__(self):
        super().__init__("BOOT SPLASH", "Shown via plymouth during boot. Optional.")
        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("File path or https:// URL")
        row.addWidget(self.path_input)
        browse = QPushButton("BROWSE")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        self.layout.addLayout(row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select splash image")
        if path:
            self.path_input.setText(path)


class ThemePage(WizardPage):
    def __init__(self):
        super().__init__("THEME & LAYOUT", "System-wide look for Weston and Qt apps.")

        self.layout.addWidget(QLabel("Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Dark", "Light"])
        self.layout.addWidget(self.mode_combo)

        self.layout.addWidget(QLabel("Accent color"))
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(list(ACCENT_COLORS.keys()))
        self.layout.addWidget(self.accent_combo)

        self.layout.addWidget(QLabel("Window layout"))
        self.tiled_radio = QRadioButton("Tiled (maximize SDR screen space)")
        self.floating_radio = QRadioButton("Floating")
        self.tiled_radio.setChecked(True)
        layout_group = QButtonGroup(self)
        layout_group.addButton(self.tiled_radio)
        layout_group.addButton(self.floating_radio)
        self.layout.addWidget(self.tiled_radio)
        self.layout.addWidget(self.floating_radio)


class AppsPage(WizardPage):
    def __init__(self):
        super().__init__("APPLICATION DEFAULTS", "")

        self.layout.addWidget(QLabel("Default SDR app (hotkey-launched)"))
        self.sdr_combo = QComboBox()
        self.sdr_combo.addItems(SDR_APPS)
        self.layout.addWidget(self.sdr_combo)

        self.layout.addWidget(QLabel("ROM directory (doomgeneric / pygame scripts)"))
        row = QHBoxLayout()
        self.rom_input = QLineEdit("/home/root/roms")
        row.addWidget(self.rom_input)
        browse = QPushButton("BROWSE")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        self.layout.addLayout(row)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select ROM directory")
        if path:
            self.rom_input.setText(path)


class NetworkPage(WizardPage):
    def __init__(self):
        super().__init__("NETWORKING & TELEMETRY", "Both fields are optional and can be configured later.")

        self.layout.addWidget(QLabel("Wi-Fi SSID"))
        self.ssid_input = QLineEdit()
        self.layout.addWidget(self.ssid_input)

        self.layout.addWidget(QLabel("Wi-Fi password"))
        self.wifi_pass_input = QLineEdit()
        self.wifi_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.wifi_pass_input)

        self.layout.addWidget(QLabel("Remote MQTT broker host (optional)"))
        self.mqtt_host_input = QLineEdit()
        self.mqtt_host_input.setPlaceholderText("leave blank to use the local broker")
        self.layout.addWidget(self.mqtt_host_input)

        self.layout.addWidget(QLabel("MQTT username (optional)"))
        self.mqtt_user_input = QLineEdit()
        self.layout.addWidget(self.mqtt_user_input)

        self.layout.addWidget(QLabel("MQTT password (optional)"))
        self.mqtt_pass_input = QLineEdit()
        self.mqtt_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.mqtt_pass_input)


class OobeWizard(QWidget):
    def __init__(self):
        super().__init__()
        if os.path.exists(FLAG_FILE):
            print("OOBE already completed. Exiting.")
            sys.exit(0)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("UConsole Setup")
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setStyleSheet(THEME_QSS)

        outer = QVBoxLayout()

        self.pin_page = PinPage()
        self.profile_page = ProfileImagePage()
        self.splash_page = SplashPage()
        self.theme_page = ThemePage()
        self.apps_page = AppsPage()
        self.network_page = NetworkPage()

        self.stack = QStackedWidget()
        for page in (self.pin_page, self.profile_page, self.splash_page,
                     self.theme_page, self.apps_page, self.network_page):
            self.stack.addWidget(page)
        outer.addWidget(self.stack)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("BACK")
        self.back_btn.clicked.connect(self._go_back)
        nav.addWidget(self.back_btn)

        self.next_btn = QPushButton("NEXT")
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.next_btn)
        outer.addLayout(nav)

        self.setLayout(outer)
        self._update_nav()

    def _update_nav(self):
        at_last = self.stack.currentIndex() == self.stack.count() - 1
        self.back_btn.setEnabled(self.stack.currentIndex() > 0)
        self.next_btn.setText("FINISH" if at_last else "NEXT")

    def _go_back(self):
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
            self._update_nav()

    def _go_next(self):
        if self.stack.currentWidget() is self.pin_page:
            if self.pin_page.validate() is None:
                return
        if self.stack.currentIndex() == self.stack.count() - 1:
            self._finish()
            return
        self.stack.setCurrentIndex(self.stack.currentIndex() + 1)
        self._update_nav()

    def _finish(self):
        pin = self.pin_page.validate()
        if pin is None:
            self.stack.setCurrentWidget(self.pin_page)
            self._update_nav()
            return

        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)

            hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
            with open(PIN_FILE, "w") as f:
                f.write(hashed_pin)
            sync_unix_password(pin)

            if self.profile_page.path_input.text():
                fetch_asset(self.profile_page.path_input.text(), PROFILE_IMAGE_FILE)
            if self.splash_page.path_input.text():
                fetch_asset(self.splash_page.path_input.text(), SPLASH_IMAGE_FILE)

            settings = {
                "theme_mode": self.theme_page.mode_combo.currentText(),
                "accent_color": ACCENT_COLORS[self.theme_page.accent_combo.currentText()],
                "layout": "tiled" if self.theme_page.tiled_radio.isChecked() else "floating",
                "default_sdr_app": self.apps_page.sdr_combo.currentText(),
                "rom_directory": self.apps_page.rom_input.text(),
                "mqtt_host": self.network_page.mqtt_host_input.text(),
                "mqtt_username": self.network_page.mqtt_user_input.text(),
                "mqtt_password": self.network_page.mqtt_pass_input.text(),
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)

            connect_wifi(self.network_page.ssid_input.text(), self.network_page.wifi_pass_input.text())

            with open(FLAG_FILE, "w") as f:
                f.write("COMPLETED")

            QMessageBox.information(self, "Success", "Local authority established. System is ready.")
            sys.exit(0)

        except Exception as e:
            QMessageBox.critical(self, "Fatal Error", f"Failed to complete setup: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = OobeWizard()
    wizard.show()
    sys.exit(app.exec())
