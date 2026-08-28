#!/usr/bin/env python3
import subprocess
import glob
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider,
)
from PyQt6.QtCore import Qt

import uconsole_theme

# ---------------------------------------------------------
# UConsole Control Panel
# ---------------------------------------------------------
# Summoned on demand by the hotkey daemon (F12). Exposes the
# quick-access toggles called for in requirement.md 5.3: CPU
# governor, SDR/GPS GPIO rails, display brightness, and Wi-Fi/
# Bluetooth radio state. Runs as root (spawned by the root-owned
# hotkey daemon) so it can write directly to sysfs/gpiod, matching
# the trust model already used by the OOBE wizard and lock screen.

GPIOCHIP = "gpiochip0"
SDR_GPIO_PIN = 23
GPS_GPIO_PIN = 27

GOVERNOR_GLOB = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
BACKLIGHT_GLOB = "/sys/class/backlight/*/brightness"
BACKLIGHT_MAX_GLOB = "/sys/class/backlight/*/max_brightness"


def run(cmd):
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"Command failed ({' '.join(cmd)}): {e}")
        return False


def gpio_read(pin):
    try:
        out = subprocess.run(
            ["gpioget", GPIOCHIP, str(pin)], check=True, capture_output=True, text=True
        )
        return out.stdout.strip() == "1"
    except Exception as e:
        print(f"Failed to read GPIO {pin}: {e}")
        return False


def gpio_write(pin, value):
    run(["gpioset", f"{GPIOCHIP}={pin}={'1' if value else '0'}"])


def set_governor(governor):
    for path in glob.glob(GOVERNOR_GLOB):
        try:
            with open(path, "w") as f:
                f.write(governor)
        except Exception as e:
            print(f"Failed to set governor on {path}: {e}")


def get_max_brightness():
    for path in glob.glob(BACKLIGHT_MAX_GLOB):
        try:
            with open(path) as f:
                return int(f.read().strip())
        except Exception:
            continue
    return 255


def set_brightness(value):
    for path in glob.glob(BACKLIGHT_GLOB):
        try:
            with open(path, "w") as f:
                f.write(str(value))
        except Exception as e:
            print(f"Failed to set brightness on {path}: {e}")


class ToggleRow(QWidget):
    def __init__(self, label, on_toggle, initial=False):
        super().__init__()
        self.state = initial
        self._on_toggle = on_toggle

        layout = QHBoxLayout()
        layout.addWidget(QLabel(label))
        self.button = QPushButton()
        self.button.clicked.connect(self._clicked)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self._refresh()

    def _clicked(self):
        self.state = not self.state
        self._on_toggle(self.state)
        self._refresh()

    def _refresh(self):
        self.button.setText("ON" if self.state else "OFF")


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UConsole Control Panel")
        self.setFixedWidth(420)
        self.setStyleSheet(uconsole_theme.build_qss())

        layout = QVBoxLayout()

        title = QLabel("CONTROL PANEL")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(ToggleRow(
            "SDR module (GPIO23)",
            lambda v: gpio_write(SDR_GPIO_PIN, v),
            initial=gpio_read(SDR_GPIO_PIN),
        ))
        layout.addWidget(ToggleRow(
            "GPS module (GPIO27)",
            lambda v: gpio_write(GPS_GPIO_PIN, v),
            initial=gpio_read(GPS_GPIO_PIN),
        ))
        layout.addWidget(ToggleRow(
            "Performance governor",
            lambda v: set_governor("performance" if v else "ondemand"),
            initial=False,
        ))
        layout.addWidget(ToggleRow(
            "Wi-Fi radio",
            lambda v: run(["nmcli", "radio", "wifi", "on" if v else "off"]),
            initial=True,
        ))
        layout.addWidget(ToggleRow(
            "Bluetooth radio",
            lambda v: run(["rfkill", "unblock" if v else "block", "bluetooth"]),
            initial=False,
        ))

        brightness_label = QLabel("Display brightness")
        layout.addWidget(brightness_label)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(10)
        slider.setMaximum(get_max_brightness())
        slider.setValue(slider.maximum())
        slider.valueChanged.connect(set_brightness)
        layout.addWidget(slider)

        close_btn = QPushButton("CLOSE")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec())
