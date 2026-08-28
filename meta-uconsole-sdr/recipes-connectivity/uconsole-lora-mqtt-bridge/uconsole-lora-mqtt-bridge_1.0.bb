SUMMARY = "UConsole LoRa <-> MQTT bridge daemon"
DESCRIPTION = "Bridges the AIO v2 LoRa module (serial) to the local mosquitto broker, per requirement.md 5.6"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://uconsole-lora-mqtt-bridge.py \
    file://uconsole-lora-mqtt-bridge.service \
    file://lora-mqtt.conf \
"

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3-core python3-pyserial python3-paho-mqtt"

SYSTEMD_SERVICE:${PN} = "uconsole-lora-mqtt-bridge.service"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/uconsole-lora-mqtt-bridge.py ${D}${bindir}/uconsole-lora-mqtt-bridge

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/uconsole-lora-mqtt-bridge.service ${D}${systemd_system_unitdir}/

    install -d ${D}${sysconfdir}/uconsole
    install -m 0644 ${S}/lora-mqtt.conf ${D}${sysconfdir}/uconsole/lora-mqtt.conf
}

CONFFILES:${PN} += "${sysconfdir}/uconsole/lora-mqtt.conf"
