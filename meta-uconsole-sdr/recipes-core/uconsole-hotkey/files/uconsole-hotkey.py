#!/usr/bin/env python3
import evdev
import glob
import os
import select
import sys
import subprocess
import time
from evdev import ecodes, categorize

# ---------------------------------------------------------
# UConsole Hardware Hotkey Daemon
# ---------------------------------------------------------
# Listens on the internal keyboard for dedicated function keys and
# toggles AIO v2 power rails via gpiod, or summons the on-screen
# control panel. State is tracked per GPIO line so repeated presses
# toggle rather than only ever turning things on.
#
# Also listens on the AXP221 PMIC's power-button input device
# ("axp20x-pek", registered by the mainline axp20x-pek driver once
# clockworkpi-uconsole-overlay.dts gives it a devicetree node to bind
# to -- see uconsole-cm4.conf and linux-raspberrypi_%.bbappend) for
# the physical power button: a short press launches the on-screen
# shutdown menu, a ~5s hold force-powers-off directly. Powering ON
# from an off state is pure PMIC hardware behavior (the chip's own
# power sequencing reacting to the PEK pin) and needs nothing here --
# by the time this daemon is running, that already happened.

GPIOCHIP = "gpiochip0"
SDR_GPIO_PIN = "23"   # Internal USB hub / SDR module power rail
GPS_GPIO_PIN = "27"   # GPS module power rail

CONTROL_PANEL_BIN = "/usr/bin/uconsole-panel"
POWER_MENU_BIN = "/usr/bin/uconsole-power-menu"

# Software long-press threshold for a controlled shutdown. Kept
# shorter than the PMIC's own hardware failsafe (see
# configure_pmic_hardware_failsafe) so software always gets first
# chance at a clean shutdown; the chip is the last-resort backstop if
# Linux is completely hung and this daemon isn't even scheduled.
LONG_PRESS_SECONDS = 5.0

# AXP20X_PEK sysfs "shutdown" attribute (drivers/input/misc/axp20x-pek.c)
# only accepts specific hardware-supported values for the AXP221
# variant: 4000/6000/8000/10000 ms. 8s is the closest option still
# comfortably longer than LONG_PRESS_SECONDS above.
PEK_SHUTDOWN_TIME_MS = "8000"
PEK_SHUTDOWN_ATTR_GLOB = "/sys/bus/platform/devices/*axp20x-pek*/shutdown"

gpio_state = {
    SDR_GPIO_PIN: False,
    GPS_GPIO_PIN: False,
}


def gpio_set(pin, value):
    try:
        subprocess.run(
            ["gpioset", f"{GPIOCHIP}={pin}={'1' if value else '0'}"],
            check=True,
        )
        return True
    except Exception as e:
        print(f"Failed to set GPIO {pin}={value}: {e}")
        return False


def toggle_gpio(pin, label):
    new_state = not gpio_state[pin]
    print(f"Toggling {label} power ({GPIOCHIP} pin {pin}) to: {'ON' if new_state else 'OFF'}")
    if gpio_set(pin, new_state):
        gpio_state[pin] = new_state


def _launch_gui(binary_path, label):
    print(f"Summoning {label}")
    try:
        subprocess.Popen(
            [binary_path],
            env={
                **os.environ,
                "WAYLAND_DISPLAY": "wayland-1",
                "QT_QPA_PLATFORM": "wayland",
            },
        )
    except FileNotFoundError:
        print(f"{label} binary not found at {binary_path}")
    except Exception as e:
        print(f"Failed to launch {label}: {e}")


def launch_control_panel():
    _launch_gui(CONTROL_PANEL_BIN, "control panel")


def launch_power_menu():
    _launch_gui(POWER_MENU_BIN, "power menu")


def force_poweroff():
    print(f"Power button held >= {LONG_PRESS_SECONDS}s -- forcing poweroff")
    subprocess.run(["systemctl", "poweroff", "--force"], check=False)


# Map evdev keycodes to actions. F10/F11 toggle GPIO rails, F12 opens
# the dashboard the way the spec's "dedicated hardware hotkey" calls for.
KEY_ACTIONS = {
    "KEY_F10": lambda: toggle_gpio(SDR_GPIO_PIN, "SDR"),
    "KEY_F11": lambda: toggle_gpio(GPS_GPIO_PIN, "GPS"),
    "KEY_F12": launch_control_panel,
}


