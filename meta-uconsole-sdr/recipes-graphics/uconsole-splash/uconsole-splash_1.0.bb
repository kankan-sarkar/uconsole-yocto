SUMMARY = "UConsole plymouth boot splash theme"
DESCRIPTION = "Default plymouth theme, replaceable by the OOBE wizard's splash upload (requirement.md 8)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole.plymouth \
    file://uconsole.script \
"

S = "${WORKDIR}"

RDEPENDS:${PN} = "plymouth"

THEME_DIR = "${datadir}/plymouth/themes/uconsole"

do_install() {
    install -d ${D}${THEME_DIR}
    install -m 0644 ${S}/uconsole.plymouth ${D}${THEME_DIR}/
    install -m 0644 ${S}/uconsole.script ${D}${THEME_DIR}/
}

FILES:${PN} += "${THEME_DIR}"

pkg_postinst:${PN}() {
    plymouth-set-default-theme uconsole || true
}
