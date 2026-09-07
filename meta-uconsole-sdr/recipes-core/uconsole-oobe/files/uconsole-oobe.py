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
    QButtonGroup, QFileDialog, QListWidget, QListWidgetItem,
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


def scan_wifi_networks():
    """Best-effort Wi-Fi scan via nmcli. Returns a list of
    (ssid, signal, secured) tuples, deduped by SSID (keeping the
    strongest signal when the same network is seen from multiple
    APs), sorted strongest-first. --escape no keeps nmcli from
    backslash-escaping ':' in field values, so a plain split(":")
    is safe for any SSID that doesn't itself contain a literal colon."""
    try:
        subprocess.run(["nmcli", "device", "wifi", "rescan"], check=False, timeout=10)
    except Exception as e:
        print(f"Wi-Fi rescan failed (continuing with cached results): {e}")

    try:
        result = subprocess.run(
            ["nmcli", "--terse", "--escape", "no", "-f", "SSID,SIGNAL,SECURITY",
             "device", "wifi", "list"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except Exception as e:
        print(f"Wi-Fi scan failed: {e}")
        return []

    strongest = {}
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue
        ssid = parts[0].strip()
        if not ssid:
            continue
        try:
            signal = int(parts[1])
        except ValueError:
            signal = 0
        secured = parts[2].strip() not in ("", "--")
        if ssid not in strongest or signal > strongest[ssid][0]:
            strongest[ssid] = (signal, secured)

    return sorted(
        ((ssid, signal, secured) for ssid, (signal, secured) in strongest.items()),
        key=lambda entry: entry[1], reverse=True,
    )


def connect_wifi(ssid, password):
    if not ssid:
        return False, "no network selected"
    try:
        args = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, ""
        return False, (result.stderr or result.stdout or "unknown error").strip()
    except Exception as e:
        return False, str(e)


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
        super().__init__(
            "NETWORKING & TELEMETRY",
            "Scan for a Wi-Fi network and connect, or skip -- both this and MQTT "
            "can be configured later.",
        )

        self.layout.addWidget(QLabel("Wi-Fi networks"))
        self.wifi_list = QListWidget()
        self.wifi_list.setMaximumHeight(160)
        self.wifi_list.currentItemChanged.connect(self._on_network_selected)
        self.layout.addWidget(self.wifi_list)

        scan_row = QHBoxLayout()
        self.scan_btn = QPushButton("SCAN")
        self.scan_btn.clicked.connect(self._scan)
        scan_row.addWidget(self.scan_btn)
        self.wifi_status_label = QLabel("")
        self.wifi_status_label.setStyleSheet("color: #c5c6c7;")
        scan_row.addWidget(self.wifi_status_label, 1)
        self.layout.addLayout(scan_row)

        connect_row = QHBoxLayout()
        self.wifi_pass_input = QLineEdit()
        self.wifi_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.wifi_pass_input.setPlaceholderText("Wi-Fi password")
        self.wifi_pass_input.returnPressed.connect(self._connect)
        self.wifi_pass_input.hide()
        connect_row.addWidget(self.wifi_pass_input)
        self.connect_btn = QPushButton("CONNECT")
        self.connect_btn.clicked.connect(self._connect)
        self.connect_btn.hide()
        connect_row.addWidget(self.connect_btn)
        self.layout.addLayout(connect_row)

        # Deferred to showEvent rather than run here: all six wizard
        # pages are constructed up front before the wizard's first
        # page ever appears, so scanning now would freeze the PIN page
        # behind a several-second Wi-Fi scan before the wizard could
        # even show up.
        self._scanned_once = False

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

    def showEvent(self, event):
        super().showEvent(event)
        if not self._scanned_once:
            self._scanned_once = True
            self._scan()

    def _scan(self):
        self.wifi_status_label.setText("Scanning...")
        self.wifi_list.clear()
        self.wifi_pass_input.hide()
        self.connect_btn.hide()
        QApplication.processEvents()

        networks = scan_wifi_networks()
        if not networks:
            self.wifi_status_label.setText("No networks found.")
            return
        for ssid, signal, secured in networks:
            label = f"{ssid}    {signal}%" + ("  (secured)" if secured else "")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, (ssid, secured))
            self.wifi_list.addItem(item)
        self.wifi_status_label.setText(f"{len(networks)} network(s) found.")

    def _on_network_selected(self, current, _previous):
        self.wifi_pass_input.hide()
        self.wifi_pass_input.clear()
        if current is None:
            self.connect_btn.hide()
            return
        _ssid, secured = current.data(Qt.ItemDataRole.UserRole)
        self.wifi_pass_input.setVisible(secured)
        self.connect_btn.show()

    def _connect(self):
        item = self.wifi_list.currentItem()
        if item is None:
            return
        ssid, secured = item.data(Qt.ItemDataRole.UserRole)
        password = self.wifi_pass_input.text() if secured else ""
        self.wifi_status_label.setText(f"Connecting to {ssid}...")
        QApplication.processEvents()
        ok, detail = connect_wifi(ssid, password)
        self.wifi_status_label.setText(
            f"Connected to {ssid}." if ok else f"Failed to connect: {detail}"
        )


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

        # Enter advances through text fields like a normal form. The
        # Wi-Fi password field is the one exception -- Enter there
        # should try to connect, not skip past it (already wired to
        # _connect in NetworkPage itself).
        for page in (self.pin_page, self.profile_page, self.splash_page,
                     self.theme_page, self.apps_page, self.network_page):
            wifi_pass = getattr(page, "wifi_pass_input", None)
            for line_edit in page.findChildren(QLineEdit):
                if line_edit is wifi_pass:
                    continue
                line_edit.returnPressed.connect(self._go_next)

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

    def keyPressEvent(self, event):
        # Plain Left/Right/Up/Down/PageUp/PageDown are all already
        # claimed by one form widget or another in this wizard --
        # QLineEdit for cursor movement, QComboBox and the new Wi-Fi
        # QListWidget for changing the selected item -- so any of them
        # would silently do the wrong thing instead of moving between
        # pages, depending on which field currently has focus. Alt+
        # Left/Right isn't consumed by any of Qt's own widgets, so it
        # reaches here reliably no matter what has focus, the same way
        # Alt+Left/Right means back/forward in every browser.
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if alt and event.key() == Qt.Key.Key_Right:
            self._go_next()
        elif alt and event.key() == Qt.Key.Key_Left:
            self._go_back()
        else:
            super().keyPressEvent(event)

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

            # Wi-Fi connection itself already happened (or was skipped)
            # live on NetworkPage's own CONNECT button, with real
            # success/failure feedback there -- nothing left to do here.

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
