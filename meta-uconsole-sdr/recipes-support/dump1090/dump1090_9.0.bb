SUMMARY = "Mode S / ADS-B decoder for RTL-SDR (aircraft tracking)"
HOMEPAGE = "https://github.com/flightaware/dump1090"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=751419260aa954499f7abaabaa882bbe"

DEPENDS = "rtl-sdr ncurses pkgconfig-native"

SRC_URI = "git://github.com/flightaware/dump1090.git;branch=master;protocol=https"
SRCREV = "a80ba8f82a74c90a29619ddbc10909c561198541"
PV = "9.0"

S = "${WORKDIR}/git"

inherit pkgconfig

# Plain Makefile project (no autotools/cmake) driven entirely through
# pkg-config feature detection, so just point it at librtlsdr and let
# it disable the other (unavailable) SDR backends.
#
# ARCH must be passed explicitly: the Makefile defaults it to
# `uname -m` (the *build host's* architecture, x86_64 on hs01) via
# `ARCH ?= $(shell uname -m)`, used to pick both the DSP "starch mix"
# and, via Makefile.cpufeatures (CPUFEATURES_ARCH ?= $(ARCH)), which
# cpu_features backend to compile. Without this override it silently
# tried to build the x86-only cpuinfo_x86.c (CPUID-based detection)
# under the aarch64 cross-compiler, which fails fast on its own
# guard: "#error Including cpuinfo_x86.h from a non-x86 target."
# ${TARGET_ARCH} matches the Makefile's expected values (aarch64) via
# its `findstring aarch64` check.
EXTRA_OEMAKE = "ARCH=${TARGET_ARCH} RTLSDR=yes BLADERF=no HACKRF=no LIMESDR=no SOAPYSDR=no DUMP1090_VERSION=${PV}"

do_compile() {
    oe_runmake
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/dump1090 ${D}${bindir}/dump1090
    install -m 0755 ${B}/view1090 ${D}${bindir}/view1090
}

FILES:${PN} += "${bindir}/*"
