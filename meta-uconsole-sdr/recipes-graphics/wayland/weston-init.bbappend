FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://weston.ini \
    file://10-uconsole-vt.conf \
"

# The VT fix ships as a drop-in rather than a patched weston.service, so
# it survives upstream changing that unit and stays obviously ours.
# See the file's own comment for what it fixes and how it was pinned down.
do_install:append() {
    install -D -p -m0644 ${WORKDIR}/weston.ini ${D}${sysconfdir}/xdg/weston/weston.ini
    install -D -p -m0644 ${WORKDIR}/10-uconsole-vt.conf \
        ${D}${systemd_system_unitdir}/weston.service.d/10-uconsole-vt.conf
}

FILES:${PN} += "${systemd_system_unitdir}/weston.service.d"

# chvt comes from kbd; without it the drop-in above silently fails and
# Weston is back to racing the console for the active VT.
RDEPENDS:${PN} += "kbd"
