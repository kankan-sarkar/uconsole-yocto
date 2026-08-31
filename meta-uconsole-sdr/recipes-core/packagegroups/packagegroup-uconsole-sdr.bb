SUMMARY = "uConsole SDR/RF tool stack (requirement.md 5.1)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

PACKAGE_ARCH = "${MACHINE_ARCH}"

inherit packagegroup

RDEPENDS:${PN} = " \
    packagegroup-sdr-gnuradio-base \
    packagegroup-sdr-rtlsdr \
    libhackrf \
    gr-osmosdr \
    soapysdr \
    soapysdr-module-rtlsdr \
    soapysdr-module-hackrf \
    rtl-433 \
    multimon-ng \
    gqrx \
    direwolf \
    dump1090 \
    gpsd \
    gpsd-conf \
    gps-utils \
    wireshark \
    python3-numpy \
"
