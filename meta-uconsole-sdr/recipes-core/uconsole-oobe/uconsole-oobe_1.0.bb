SUMMARY = "UConsole Out-Of-Box Experience & Security Wizard"
DESCRIPTION = "PyQt6 based wizard for first boot customization and lock screen management"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-oobe.py \
    file://uconsole-lock.py \
    file://oobe.service \
"

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3-core python3-pyqt6 networkmanager python3-networkmanager shadow plymouth weston weston-init uconsole-theme"

SYSTEMD_SERVICE:${PN} = "oobe.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-oobe.py ${D}${bindir}/uconsole-oobe
    install -m 0755 ${S}/uconsole-lock.py ${D}${bindir}/uconsole-lock

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/oobe.service ${D}${systemd_system_unitdir}/
}
