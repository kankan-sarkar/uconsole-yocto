#!/usr/bin/env python3
import sys
import os
import glob
import socket
import threading
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QStackedLayout,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QPropertyAnimation

import uconsole_theme

# ---------------------------------------------------------
# UConsole Home Screen
# ---------------------------------------------------------
# Real hardware finding: after switching Weston to kiosk-shell.so (see
# weston-init.bbappend) to get rid of the stock desktop-shell panel,
# the screen after OOBE (or whenever no app happens to be running) was
# just black -- kiosk-shell draws literally nothing of its own, and
# nothing in this project had ever been built to serve as an idle/home
# screen. This is that home screen: a persistent app, always running
# in the background, that becomes the visible fullscreen surface again
# whenever nothing else is (see hide()/show() below).
#
# Real constraint that shapes this whole file: this Weston build has
# neither the wlr-layer-shell protocol (what a real always-on-top Dock
# needs to coexist with another fullscreen app) nor xdg-activation or
# any other way to tell the compositor "reactivate that other already-
# running app's window" (confirmed by grepping the actual built
# rootfs -- neither string appears anywhere, and kiosk-shell.so has no
# such IPC). So there is no true multi-window desktop here: launching
# an app covers this home screen completely, and "switching apps"
# means coming back to THIS screen (via the global hotkeys below) and
# picking something else from the Dock or search -- not simultaneous
# windows, and not reliably reactivating a specific already-running
# app's own window (that app may reopen a second instance, or refuse
# to and simply do nothing, entirely up to that app -- not something
# this shell can control).
#
# Global hotkeys (Ctrl+Alt+Space for search, Ctrl+Tab to come home,
# Ctrl+1..9 for direct Dock launches) are handled entirely in
# uconsole-hotkey.py, which reads the physical keyboard at the evdev
# level below Wayland's own focus model -- the same proven mechanism
# already behind F10/F11/F12, and the only way to get input that
# works no matter which app currently has keyboard focus (Wayland's
# security model deliberately does not let one client grab another's
# input). Commands reach this process over a local Unix socket.

SOCK_PATH = "/run/uconsole-shell.sock"

BATTERY_CAPACITY_GLOB = "/sys/class/power_supply/*/capacity"

# Checked against the real installed path for each -- only apps that
# actually exist in this image variant show up in the Dock (the
# qemu-test image has none of the SDR tools; real hardware does).
CANDIDATE_APPS = [
    ("Control Panel", "⚙", "/usr/bin/uconsole-panel"),
    ("GQRX", "\U0001F4E1", "/usr/bin/gqrx"),
    ("SDRangel", "\U0001F4E1", "/usr/bin/sdrangel"),
    ("CubicSDR", "\U0001F4E1", "/usr/bin/CubicSDR"),
    ("SDR++", "\U0001F4E1", "/usr/bin/sdrpp"),
    ("Terminal", "⌨", "/usr/bin/weston-terminal"),
]


def discover_apps():
    return [(name, icon, path) for name, icon, path in CANDIDATE_APPS if os.path.exists(path)]


