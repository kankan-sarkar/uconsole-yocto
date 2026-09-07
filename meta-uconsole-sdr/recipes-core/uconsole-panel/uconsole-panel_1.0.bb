SUMMARY = "UConsole on-demand control panel (CPU governor, GPIO, brightness, radios)"
DESCRIPTION = "PyQt6 dashboard summoned by the F12 hotkey, per requirement.md 5.3. \
Also carries uconsole-power-menu, the Shut Down/Restart/Cancel dialog \
the hotkey daemon summons on a short press of the physical power \
button -- same trust model and dependency set, not worth a separate \
recipe for one more small on-demand PyQt6 script."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-panel.py \
    file://uconsole-power-menu.py \
"

S = "${WORKDIR}"

# Same real bug as uconsole-oobe (see its RDEPENDS comment): this panel
# is also a PyQt6 app run under QT_QPA_PLATFORM=wayland (set by
# uconsole-hotkey when it launches it), so it needs the same
# qtwayland-plugins dependency for the actual Wayland QPA plugin .so.
RDEPENDS:${PN} = "python3-core python3-pyqt6 qtwayland-plugins libgpiod-tools networkmanager rfkill uconsole-theme"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-panel.py ${D}${bindir}/uconsole-panel
    install -m 0755 ${S}/uconsole-power-menu.py ${D}${bindir}/uconsole-power-menu
}
