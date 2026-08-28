#!/usr/bin/env python3
import configparser
import sys
import threading
import time

import serial
import paho.mqtt.client as mqtt

# ---------------------------------------------------------
# UConsole LoRa <-> MQTT Bridge
# ---------------------------------------------------------
# Bidirectional bridge between the AIO v2 LoRa module (plain serial,
# newline-delimited text frames) and the local mosquitto broker, per
# requirement.md 5.6. Inbound LoRa lines are published to
# <topic_prefix>/rx; anything published to <topic_prefix>/tx is
# written out to the LoRa module.

CONFIG_FILE = "/etc/uconsole/lora-mqtt.conf"

DEFAULTS = {
    "serial": {"port": "/dev/ttyAMA0", "baud": "9600"},
    "mqtt": {
        "host": "localhost",
        "port": "1883",
        "topic_prefix": "uconsole/lora",
        "username": "",
        "password": "",
    },
}


def load_config():
    cfg = configparser.ConfigParser()
    cfg.read_dict(DEFAULTS)
    cfg.read(CONFIG_FILE)
    return cfg


def main():
    cfg = load_config()

    port = cfg.get("serial", "port")
    baud = cfg.getint("serial", "baud")
    host = cfg.get("mqtt", "host")
    mqtt_port = cfg.getint("mqtt", "port")
    prefix = cfg.get("mqtt", "topic_prefix")
    username = cfg.get("mqtt", "username")
    password = cfg.get("mqtt", "password")

    rx_topic = f"{prefix}/rx"
    tx_topic = f"{prefix}/tx"

    try:
        ser = serial.Serial(port, baud, timeout=1)
    except Exception as e:
        print(f"Failed to open LoRa serial port {port}: {e}")
        sys.exit(1)

    client = mqtt.Client()
    if username:
        client.username_pw_set(username, password or None)

    def on_connect(c, userdata, flags, rc):
        print(f"Connected to MQTT broker at {host}:{mqtt_port} (rc={rc})")
        c.subscribe(tx_topic)

    def on_message(c, userdata, msg):
        payload = msg.payload
        try:
            ser.write(payload + b"\n")
            print(f"MQTT->LoRa: {payload!r}")
        except Exception as e:
            print(f"Failed writing to LoRa serial: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, mqtt_port, keepalive=60)

    def serial_reader():
        while True:
            try:
                line = ser.readline()
                if line:
                    client.publish(rx_topic, line.strip())
                    print(f"LoRa->MQTT: {line!r}")
            except Exception as e:
                print(f"Serial read error: {e}")
                time.sleep(1)

    threading.Thread(target=serial_reader, daemon=True).start()
    client.loop_forever()


if __name__ == "__main__":
    main()
