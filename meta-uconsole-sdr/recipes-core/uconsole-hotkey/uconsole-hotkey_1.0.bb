SUMMARY = "UConsole Hotkey Daemon"
DESCRIPTION = "Python evdev daemon to toggle AIO v2 GPIO rails via keyboard matrix"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-hotkey.py \
    file://uconsole-hotkey.service \
"

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3-core python3-evdev libgpiod-tools"

SYSTEMD_SERVICE:${PN} = "uconsole-hotkey.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-hotkey.py ${D}${bindir}/uconsole-hotkey

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/uconsole-hotkey.service ${D}${systemd_system_unitdir}/
}
