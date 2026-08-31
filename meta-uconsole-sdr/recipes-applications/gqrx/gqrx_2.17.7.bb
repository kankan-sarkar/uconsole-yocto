SUMMARY = "SDR powered by GNU Radio and Qt"
HOMEPAGE = "http://gqrx.dk/"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=d32239bcb673463ab874e80d47fae504"

# Own recipe rather than meta-sdr's recipes-applications/gqrx/gqrx_git.bb
# (which stays BBMASK'd out in kas-project.yml -- see gqrx_bbmask). That
# recipe is pinned to 2.15.9, predating upstream's Qt6 support and hard
# `inherit cmake_qt5` (a class that doesn't exist now meta-qt5 is gone).
# v2.17.7's CMakeLists.txt added a FORCE_QT6 option that finds Qt6's
# Core/Network/Widgets/Svg/SvgWidgets components directly -- verified
# against the actual tag content -- so this can build against the same
# Qt6 (meta-qt6) already used for python3-pyqt6 without any Qt5 layer.
DEPENDS = "gnuradio gr-osmosdr qtbase qtsvg"

# Plain `cmake` isn't enough for a Qt6 CMake app under cross-compile:
# Qt6's own CMake modules (Qt6Dependencies.cmake) need to invoke host
# tools (moc/uic/rcc) during configure, which requires QT_HOST_PATH
# pointing at a native Qt6 install -- confirmed via the real failure:
# "To use a cross-compiled Qt, please set the QT_HOST_PATH cache
# variable". meta-qt6's qt6-cmake.bbclass (verified against its actual
# content) is exactly this: inherits cmake, prepends qtbase-native to
# DEPENDS, and passes -DQT_HOST_PATH pointing at the native sysroot.
inherit qt6-cmake

SRC_URI = "git://github.com/gqrx-sdr/gqrx.git;branch=master;protocol=https"
SRCREV = "1a8ab3a3cc02db3bf4c9058ed4b60ddad06fe9d1"
PV = "2.17.7"

S = "${WORKDIR}/git"

# Gr-audio avoids requiring PulseAudio/PortAudio entirely (verified in
# CMakeLists.txt: only Pulseaudio/Portaudio branches call
# find_package(PulseAudio|PORTAUDIO REQUIRED)), so no extra DEPENDS
# needed for audio output.
EXTRA_OECMAKE = "-DLINUX_AUDIO_BACKEND=Gr-audio -DFORCE_QT6=ON"

FILES:${PN} += "${datadir}"
