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

# Real crash, found via QEMU testing: qt.qpa.plugin: Could not find the
# Qt platform plugin "wayland" in "" -- oobe.service sets
# QT_QPA_PLATFORM=wayland (see oobe.service), but nothing pulled in the
# actual plugin .so that implements it. meta-qt6's own qt6.inc packages
# every Qt6 plugin (the wayland QPA backend included) into
# ${PN}-plugins for each Qt6 recipe, not into the recipe's main
# package -- confirmed by reading qt6.inc's own FILES:${PN}-plugins
# definition. python3-pyqt6 depends on qtbase/qtdeclarative for its
# bindings, but never on qtwayland, since PyQt6 itself is platform-
# agnostic; something consuming it under Wayland has to pull the
# plugin in explicitly.
RDEPENDS:${PN} = "python3-core python3-pyqt6 qtwayland-plugins networkmanager python3-networkmanager shadow plymouth weston weston-init uconsole-theme"

SYSTEMD_SERVICE:${PN} = "oobe.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-oobe.py ${D}${bindir}/uconsole-oobe
    install -m 0755 ${S}/uconsole-lock.py ${D}${bindir}/uconsole-lock

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/oobe.service ${D}${systemd_system_unitdir}/
}
