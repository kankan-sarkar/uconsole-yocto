SUMMARY = "uConsole software stack, built for qemux86-64 sanity testing"
DESCRIPTION = "Same login/systemd/Weston/OOBE wiring as uconsole-image, \
minus the SDR/RF toolchain and anything that only makes sense on real \
uconsole-cm4 hardware, so it can boot under runqemu for fast iteration \
without a real SD-card flash cycle. \
\
What this CAN catch: systemd target wiring (this is exactly how the \
missing graphical.target default was found), PAM/login/lockout \
behavior, whether Weston starts and a Wayland client (uconsole-oobe) \
successfully attaches to it, package installation problems. \
\
What this CANNOT catch: anything about the real DSI panel, AXP221 \
PMIC, physical power button, or the USB-HID keyboard MCU -- none of \
that hardware has a QEMU model. uconsole-hotkey.py is expected to \
print 'Could not find uConsole keyboard or power button' and exit --\
that's the daemon behaving correctly when its hardware genuinely \
isn't there, not a bug to chase here. Real hardware is still the only \
way to validate those. See scripts/run-qemu-test.sh for how to boot \
this."

require uconsole-image-common.inc

IMAGE_INSTALL += " \
    weston \
    weston-init \
    uconsole-theme \
    uconsole-oobe \
    uconsole-hotkey \
    uconsole-idle-lock \
    uconsole-panel \
    uconsole-shell \
    uconsole-systemd-preset \
    python3-pyqt6 \
    networkmanager \
    python3-networkmanager \
"

IMAGE_ROOTFS_EXTRA_SPACE = "524288"
