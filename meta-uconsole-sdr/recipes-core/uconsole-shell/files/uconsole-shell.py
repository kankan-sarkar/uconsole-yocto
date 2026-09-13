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
THERMAL_GLOB = "/sys/class/thermal/thermal_zone*/temp"

# Checked against the real installed path for each -- only apps that
# actually exist in this image variant show up in the Dock (the
# qemu-test image has none of the SDR tools; real hardware does).
# The one-line description is what the search overlay shows under each
# result, per the command-palette mock in ui-mocks/.
# Icons are Material Symbols names resolved through uconsole_theme.icon()
# rather than emoji: the fonts in this image carry no pictographs, so
# emoji render as empty boxes (which is exactly what the first themed
# build did before ttf-material-symbols was added).
CANDIDATE_APPS = [
    ("Terminal", "terminal", "Launch a root shell session", "/usr/bin/weston-terminal"),
    ("Control Panel", "settings", "CPU governor, GPIO rails, brightness, radios", "/usr/bin/uconsole-panel"),
    ("GQRX", "satellite", "Software defined radio receiver", "/usr/bin/gqrx"),
    ("SDRangel", "satellite", "Multi-mode SDR transceiver", "/usr/bin/sdrangel"),
    ("CubicSDR", "satellite", "Cross-platform SDR spectrum browser", "/usr/bin/CubicSDR"),
    ("SDR++", "satellite", "Modular SDR receiver", "/usr/bin/sdrpp"),
]


def discover_apps():
    return [app for app in CANDIDATE_APPS if os.path.exists(app[3])]


