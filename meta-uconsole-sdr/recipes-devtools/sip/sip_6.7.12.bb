# Adapted from meta-openembedded's meta-oe (nanbield branch) recipe of
# the same name/version -- that recipe isn't present on the kirkstone
# branch we're pinned to, but it only uses stable oe-core classes
# (pypi/setuptools3/python3native), so it's portable as-is. Tarball
# sha256 and LICENSE-GPL2 md5 both independently re-verified against
# the real PyPI sdist rather than trusted blindly.
#
# python3-pyqt6 (meta-qt6) DEPENDS on "sip (>= 6.7.12)" and
# "sip-native (>= 6.7.12)" -- the only "sip" available anywhere in our
# other layers is meta-oe's sip3_4.19.23.bb, which is the old SIP 4.x
# tool for PyQt5-era bindings, not this one.

SUMMARY = "A Python bindings generator for C/C++ libraries"

HOMEPAGE = "https://www.riverbankcomputing.com/software/sip/"
LICENSE = "GPL-2.0-or-later"
SECTION = "devel"
LIC_FILES_CHKSUM = "file://LICENSE-GPL2;md5=e91355d8a6f8bd8f7c699d62863c7303"

inherit pypi setuptools3 python3native

PYPI_PACKAGE = "sip"
SRC_URI[sha256sum] = "08e66f742592eb818ac8fda4173e2ed64c9f2d40b70bee11db1c499127d98450"

BBCLASSEXTEND = "native"