def find_input_devices():
    """Locate the uConsole keyboard and the PMIC power button.

    Returns (keyboard_device_or_None, power_button_device_or_None) --
    each is independently optional so this daemon still runs (and logs
    what it's missing) rather than exiting outright if only one of the
    two is present, e.g. while bringing up hardware support
    incrementally.
    """
    keyboard = None
    power_button = None
    for path in evdev.list_devices():
        device = evdev.InputDevice(path)
        name = device.name.lower()
        if power_button is None and "axp20x-pek" in name:
            power_button = device
        elif keyboard is None and ("keyboard" in name or "clockwork" in name):
            keyboard = device
    return keyboard, power_button


def configure_pmic_hardware_failsafe():
    """Program the AXP221's own hardware forced-poweroff timer.

    This is a backstop independent of this daemon or Linux even being
    responsive: it's silicon inside the PMIC itself. Belt-and-braces
    alongside the software LONG_PRESS_SECONDS handling below -- if this
    daemon can't run (crashed, system hung), the button still works.
    Best-effort: an image with hardware support only partially wired
    up (see find_input_devices) simply won't have this sysfs path yet.
    """
    matches = glob.glob(PEK_SHUTDOWN_ATTR_GLOB)
    if not matches:
        print("axp20x-pek shutdown-time sysfs attribute not found -- "
              "PMIC hardware failsafe not configured")
        return
    try:
        with open(matches[0], "w") as f:
            f.write(PEK_SHUTDOWN_TIME_MS)
        print(f"PMIC hardware poweroff failsafe set to {PEK_SHUTDOWN_TIME_MS}ms")
    except Exception as e:
        print(f"Failed to configure PMIC hardware failsafe: {e}")


def main():
    keyboard, power_button = find_input_devices()
    if not keyboard and not power_button:
        print("Could not find uConsole keyboard or power button. Exiting.")
        sys.exit(1)
    if not keyboard:
        print("uConsole keyboard not found -- F10/F11/F12 hotkeys unavailable")
    if not power_button:
        print("PMIC power button (axp20x-pek) not found -- power button unavailable")

    devices = {d.fd: d for d in (keyboard, power_button) if d is not None}
    for d in devices.values():
        print(f"Listening on: {d.name}")

    power_press_started_at = None
    power_long_press_fired = False

    while True:
        # Wake at least once a second even with no events so a held
        # power button gets checked against LONG_PRESS_SECONDS without
        # waiting for the eventual key-up.
        r, _, _ = select.select(devices.keys(), [], [], 1.0)

        if power_press_started_at is not None and not power_long_press_fired:
            if time.monotonic() - power_press_started_at >= LONG_PRESS_SECONDS:
                power_long_press_fired = True
                force_poweroff()

        for fd in r:
            dev = devices[fd]
            for event in dev.read():
                if event.type != ecodes.EV_KEY:
                    continue
                key_event = categorize(event)

                if dev is power_button:
                    if key_event.keycode != "KEY_POWER":
                        continue
                    if key_event.keystate == key_event.key_down:
                        power_press_started_at = time.monotonic()
                        power_long_press_fired = False
                    elif key_event.keystate == key_event.key_up:
                        if power_press_started_at is not None:
                            held_for = time.monotonic() - power_press_started_at
                            if held_for < LONG_PRESS_SECONDS:
                                print(f"Power button short press ({held_for:.1f}s) "
                                      "-- showing shutdown menu")
                                launch_power_menu()
                            # Held >= LONG_PRESS_SECONDS was already
                            # handled by the poll loop above, at the
                            # moment it crossed the threshold.
                        power_press_started_at = None
                    continue

                if key_event.keystate != key_event.key_down:
                    continue
                action = KEY_ACTIONS.get(key_event.keycode)
                if action:
                    action()


if __name__ == "__main__":
    # Initialize both rails to OFF on boot so state matches hardware.
    for pin in gpio_state:
        gpio_set(pin, False)

    configure_pmic_hardware_failsafe()
    main()
