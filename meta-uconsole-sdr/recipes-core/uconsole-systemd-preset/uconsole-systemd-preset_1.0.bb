SUMMARY = "UConsole systemd boot-time service policy (requirement.md 6)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://90-uconsole.preset"

S = "${WORKDIR}"

PRESET_DIR = "${nonarch_base_libdir}/systemd/system-preset"

do_install() {
    install -d ${D}${PRESET_DIR}
    install -m 0644 ${S}/90-uconsole.preset ${D}${PRESET_DIR}/
}

FILES:${PN} += "${PRESET_DIR}"
