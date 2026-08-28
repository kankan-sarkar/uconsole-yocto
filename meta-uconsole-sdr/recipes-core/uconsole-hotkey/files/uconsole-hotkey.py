#!/usr/bin/env python3
import evdev
import sys
import subprocess
from evdev import ecodes, categorize

# ---------------------------------------------------------
# UConsole Hardware Hotkey Daemon
# ---------------------------------------------------------
# Listens on the internal keyboard for dedicated function keys and
# toggles AIO v2 power rails via gpiod, or summons the on-screen
# control panel. State is tracked per GPIO line so repeated presses
# toggle rather than only ever turning things on.

GPIOCHIP = "gpiochip0"
SDR_GPIO_PIN = "23"   # Internal USB hub / SDR module power rail
GPS_GPIO_PIN = "27"   # GPS module power rail

CONTROL_PANEL_BIN = "/usr/bin/uconsole-panel"

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


def launch_control_panel():
    print("Summoning control panel")
    try:
        subprocess.Popen(
            [CONTROL_PANEL_BIN],
            env={
                **__import__("os").environ,
                "WAYLAND_DISPLAY": "wayland-1",
                "QT_QPA_PLATFORM": "wayland",
            },
        )
    except FileNotFoundError:
        print(f"Control panel binary not found at {CONTROL_PANEL_BIN}")
    except Exception as e:
        print(f"Failed to launch control panel: {e}")


# Map evdev keycodes to actions. F10/F11 toggle GPIO rails, F12 opens
# the dashboard the way the spec's "dedicated hardware hotkey" calls for.
KEY_ACTIONS = {
    "KEY_F10": lambda: toggle_gpio(SDR_GPIO_PIN, "SDR"),
    "KEY_F11": lambda: toggle_gpio(GPS_GPIO_PIN, "GPS"),
    "KEY_F12": launch_control_panel,
}


def find_uconsole_keyboard():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        name = device.name.lower()
        if "keyboard" in name or "clockwork" in name:
            return device
    return None


def main():
    dev = find_uconsole_keyboard()
    if not dev:
        print("Could not find uConsole keyboard. Exiting.")
        sys.exit(1)

    print(f"Listening for hotkeys on: {dev.name}")

    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate != key_event.key_down:
                continue
            action = KEY_ACTIONS.get(key_event.keycode)
            if action:
                action()


if __name__ == "__main__":
    # Initialize both rails to OFF on boot so state matches hardware.
    for pin in gpio_state:
        gpio_set(pin, False)

    main()
