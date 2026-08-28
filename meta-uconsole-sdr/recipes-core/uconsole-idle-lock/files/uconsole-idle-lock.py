#!/usr/bin/env python3
import glob
import json
import os
import select
import subprocess
import time

import evdev

# ---------------------------------------------------------
# UConsole Idle Timeout / Screen Lock Trigger
# ---------------------------------------------------------
# Watches all input devices for activity. After the configured idle
# timeout it blanks the DSI backlight to save battery while background
# daemons (SDR logging, MQTT, telemetry) keep running untouched. The
# next keypress/touch wakes the display and shows uconsole-lock.py --
# it never auto-unlocks on wake (requirement.md 7).

SETTINGS_FILE = "/etc/uconsole/settings.json"
DEFAULT_TIMEOUT_SECONDS = 120
LOCK_BIN = "/usr/bin/uconsole-lock"
BACKLIGHT_POWER_GLOB = "/sys/class/backlight/*/bl_power"


def load_timeout():
    try:
        with open(SETTINGS_FILE) as f:
            return int(json.load(f).get("idle_timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    except Exception:
        return DEFAULT_TIMEOUT_SECONDS


def backlight_off(off):
    for path in glob.glob(BACKLIGHT_POWER_GLOB):
        try:
            with open(path, "w") as f:
                f.write("1" if off else "0")
        except Exception as e:
            print(f"Failed to set backlight power on {path}: {e}")


def spawn_lock_screen():
    env = dict(os.environ, WAYLAND_DISPLAY="wayland-1", QT_QPA_PLATFORM="wayland")
    return subprocess.Popen([LOCK_BIN], env=env)


def open_input_devices():
    devices = []
    for path in evdev.list_devices():
        try:
            devices.append(evdev.InputDevice(path))
        except OSError:
            continue
    return devices


def main():
    devices = open_input_devices()
    if not devices:
        print("No input devices found; idle-lock daemon has nothing to watch.")
        return

    fd_to_dev = {dev.fd: dev for dev in devices}
    state = "active"  # active -> blanked -> locked -> active
    last_activity = time.time()
    lock_proc = None

    while True:
        timeout = load_timeout()
        ready, _, _ = select.select(list(fd_to_dev.keys()), [], [], 1.0)

        if ready:
            for fd in ready:
                try:
                    for _ in fd_to_dev[fd].read():
                        pass
                except OSError:
                    pass

            if state == "active":
                last_activity = time.time()
            elif state == "blanked":
                backlight_off(False)
                lock_proc = spawn_lock_screen()
                state = "locked"
        elif state == "active" and (time.time() - last_activity) >= timeout:
            backlight_off(True)
            state = "blanked"

        if state == "locked" and lock_proc is not None and lock_proc.poll() is not None:
            state = "active"
            last_activity = time.time()
            lock_proc = None


if __name__ == "__main__":
    main()
