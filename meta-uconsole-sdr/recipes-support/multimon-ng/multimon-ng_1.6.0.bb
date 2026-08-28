SUMMARY = "Digital transmission decoder (POCSAG, AFSK, ZVEI, and more)"
HOMEPAGE = "https://github.com/EliasOenal/multimon-ng"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=b234ee4d69f5fce4486a80fdaf4a4263"

DEPENDS = "pulseaudio"

SRC_URI = "git://github.com/EliasOenal/multimon-ng.git;branch=master;protocol=https"
SRCREV = "de0585926542687155852db502a9d2861e9acf95"
PV = "1.6.0"

S = "${WORKDIR}/git"

inherit cmake pkgconfig

# No X11 on this Wayland-only image; feed captured audio in via stdin
# from rtl_fm/sox instead of a live X11 waterfall.
EXTRA_OECMAKE = " \
    -DX11_SUPPORT=OFF \
    -DSDL3_SCOPE=OFF \
"
