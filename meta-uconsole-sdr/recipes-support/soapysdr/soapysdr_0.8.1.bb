SUMMARY = "Vendor and platform neutral SDR support library"
HOMEPAGE = "https://github.com/pothosware/SoapySDR"
LICENSE = "BSL-1.0"
LIC_FILES_CHKSUM = "file://LICENSE_1_0.txt;md5=e4224ccaecb14d942c71d31bef20d78c"

DEPENDS = ""

SRC_URI = "git://github.com/pothosware/SoapySDR.git;branch=master;protocol=https"
SRCREV = "356aaabc9046bd05757a08c03a406b8ef9b88e21"
PV = "0.8.1"

S = "${WORKDIR}/git"

inherit cmake pkgconfig

# Python bindings and docs aren't needed on-target; keep this to the
# core library, module loader and the soapysdrutil CLI.
EXTRA_OECMAKE = " \
    -DENABLE_PYTHON=OFF \
    -DENABLE_PYTHON3=OFF \
    -DENABLE_DOCS=OFF \
"

FILES:${PN} += "${libdir}/SoapySDR"
