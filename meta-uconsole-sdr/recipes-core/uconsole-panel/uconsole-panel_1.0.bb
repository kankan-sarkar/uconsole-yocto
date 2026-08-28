SUMMARY = "UConsole on-demand control panel (CPU governor, GPIO, brightness, radios)"
DESCRIPTION = "PyQt6 dashboard summoned by the F12 hotkey, per requirement.md 5.3"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://uconsole-panel.py"

S = "${WORKDIR}"

RDEPENDS:${PN} = "python3-core python3-pyqt6 libgpiod-tools networkmanager rfkill uconsole-theme"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-panel.py ${D}${bindir}/uconsole-panel
}
