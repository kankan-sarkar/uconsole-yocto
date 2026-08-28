SUMMARY = "uConsole CM4 Field Operations & SDR Rig image"
DESCRIPTION = "Custom field-ops image: Weston/Wayland UI, SDR/RF tool \
stack, IoT/telemetry services and the uConsole OOBE/security wizard. \
See requirement.md at the top of the repo for the full spec this \
image is built against."

LICENSE = "MIT"

inherit core-image

IMAGE_FEATURES += " \
    ssh-server-openssh \
    splash \
"

# weston/weston-init are also pulled in transitively via uconsole-oobe's
# RDEPENDS, but the compositor is fundamental enough to this image that
# it shouldn't depend on an unrelated first-boot-wizard package for its
# only path into the rootfs -- listed explicitly here too.
IMAGE_INSTALL += " \
    weston \
    weston-init \
    packagegroup-uconsole-sdr \
    packagegroup-uconsole-security \
    packagegroup-uconsole-base \
    uconsole-theme \
    uconsole-oobe \
    uconsole-hotkey \
    uconsole-idle-lock \
    uconsole-panel \
    uconsole-lora-mqtt-bridge \
    uconsole-splash \
    uconsole-systemd-preset \
"

IMAGE_ROOTFS_EXTRA_SPACE = "1048576"
