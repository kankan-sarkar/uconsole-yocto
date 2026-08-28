SUMMARY = "Decoder for many common ISM band radio protocols (weather stations, TPMS, IoT sensors)"
HOMEPAGE = "https://github.com/merbanan/rtl_433"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=751419260aa954499f7abaabaa882bbe"

DEPENDS = "rtl-sdr openssl"

SRC_URI = "git://github.com/merbanan/rtl_433.git;branch=master;protocol=https"
SRCREV = "ea7d504877df751a202432d47dbb0c425ab0a93c"
PV = "25.12"

S = "${WORKDIR}/git"

inherit cmake pkgconfig

# SoapySDR support is optional upstream; leave it off so this recipe
# doesn't force an ordering dependency on the soapysdr recipes -- add
# "soapysdr" to DEPENDS and drop this if combined SDR-backend capture
# is wanted later.
EXTRA_OECMAKE = "-DENABLE_SOAPYSDR=OFF"
