SUMMARY = "UConsole home screen: Dock, app search, network/battery/VPN status"
DESCRIPTION = "Persistent PyQt6 home screen filling the gap left by \
switching Weston to kiosk-shell.so (see weston-init.bbappend) -- \
kiosk-shell draws no panel or background of its own, so without this \
the screen would just be black whenever no app is running. Provides a \
Dock of installed apps, a translucent search-and-launch overlay, and \
network/battery/VPN status, all reachable via global hotkeys handled \
by uconsole-hotkey.py (see its own RDEPENDS comment for why that has \
to be the one reading the keyboard, not this app)."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-shell.py \
    file://uconsole-shell.service \
"

S = "${WORKDIR}"

inherit systemd

# Same real bug as uconsole-oobe/uconsole-panel (see uconsole-oobe's
# RDEPENDS comment): a PyQt6 app run under QT_QPA_PLATFORM=wayland
# needs qtwayland-plugins explicitly, since PyQt6 itself is platform-
# agnostic and nothing else pulls the actual Wayland QPA plugin .so in.
RDEPENDS:${PN} = "python3-core python3-pyqt6 qtwayland-plugins networkmanager python3-networkmanager uconsole-theme"

SYSTEMD_SERVICE:${PN} = "uconsole-shell.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-shell.py ${D}${bindir}/uconsole-shell

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/uconsole-shell.service ${D}${systemd_system_unitdir}/
}
