SUMMARY = "uConsole CM4 Field Operations & SDR Rig image"
DESCRIPTION = "Custom field-ops image: Weston/Wayland UI, SDR/RF tool \
stack, IoT/telemetry services and the uConsole OOBE/security wizard. \
See requirement.md at the top of the repo for the full spec this \
image is built against."

LICENSE = "MIT"

inherit core-image extrausers

IMAGE_FEATURES += " \
    ssh-server-openssh \
    splash \
"

# Fallback login for hardware bring-up. Root's real password normally
# comes from uconsole-oobe's first-boot PIN wizard (sync_unix_password
# in uconsole-oobe.py) -- but that wizard depends on Weston and a DSI
# panel driver that, as of this image, have never run on real
# hardware. Without this, a wizard that doesn't come up leaves root
# with no password at all and no way in, not even over serial.
#
# Real build caught this: extrausers.bbclass passes EXTRA_USERS_PARAMS
# straight through to the real usermod binary with no translation --
# there's no OE-side "-P means plaintext password" magic (confirmed
# by reading useradd_base.bbclass's perform_usermod). This project's
# shadow-utils version defines -P as --prefix (a chroot-directory
# option, unrelated to passwords), so `usermod -P uconsole root`
# failed with "prefix must be an absolute path" -- it was passing
# "uconsole" as a directory path, not a password. Older/other
# shadow-utils builds may not define -P at all, which is presumably
# why the "-P plaintext password" convention shows up copy-pasted
# across various BSP layers; it isn't a real, version-independent
# feature. The correct, version-independent way is shadow-utils' own
# documented -p (lowercase), which takes an already-encrypted
# password. Hash generated once with a fixed salt for a reproducible
# build: `openssl passwd -6 -salt uconsole uconsole`.
#
# passwd-expire forces PAM's standard change-password flow (prompts
# for the new password twice) at the very next login, whether that's
# a serial getty or SSH. If the OOBE wizard *does* run successfully,
# its own passwd call overwrites this and clears the expiry as a
# normal side effect -- no conflict either way.
#
# "uconsole" is a placeholder default, not a real security posture --
# revisit before this image goes anywhere near untrusted networks.
#
# Second real bug, found the same way (checking the actual built
# rootfs, not just a green build): set_user_group() does
# user_group_settings="${EXTRA_USERS_PARAMS}" -- bitbake pastes this
# value in literally, landing inside a DOUBLE-quoted shell string.
# Single quotes have no special meaning nested inside an already-
# double-quoted string, so they gave the hash's own $6/$uconsole/$2
# zero protection from real shell variable expansion (all three
# unset, so they silently vanished) -- confirmed by reproducing
# set_user_group's exact assignment by hand. Fix: escape every
# literal $ in the hash with a backslash, verified the same way to
# survive intact all the way to the final eval'd usermod command.
EXTRA_USERS_PARAMS = "\
    usermod -p '\$6\$uconsole\$2Za1/ZgSaHIRYRsoCx3U.Tb.h90Jng.pBeJxnjEZhjoDhfVlyLr36SOg9aiI7f1eEPaeUc89a/05xLn.I2.Md/' root; \
    passwd-expire root; \
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

# Build identification. Bump UCONSOLE_IMAGE_VERSION's letter suffix
# (a, b, c, ...) by hand on every meaningful change to this project --
# there's no automatic counter, it's a manually-maintained release
# tag. The point: this is the single, unambiguous, zero-login way to
# confirm exactly which build is on a given SD card, which several
# rounds of "is this actually the image I think it is?" confusion
# during hardware bring-up would have been solved by immediately.
# Shown at every login prompt (serial or local, before auth) via
# /etc/issue, and readable any time from a shell via
# /etc/uconsole-version. ${DATETIME} is bitbake's own build-start
# timestamp (UTC, YYYYMMDDHHMMSS) -- always fresh per build
# invocation, unaffected by sstate reuse of this task.
UCONSOLE_IMAGE_VERSION = "1.0.0a"

uconsole_write_version_banner () {
    banner="uConsole image ${UCONSOLE_IMAGE_VERSION} -- built ${DATETIME} (YYYYMMDDHHMMSS, UTC)"
    echo "$banner" > ${IMAGE_ROOTFS}${sysconfdir}/uconsole-version
    { echo "$banner"; echo; cat ${IMAGE_ROOTFS}${sysconfdir}/issue 2>/dev/null; } > ${IMAGE_ROOTFS}${sysconfdir}/issue.uconsole_new
    mv ${IMAGE_ROOTFS}${sysconfdir}/issue.uconsole_new ${IMAGE_ROOTFS}${sysconfdir}/issue
}
ROOTFS_POSTPROCESS_COMMAND += "uconsole_write_version_banner;"
