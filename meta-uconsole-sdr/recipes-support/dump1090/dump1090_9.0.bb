SUMMARY = "Mode S / ADS-B decoder for RTL-SDR (aircraft tracking)"
HOMEPAGE = "https://github.com/flightaware/dump1090"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=751419260aa954499f7abaabaa882bbe"

DEPENDS = "rtl-sdr ncurses"

SRC_URI = "git://github.com/flightaware/dump1090.git;branch=master;protocol=https"
SRCREV = "a80ba8f82a74c90a29619ddbc10909c561198541"
PV = "9.0"

S = "${WORKDIR}/git"

# Plain Makefile project (no autotools/cmake) driven entirely through
# pkg-config feature detection, so just point it at librtlsdr and let
# it disable the other (unavailable) SDR backends.
EXTRA_OEMAKE = "RTLSDR=yes BLADERF=no HACKRF=no LIMESDR=no SOAPYSDR=no DUMP1090_VERSION=${PV}"

do_compile() {
    oe_runmake
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/dump1090 ${D}${bindir}/dump1090
    install -m 0755 ${B}/view1090 ${D}${bindir}/view1090
}

FILES:${PN} += "${bindir}/*"
