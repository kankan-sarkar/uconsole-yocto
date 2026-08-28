SUMMARY = "Shared dark/light theme module for uConsole PyQt6 apps"
DESCRIPTION = "Single source of truth for theme_mode/accent_color set by the OOBE wizard, read by the lock screen and control panel"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://uconsole_theme.py"

S = "${WORKDIR}"

inherit python3-dir

RDEPENDS:${PN} = "python3-core python3-json"

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}
    install -m 0644 ${S}/uconsole_theme.py ${D}${PYTHON_SITEPACKAGES_DIR}/
}

FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}"
