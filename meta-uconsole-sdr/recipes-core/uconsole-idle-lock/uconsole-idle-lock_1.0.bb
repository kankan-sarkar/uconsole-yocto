SUMMARY = "UConsole idle timeout and screen lock trigger daemon"
DESCRIPTION = "Blanks the backlight after an idle timeout and summons uconsole-lock on wake, per requirement.md 7"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-idle-lock.py \
    file://uconsole-idle-lock.service \
"

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3-core python3-evdev uconsole-oobe"

SYSTEMD_SERVICE:${PN} = "uconsole-idle-lock.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-idle-lock.py ${D}${bindir}/uconsole-idle-lock

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/uconsole-idle-lock.service ${D}${systemd_system_unitdir}/
}
