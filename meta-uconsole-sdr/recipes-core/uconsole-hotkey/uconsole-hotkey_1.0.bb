SUMMARY = "UConsole Hotkey Daemon"
DESCRIPTION = "Python evdev daemon to toggle AIO v2 GPIO rails via keyboard \
matrix, and to own the physical power button (short press -> shutdown \
menu, long press -> forced poweroff) via the axp20x-pek input device."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-hotkey.py \
    file://uconsole-hotkey.service \
    file://90-uconsole-power-button.conf \
"

S = "${WORKDIR}"

inherit systemd

# uconsole-panel: both the F12 control panel and (new) uconsole-power-menu
# are launched by path from uconsole-hotkey.py -- previously undeclared
# for the control panel too, fixed here alongside the power-menu addition.
RDEPENDS:${PN} = "python3-core python3-evdev libgpiod-tools systemd uconsole-panel"

SYSTEMD_SERVICE:${PN} = "uconsole-hotkey.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-hotkey.py ${D}${bindir}/uconsole-hotkey

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/uconsole-hotkey.service ${D}${systemd_system_unitdir}/

    install -d ${D}${sysconfdir}/systemd/logind.conf.d
    install -m 0644 ${S}/90-uconsole-power-button.conf \
        ${D}${sysconfdir}/systemd/logind.conf.d/
}

FILES:${PN} += "${sysconfdir}/systemd/logind.conf.d/90-uconsole-power-button.conf"
CONFFILES:${PN} += "${sysconfdir}/systemd/logind.conf.d/90-uconsole-power-button.conf"