def get_cpu_temperature():
    """Highest thermal zone reading in °C, or None if the host has none.

    The status bar shows this because a field SDR rig is a thermally
    constrained box: DESIGN.md puts temperature in the hardware status
    bar for good reason. QEMU has no thermal zones, so None is normal
    there and the label simply hides.
    """
    readings = []
    for path in glob.glob(THERMAL_GLOB):
        try:
            with open(path) as f:
                millicelsius = int(f.read().strip())
        except (OSError, ValueError):
            continue
        # Kernel reports millidegrees, but a few drivers report whole
        # degrees; treat implausibly small values as already-degrees.
        readings.append(millicelsius / 1000.0 if millicelsius > 1000 else float(millicelsius))
    return max(readings) if readings else None


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
    """Top hardware status strip, per the mock in ui-mocks/.

    Right-aligned and deliberately terse: network (hover for IP),
    temperature, VPN, battery, clock. Small label type, a hairline
    bottom border, no heavy chrome -- it's meant to read as part of the
    hardware rather than as an application toolbar.
    """

    def __init__(self):
        super().__init__()
        p = uconsole_theme.palette()
        self.setObjectName("statusBar")
        self.setFixedHeight(30)
        self.setStyleSheet(
            f"#statusBar {{ background-color: {p['surface_low']};"
            f" border-bottom: 1px solid {p['surface_highest']}; }}"
            f"#statusBar QLabel {{ font-size: 11px; letter-spacing: 1px; }}"
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(16)
        # Everything sits on the right, as in the mock; the left side is
        # left clear so a future taskbar can live there.
        layout.addStretch()

        icon_css = f"font-family: '{uconsole_theme.ICON_FONT_FAMILY}'; font-size: 14px;"

        self.net_label = QLabel(uconsole_theme.icon("wifi"))
        self.net_label.setStyleSheet(f"color: {p['secondary']}; {icon_css}")
        self.net_label.setToolTip("No network connection")
        layout.addWidget(self.net_label)

        self.temp_label = QLabel("")
        self.temp_label.setStyleSheet(f"color: {p['error']}; font-size: 11px;")
        layout.addWidget(self.temp_label)

        self.vpn_button = QPushButton("VPN")
        self.vpn_button.setCheckable(True)
        self.vpn_button.setFixedHeight(20)
        self.vpn_button.setStyleSheet(
            f"QPushButton {{ font-size: 10px; padding: 1px 6px;"
            f" border: 1px solid {p['outline_variant']}; border-radius: 2px;"
            f" background: transparent; color: {p['on_surface_variant']}; }}"
            f"QPushButton:checked {{ color: {p['tertiary']};"
            f" border: 1px solid {p['tertiary']}; }}"
        )
        self.vpn_button.clicked.connect(self._toggle_vpn)
        self._vpn_name = None
        layout.addWidget(self.vpn_button)

        self.battery_label = QLabel("")
        self.battery_label.setStyleSheet(f"color: {p['tertiary']};")
        layout.addWidget(self.battery_label)

        self.clock_label = QLabel("")
        self.clock_label.setStyleSheet(
            f"color: {p['on_surface']}; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.clock_label)

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
        self.clock_label.setText(datetime.datetime.now().strftime("%H:%M:%S"))

        p = uconsole_theme.palette()
        kind, ip = get_network_status()
        if kind is None:
            self.net_label.setText(uconsole_theme.icon("wifi"))
            self.net_label.setStyleSheet(
                f"color: {p['outline']};"
                f" font-family: '{uconsole_theme.ICON_FONT_FAMILY}'; font-size: 14px;")
            self.net_label.setToolTip("No network connection")
        else:
            self.net_label.setText(
                uconsole_theme.icon("network" if kind == "wired" else "wifi"))
            self.net_label.setStyleSheet(
                f"color: {p['secondary']};"
                f" font-family: '{uconsole_theme.ICON_FONT_FAMILY}'; font-size: 14px;")
            # Hovering is how you get the address, per the mock -- the
            # bar itself stays terse.
            self.net_label.setToolTip(ip or "Connected (IP unknown)")

        temp = get_cpu_temperature()
        # Hidden rather than shown empty when the host has no thermal
        # zones (QEMU), so the bar doesn't keep a blank gap.
        self.temp_label.setVisible(temp is not None)
        if temp is not None:
            self.temp_label.setText(
                f"{uconsole_theme.icon('thermostat')} {temp:.0f}°C")
            self.temp_label.setStyleSheet(
                f"color: {p['error']}; font-size: 11px;"
                f" font-family: '{uconsole_theme.ICON_FONT_FAMILY}';")

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
            bolt = uconsole_theme.icon("bolt") if charging else ""
            self.battery_label.setText(f"{bolt}{percent}%")
            self.battery_label.setStyleSheet(
                f"color: {uconsole_theme.palette()['tertiary']}; font-size: 11px;"
                f" font-family: '{uconsole_theme.ICON_FONT_FAMILY}';")
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
    """Floating icon dock along the bottom edge, per the mock.

    A single rounded translucent container holding square icon tiles,
    rather than a full-width bar -- on a 1280x480 panel a full-width
    bar wastes scarce vertical space and reads as chrome.
    """

    def __init__(self, launch_callback):
        super().__init__()
        self._launch = launch_callback
        self.apps = discover_apps()
        p = uconsole_theme.palette()
        accent = uconsole_theme.accent_color()

        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 16)
        outer.addStretch()

        tray = QWidget()
        tray.setObjectName("dockTray")
        tray.setStyleSheet(
            f"#dockTray {{ background-color: {p['surface_high']};"
            f" border: 1px solid {p['surface_highest']};"
            f" border-radius: 12px; }}"
        )
        tray_layout = QHBoxLayout()
        tray_layout.setContentsMargins(12, 8, 12, 8)
        tray_layout.setSpacing(8)

        if not self.apps:
            empty = QLabel("no launchable apps installed")
            empty.setStyleSheet(f"color: {p['outline']}; font-size: 11px;")
            tray_layout.addWidget(empty)

        for index, (name, icon_name, _desc, path) in enumerate(self.apps, start=1):
            button = QPushButton(uconsole_theme.icon(icon_name))
            button.setFixedSize(52, 52)
            button.setStyleSheet(
                f"QPushButton {{ font-family: '{uconsole_theme.ICON_FONT_FAMILY}';"
                f" font-size: 24px;"
                f" background-color: {p['surface_container']};"
                f" border: 1px solid {p['surface_highest']};"
                f" border-radius: 8px; color: {p['on_surface']}; }}"
                f"QPushButton:hover, QPushButton:focus {{"
                f" background-color: {p['surface_highest']};"
                f" border: 1px solid {accent}; color: {accent}; }}"
            )
            hint = f"{name}  (Ctrl+{index})" if index <= 9 else name
            button.setToolTip(hint)
            button.clicked.connect(lambda _checked, p_=path: self._launch(p_))
            tray_layout.addWidget(button)

        tray.setLayout(tray_layout)
        outer.addWidget(tray)
        outer.addStretch()
        self.setLayout(outer)

    def launch_index(self, index_1_based):
        pos = index_1_based - 1
        if 0 <= pos < len(self.apps):
            self._launch(self.apps[pos][3])


class SearchOverlay(QWidget):
    """Command palette, per the mock in ui-mocks/.

    A single card floating over a dimmed backdrop: prompt row with an
    ESC hint, then result rows carrying a title, a one-line
    description and the launch shortcut, then a footer spelling out the
    navigation keys. The hints are on screen rather than assumed
    because this device is driven by keyboard and d-pad, not a mouse.
    """

    def __init__(self, apps, launch_callback, close_callback):
        super().__init__()
        self._apps = apps
        self._launch = launch_callback
        self._close = close_callback
        p = uconsole_theme.palette()
        accent = uconsole_theme.accent_color()

        # Deliberately NOT objectName "glassCard" -- that's reserved for
        # the floating card below. Sharing the name would apply the
        # panel border and rounded corners to this widget's own
        # full-window rect too, nesting one rounded box inside another
        # instead of a single card over a plain dimmed backdrop.
        self.setStyleSheet("background-color: rgba(4, 14, 31, 190);")

        outer = QVBoxLayout()
        outer.setContentsMargins(160, 40, 160, 40)
        # Pin the card to the top third rather than centring it in the
        # remaining space: a palette that grows downward from a fixed
        # point is easier to aim at than one that recentres itself every
        # time the result count changes.
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QWidget()
        card.setObjectName("glassCard")
        card.setStyleSheet(
            f"#glassCard {{ background-color: {p['surface_container']};"
            f" border: 1px solid {p['surface_highest']};"
            f" border-radius: 8px; }}"
        )
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # --- prompt row -------------------------------------------------
        prompt_row = QWidget()
        prompt_row.setStyleSheet(
            f"border-bottom: 1px solid {p['surface_highest']};")
        prompt_layout = QHBoxLayout()
        prompt_layout.setContentsMargins(12, 10, 12, 10)
        prompt_layout.setSpacing(8)

        sigil = QLabel(uconsole_theme.icon("search"))
        sigil.setStyleSheet(
            f"color: {accent}; font-size: 16px; border: none;"
            f" font-family: '{uconsole_theme.ICON_FONT_FAMILY}';")
        prompt_layout.addWidget(sigil)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Type a command or search apps (e.g. terminal, monitor)")
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none;"
            f" font-size: 14px; color: {p['on_surface']}; padding: 0; }}"
        )
        self.search_input.textChanged.connect(self._filter)
        self.search_input.returnPressed.connect(self._launch_selected)
        prompt_layout.addWidget(self.search_input)

        esc = QLabel("ESC")
        esc.setStyleSheet(
            f"color: {p['on_surface_variant']}; font-size: 10px;"
            f" background-color: {p['surface_high']};"
            f" border: 1px solid {p['outline_variant']};"
            f" border-radius: 2px; padding: 2px 6px;"
        )
        prompt_layout.addWidget(esc)
        prompt_row.setLayout(prompt_layout)
        card_layout.addWidget(prompt_row)

        # --- results ----------------------------------------------------
        self.results = QListWidget()
        self.results.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none;"
            f" padding: 4px; }}"
            f"QListWidget::item {{ border-radius: 4px; padding: 0px; }}"
            f"QListWidget::item:selected {{"
            f" background-color: {p['surface_high']}; }}"
        )
        self.results.itemActivated.connect(lambda _item: self._launch_selected())
        card_layout.addWidget(self.results)

        # --- footer hints -----------------------------------------------
        footer = QWidget()
        footer.setStyleSheet(
            f"background-color: {p['surface_low']};"
            f" border-top: 1px solid {p['surface_highest']};")
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(12, 6, 12, 6)
        hint_style = f"color: {p['on_surface_variant']}; font-size: 11px; border: none;"
        nav_hint = QLabel("Use ↑↓ to navigate")
        nav_hint.setStyleSheet(hint_style)
        sel_hint = QLabel("Press Enter to select")
        sel_hint.setStyleSheet(hint_style)
        footer_layout.addWidget(nav_hint)
        footer_layout.addStretch()
        footer_layout.addWidget(sel_hint)
        footer.setLayout(footer_layout)
        card_layout.addWidget(footer)

        card.setLayout(card_layout)
        outer.addWidget(card)
        self.setLayout(outer)

    def _make_row(self, name, icon_name, description, index):
        """A result row: icon, title over description, shortcut chip."""
        p = uconsole_theme.palette()
        accent = uconsole_theme.accent_color()

        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        glyph = QLabel(uconsole_theme.icon(icon_name))
        glyph.setFixedWidth(24)
        glyph.setStyleSheet(
            f"color: {accent}; font-size: 18px;"
            f" font-family: '{uconsole_theme.ICON_FONT_FAMILY}';")
        layout.addWidget(glyph)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title = QLabel(name)
        title.setStyleSheet(
            f"color: {p['on_surface']}; font-size: 13px; font-weight: 600;")
        subtitle = QLabel(description)
        subtitle.setStyleSheet(
            f"color: {p['on_surface_variant']}; font-size: 11px;")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        layout.addLayout(text_col)
        layout.addStretch()

        if index <= 9:
            chip = QLabel(f"Ctrl+{index}")
            chip.setStyleSheet(
                f"color: {p['on_surface_variant']}; font-size: 10px;"
                f" background-color: {p['surface_high']};"
                f" border: 1px solid {p['outline_variant']};"
                f" border-radius: 2px; padding: 2px 6px;"
            )
            layout.addWidget(chip)

        row.setLayout(layout)
        return row

    def showEvent(self, event):
        super().showEvent(event)
        self.search_input.clear()
        self._filter("")
        self.search_input.setFocus()

    def _filter(self, text):
        self.results.clear()
        needle = text.strip().lower()
        for index, (name, icon, description, path) in enumerate(self._apps, start=1):
            # Match the description too, so "shell" finds Terminal and
            # "radio" finds the SDR apps without knowing their names.
            if needle and needle not in name.lower() and needle not in description.lower():
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, path)
            widget = self._make_row(name, icon, description, index)
            item.setSizeHint(widget.sizeHint())
            self.results.addItem(item)
            self.results.setItemWidget(item, widget)
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

        p = uconsole_theme.palette()
        self.stack = QStackedLayout()
        # The overlay has to paint over the home page rather than
        # replace it, so the dimmed backdrop reads as a layer above the
        # desktop -- StackAll keeps both widgets visible at once.
        self.stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        home_page = QWidget()
        home_page.setObjectName("homePage")
        # Vertical gradient from the deep surface to the lowest tone,
        # which is what gives the mock's sense of depth without a
        # wallpaper file to ship and keep in sync.
        home_page.setStyleSheet(
            f"#homePage {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f" stop:0 {p['surface']}, stop:1 {p['surface_lowest']}); }}"
        )
        home_layout = QVBoxLayout()
        home_layout.setContentsMargins(0, 0, 0, 0)
        home_layout.setSpacing(0)
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
        # Starts closed: the desktop is the resting state, and the
        # palette is summoned by Ctrl+Alt+Space (or the SEARCH command
        # from the hotkey daemon).
        self.search_overlay.hide()

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
        self._close_search()
        self.status_bar.refresh()
        self.show()
        self.raise_()
        self.activateWindow()

    def _open_search(self):
        self.status_bar.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
        # StackAll keeps both layers mapped, so the overlay is shown and
        # raised rather than swapped in -- that's what lets its dimmed
        # backdrop read as a layer over the desktop instead of
        # replacing it.
        self.search_overlay.show()
        self.search_overlay.raise_()
        self.search_overlay.setFocus()

    def _close_search(self):
        self.search_overlay.hide()

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
