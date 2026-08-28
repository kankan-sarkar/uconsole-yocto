FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += "file://gpsd.default"

# Bind gpsd to the AIO v2's GPS UART permanently so GUI tools (xgps,
# gpsmon) just connect to localhost:2947 with no manual port setup,
# per requirement.md 5.1.
do_install:append() {
    install -d ${D}${sysconfdir}/default
    install -m 0644 ${WORKDIR}/gpsd.default ${D}${sysconfdir}/default/gpsd.default
}