def get_network_status():
    """Best-effort. Returns (kind, ip) where kind is 'wired', 'wifi',
    or None if nothing is connected. ip is None if unknown."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
            capture_output=True, text=True, timeout=5, check=True,
        )
    except Exception:
        return None, None

    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue
        device, dtype, state = parts[0], parts[1], parts[2]
        if state != "connected" or dtype not in ("wifi", "ethernet"):
            continue
        ip = None
        try:
            ip_result = subprocess.run(
                ["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", device],
                capture_output=True, text=True, timeout=5, check=True,
            )
            for ip_line in ip_result.stdout.splitlines():
                if ip_line.startswith("IP4.ADDRESS"):
                    ip = ip_line.split(":", 1)[1].split("/")[0]
                    break
        except Exception:
            pass
        return ("wired" if dtype == "ethernet" else "wifi"), ip
    return None, None


def get_battery_status():
    """Best-effort. Returns (percent, charging) or (None, False) if
    this device has no battery power_supply node (e.g. QEMU)."""
    for path in glob.glob(BATTERY_CAPACITY_GLOB):
        try:
            with open(path) as f:
                percent = int(f.read().strip())
        except Exception:
            continue
        charging = False
        status_path = path.replace("capacity", "status")
        try:
            with open(status_path) as f:
                charging = f.read().strip() in ("Charging", "Full")
        except Exception:
            pass
        return percent, charging
    return None, False


def list_vpn_connections():
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
            capture_output=True, text=True, timeout=5, check=True,
        )
    except Exception:
        return []
    return [
        parts[0] for parts in (line.split(":") for line in result.stdout.splitlines())
        if len(parts) >= 2 and parts[1] in ("vpn", "wireguard")
    ]


def is_vpn_active(name):
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return name in result.stdout.splitlines()
    except Exception:
        return False


def set_vpn(name, up):
    try:
        subprocess.run(["nmcli", "connection", "up" if up else "down", name],
                        check=True, timeout=20)
        return True
    except Exception as e:
        print(f"VPN {'up' if up else 'down'} failed for {name}: {e}")
        return False


class IpcBridge(QObject):
    command_received = pyqtSignal(str)


def start_ipc_server(bridge):
    """Listens on SOCK_PATH for single-line text commands from
    uconsole-hotkey.py (root, evdev-driven, works regardless of which
    app has Wayland focus). Runs the accept loop on a background
    thread; command_received's queued cross-thread connection is what
    safely hands each command back to the Qt main thread."""
    try:
        if os.path.exists(SOCK_PATH):
            os.remove(SOCK_PATH)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCK_PATH)
        os.chmod(SOCK_PATH, 0o666)
        server.listen(5)
    except Exception as e:
        print(f"Failed to start uconsole-shell IPC socket: {e}")
        return

    def accept_loop():
        while True:
            try:
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(256).decode(errors="ignore").strip()
                    if data:
                        bridge.command_received.emit(data)
            except Exception as e:
                print(f"uconsole-shell IPC accept error: {e}")

    threading.Thread(target=accept_loop, daemon=True).start()


class StatusBar(QWidget):
    """Top strip: network (hover for IP), VPN toggle, battery."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 8, 16, 8)

        self.clock_label = QLabel("")
        layout.addWidget(self.clock_label)
        layout.addStretch()

        self.net_label = QLabel("●")
        self.net_label.setToolTip("No network connection")
        layout.addWidget(self.net_label)

        self.vpn_button = QPushButton("VPN")
        self.vpn_button.setCheckable(True)
        self.vpn_button.clicked.connect(self._toggle_vpn)
        self._vpn_name = None
        layout.addWidget(self.vpn_button)

        self.battery_label = QLabel("")
        layout.addWidget(self.battery_label)

        self.setLayout(layout)

        self._battery_opacity = QGraphicsOpacityEffect(self.battery_label)
        self.battery_label.setGraphicsEffect(self._battery_opacity)
        self._battery_anim = QPropertyAnimation(self._battery_opacity, b"opacity")
        self._battery_anim.setDuration(1200)
        self._battery_anim.setStartValue(1.0)
        self._battery_anim.setEndValue(0.4)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)
        self.refresh()

    def refresh(self):
        import datetime
        self.clock_label.setText(datetime.datetime.now().strftime("%H:%M"))

        kind, ip = get_network_status()
        if kind is None:
            self.net_label.setText("○")
            self.net_label.setToolTip("No network connection")
        else:
            glyph = "\U0001F5A7" if kind == "wired" else "\U0001F4F6"
            self.net_label.setText(glyph)
            self.net_label.setToolTip(ip or "Connected (IP unknown)")

        if self._vpn_name is None:
            vpns = list_vpn_connections()
            self._vpn_name = vpns[0] if vpns else None
        if self._vpn_name is None:
            self.vpn_button.setEnabled(False)
            self.vpn_button.setToolTip("No VPN connection profile configured (nmcli)")
        else:
            active = is_vpn_active(self._vpn_name)
            self.vpn_button.blockSignals(True)
            self.vpn_button.setChecked(active)
            self.vpn_button.blockSignals(False)
            self.vpn_button.setToolTip(f"{self._vpn_name} ({'connected' if active else 'disconnected'})")

        percent, charging = get_battery_status()
        if percent is None:
            self.battery_label.setText("")
        else:
            bolt = "⚡" if charging else ""
            self.battery_label.setText(f"{bolt}{percent}%")
            if charging and self._battery_anim.state() != QPropertyAnimation.State.Running:
                self._battery_anim.setLoopCount(-1)
                self._battery_anim.start()
            elif not charging and self._battery_anim.state() == QPropertyAnimation.State.Running:
                self._battery_anim.stop()
                self._battery_opacity.setOpacity(1.0)

    def _toggle_vpn(self, checked):
        if self._vpn_name is None:
            return
        set_vpn(self._vpn_name, checked)
        QTimer.singleShot(1500, self.refresh)


