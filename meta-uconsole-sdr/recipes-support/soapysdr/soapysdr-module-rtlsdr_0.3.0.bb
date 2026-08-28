SUMMARY = "SoapySDR module for RTL-SDR devices"
HOMEPAGE = "https://github.com/pothosware/SoapyRTLSDR"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=76c8dd204c0791e9a30c30d0406b75da"

DEPENDS = "soapysdr rtl-sdr"

SRC_URI = "git://github.com/pothosware/SoapyRTLSDR.git;branch=master;protocol=https"
SRCREV = "ae8fb0845232c552b6c2e0c0074f2dfc332e5fac"
PV = "0.3.0"

S = "${WORKDIR}/git"

inherit cmake pkgconfig

FILES:${PN} += "${libdir}/SoapySDR"
