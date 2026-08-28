SUMMARY = "uConsole networking, audio, telemetry, IoT and Python baseline (requirement.md 4.3-4.4, 5.2, 5.5-5.6)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

PACKAGE_ARCH = "${MACHINE_ARCH}"

inherit packagegroup

RDEPENDS:${PN} = " \
    sudo \
    shadow \
    polkit \
    networkmanager \
    python3-networkmanager \
    tmux \
    pipewire \
    wireplumber \
    pipewire-alsa \
    alsa-utils \
    cpufrequtils \
    htop \
    iotop \
    sysstat \
    netdata \
    nginx \
    mosquitto \
    mosquitto-clients \
    python3-core \
    python3-pip \
    python3-numpy \
    python3-paho-mqtt \
    python3-pyserial \
    python3-pyqt6 \
"