class Dock(QWidget):
    def __init__(self, launch_callback):
        super().__init__()
        self._launch = launch_callback
        self.apps = discover_apps()

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 8, 16, 16)
        layout.addStretch()
        for index, (name, icon, path) in enumerate(self.apps, start=1):
            button = QPushButton(f"{icon}\n{name}")
            button.setFixedSize(96, 72)
            button.setToolTip(f"{name}  (Ctrl+{index})" if index <= 9 else name)
            button.clicked.connect(lambda _checked, p=path: self._launch(p))
            layout.addWidget(button)
        layout.addStretch()
        self.setLayout(layout)

    def launch_index(self, index_1_based):
        pos = index_1_based - 1
        if 0 <= pos < len(self.apps):
            self._launch(self.apps[pos][2])


class SearchOverlay(QWidget):
    def __init__(self, apps, launch_callback, close_callback):
        super().__init__()
        self._apps = apps
        self._launch = launch_callback
        self._close = close_callback
        # Deliberately NOT objectName "glassCard" -- that's reserved
        # for the floating `card` widget below. Giving both the same
        # name would double up the glass-panel border/rounded-corner
        # styling on this widget's own (much larger) full-window rect
        # as well, nesting one rounded box inside another instead of a
        # single card floating over a plain dimmed backdrop.
        self.setStyleSheet("background-color: rgba(0, 0, 0, 140);")

        outer = QVBoxLayout()
        outer.setContentsMargins(200, 80, 200, 80)

        card = QWidget()
        card.setObjectName("glassCard")
        card_layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search apps...")
        self.search_input.textChanged.connect(self._filter)
        self.search_input.returnPressed.connect(self._launch_selected)
        card_layout.addWidget(self.search_input)

        self.results = QListWidget()
        self.results.itemActivated.connect(lambda _item: self._launch_selected())
        card_layout.addWidget(self.results)

        card.setLayout(card_layout)
        outer.addWidget(card)
        self.setLayout(outer)

    def showEvent(self, event):
        super().showEvent(event)
        self.search_input.clear()
        self._filter("")
        self.search_input.setFocus()

    def _filter(self, text):
        self.results.clear()
        needle = text.strip().lower()
        for name, icon, path in self._apps:
            if needle in name.lower():
                item = QListWidgetItem(f"{icon}  {name}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _launch_selected(self):
        item = self.results.currentItem()
        if item is not None:
            self._launch(item.data(Qt.ItemDataRole.UserRole))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._close()
        elif event.key() == Qt.Key.Key_Down:
            self.results.setCurrentRow(min(self.results.currentRow() + 1, self.results.count() - 1))
        elif event.key() == Qt.Key.Key_Up:
            self.results.setCurrentRow(max(self.results.currentRow() - 1, 0))
        else:
            super().keyPressEvent(event)


class HomeScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UConsole")
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setStyleSheet(uconsole_theme.build_qss() + uconsole_theme.build_glass_qss())

        self.stack = QStackedLayout()

        home_page = QWidget()
        home_layout = QVBoxLayout()
        home_layout.setContentsMargins(0, 0, 0, 0)
        self.status_bar = StatusBar()
        home_layout.addWidget(self.status_bar)
        home_layout.addStretch()
        self.dock = Dock(self._launch)
        home_layout.addWidget(self.dock)
        home_page.setLayout(home_layout)

        self.search_overlay = SearchOverlay(self.dock.apps, self._launch, self._close_search)

        self.stack.addWidget(home_page)
        self.stack.addWidget(self.search_overlay)
        self.setLayout(self.stack)

        self.bridge = IpcBridge()
        self.bridge.command_received.connect(self._on_command)
        start_ipc_server(self.bridge)

    def keyPressEvent(self, event):
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl and alt and event.key() == Qt.Key.Key_Space:
            self._open_search()
        else:
            super().keyPressEvent(event)

    def _on_command(self, command):
        self._come_home()
        if command == "SEARCH":
            self._open_search()
        elif command.startswith("ACTIVATE:"):
            try:
                index = int(command.split(":", 1)[1])
            except ValueError:
                return
            self.dock.launch_index(index)
        # "SHOW" (or anything unrecognized) already handled by
        # _come_home() above -- just bring the home screen back.

    def _come_home(self):
        self.stack.setCurrentIndex(0)
        self.status_bar.refresh()
        self.show()
        self.raise_()
        self.activateWindow()

    def _open_search(self):
        self._come_home()
        self.stack.setCurrentIndex(1)

    def _close_search(self):
        self.stack.setCurrentIndex(0)

    def _launch(self, path):
        try:
            subprocess.Popen([path])
        except Exception as e:
            print(f"Failed to launch {path}: {e}")
        # Relinquish the fullscreen surface to the just-launched app --
        # kiosk-shell shows whichever toplevel was mapped most
        # recently, so hiding (unmapping) this one lets the new app's
        # surface take over instead of the two competing.
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    home = HomeScreen()
    home.show()
    sys.exit(app.exec())
