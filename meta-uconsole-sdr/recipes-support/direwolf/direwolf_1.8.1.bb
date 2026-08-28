SUMMARY = "Soundcard TNC for APRS / AX.25 packet radio decoding"
HOMEPAGE = "https://github.com/wb2osz/direwolf"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=fa22e16ebbe6638b2bd253338fbded9f"

DEPENDS = "alsa-lib"

SRC_URI = "git://github.com/wb2osz/direwolf.git;branch=master;protocol=https"
SRCREV = "a231971a652bfb574a4bae9a5d875fbce53d2267"
PV = "1.8.1"

S = "${WORKDIR}/git"

inherit cmake pkgconfig

# GPSD/hamlib/gpiod support are optional upstream (bare find_package,
# no REQUIRED) and will no-op if their headers aren't in the sysroot;
# not adding them to DEPENDS here keeps this recipe's dependency
# surface small. Add gpsd/hamlib to DEPENDS later to enable those.
