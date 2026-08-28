SUMMARY = "SoapySDR module for HackRF devices"
HOMEPAGE = "https://github.com/pothosware/SoapyHackRF"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=71a52831f2bbba1383d42d9390458df8"

DEPENDS = "soapysdr libhackrf"

SRC_URI = "git://github.com/pothosware/SoapyHackRF.git;branch=master;protocol=https"
SRCREV = "5d78799d432c085df8cfda86a3ca646270eab67d"
PV = "0.3.4"

S = "${WORKDIR}/git"

inherit cmake pkgconfig

FILES:${PN} += "${libdir}/SoapySDR"
