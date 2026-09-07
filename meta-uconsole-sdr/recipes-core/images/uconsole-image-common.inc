# Shared between uconsole-image.bb (real uconsole-cm4 hardware) and
# uconsole-image-qemu-test.bb (qemux86-64, for fast pre-flash sanity
# checks -- see that recipe's own comment for what it can and can't
# actually validate). Kept in one place so a login/systemd fix found
# on either target automatically applies to both, rather than the two
# images silently drifting apart.

LICENSE = "MIT"

inherit core-image extrausers

IMAGE_FEATURES += "ssh-server-openssh"

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
#
# Second account added as a diagnostic: root logins have been
# consistently rejected on real hardware even with this exact hash
# confirmed correct at the file level (permissions, PAM stack, and
# /etc/securetty all checked out too) -- current leading theory is
# pam_faillock's deny=5/unlock_time=60 (see common-auth) locking root
# out from the many attempts made while diagnosing this, possibly
# compounded by the device's clock not being reliably set at boot
# (no confirmed-working RTC yet -- see HARDWARE_STATUS.md) confusing
# unlock_time's wall-clock comparison. A brand-new account has no
# failure history, so if *this* one logs in fine, that confirms the
# lockout theory rather than a deeper PAM/hash problem. Same password
# hash reused deliberately -- crypt hashes aren't tied to a username,
# and the point here is a matching, memorable password, not a
# different one. -G sudo since this needs to be a full admin account,
# not a restricted one, until root itself is sorted out.
EXTRA_USERS_PARAMS = "\
    usermod -p '\$6\$uconsole\$2Za1/ZgSaHIRYRsoCx3U.Tb.h90Jng.pBeJxnjEZhjoDhfVlyLr36SOg9aiI7f1eEPaeUc89a/05xLn.I2.Md/' root; \
    passwd-expire root; \
    useradd -m -s /bin/sh -G sudo -p '\$6\$uconsole\$2Za1/ZgSaHIRYRsoCx3U.Tb.h90Jng.pBeJxnjEZhjoDhfVlyLr36SOg9aiI7f1eEPaeUc89a/05xLn.I2.Md/' uconsole; \
    passwd-expire uconsole; \
"

# Build identification. Bump UCONSOLE_IMAGE_VERSION's letter suffix
# (a, b, c, ...) by hand on every meaningful change to this project --
# there's no automatic counter, it's a manually-maintained release
# tag. The point: this is the single, unambiguous, zero-login way to
# confirm exactly which build is on a given SD card, which several
# rounds of "is this actually the image I think it is?" confusion
# during hardware bring-up would have been solved by immediately.
# Shown at every login prompt (serial or local, before auth) via
# /etc/issue, and readable any time from a shell via
# /etc/uconsole-version.
#
# Real build error caught this: bitbake's ${DATETIME} is recomputed
# fresh on every metadata reparse (bitbake parses recipes multiple
# times per invocation, not once), so textually substituting it into
# a task function's body made do_rootfs's own basehash non-
# deterministic within a single build -- exactly what bitbake's
# "metadata is not deterministic" check exists to catch. Fixed by
# calling `date` live inside the shell function instead: the
# function's own text (what bitbake hashes) is now a fixed string,
# while the actual timestamp is still produced fresh at real
# execution time, not at parse time.
UCONSOLE_IMAGE_VERSION = "1.0.0f"

uconsole_write_version_banner () {
    build_date=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    banner="uConsole image ${UCONSOLE_IMAGE_VERSION} (${PN}) -- built $build_date"
    echo "$banner" > ${IMAGE_ROOTFS}${sysconfdir}/uconsole-version
    { echo "$banner"; echo; cat ${IMAGE_ROOTFS}${sysconfdir}/issue 2>/dev/null; } > ${IMAGE_ROOTFS}${sysconfdir}/issue.uconsole_new
    mv ${IMAGE_ROOTFS}${sysconfdir}/issue.uconsole_new ${IMAGE_ROOTFS}${sysconfdir}/issue
}
ROOTFS_POSTPROCESS_COMMAND += "uconsole_write_version_banner;"

# Real hardware caught this: the screen never showed anything but the
# plain kernel text console, no matter what else was fixed, because
# nothing in this project ever set the systemd default target --
# confirmed directly in the built rootfs: /etc/systemd/system/
# default.target symlinked to multi-user.target, poky's own base
# default. weston.service and uconsole-oobe's oobe.service are both
# WantedBy=graphical.target (already correctly enabled -- confirmed
# weston.service is symlinked under graphical.target.wants/), but
# graphical.target itself was simply never reached at boot, so
# neither ever started. This is exactly the class of bug
# uconsole-image-qemu-test.bb exists to catch before a flash cycle --
# it's pure systemd/config wiring, nothing hardware-specific about it.
set_graphical_target () {
    ln -sf ${systemd_unitdir}/system/graphical.target ${IMAGE_ROOTFS}${sysconfdir}/systemd/system/default.target
}
ROOTFS_POSTPROCESS_COMMAND += "set_graphical_target;"
