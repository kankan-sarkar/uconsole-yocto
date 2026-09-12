#!/bin/bash
# Flash a uConsole Yocto image onto an SD card, with safety checks and
# a full progress report. Designed to run on the build host.
#
# Usage:
#   flash-sd.sh <sd-card-device> [image-file]
#
#   <sd-card-device>   Whole-disk device to flash, e.g. /dev/sdb.
#                      Must be the whole disk, NOT a partition
#                      (/dev/sdb, not /dev/sdb1).
#   [image-file]       Path to a .wic / .wic.bz2 / .wic.gz image.
#                      Defaults to this checkout's own build output, or
#                      $UCONSOLE_IMAGE if that's set.
#
# Examples:
#   ./flash-sd.sh /dev/sdb
#   ./flash-sd.sh /dev/sdb /path/to/uconsole-image-uconsole-cm4.wic.bz2
#   UCONSOLE_IMAGE=~/actions-runner/_work/.../uconsole-image-uconsole-cm4.wic.bz2 ./flash-sd.sh /dev/sdb

set -euo pipefail

# Defaults to the image this checkout's own `kas build kas-project.yml`
# produces. Resolved relative to this script so it works from any
# checkout, rather than hardcoding one machine's layout. Override with
# UCONSOLE_IMAGE=/path/to/image.wic.bz2 (or pass the image as the second
# argument) to flash a build from somewhere else -- a CI runner's own
# _work checkout, for instance.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_IMAGE="${UCONSOLE_IMAGE:-$REPO_ROOT/build/tmp/deploy/images/uconsole-cm4/uconsole-image-uconsole-cm4.wic.bz2}"

usage() {
    cat >&2 <<EOF
Usage: $0 <sd-card-device> [image-file]

  <sd-card-device>  Whole-disk device to flash, e.g. /dev/sdb
                    (NOT a partition like /dev/sdb1)
  [image-file]      Path to a .wic / .wic.bz2 / .wic.gz image.
                    Default: $DEFAULT_IMAGE

Examples:
  $0 /dev/sdb
  $0 /dev/sdb /path/to/custom-image.wic.bz2
EOF
    exit 1
}

log()  { printf '\n==> %s\n' "$1"; }
die()  { printf 'ERROR: %s\n' "$1" >&2; exit 1; }

[ $# -ge 1 ] || usage
DEVICE="$1"
IMAGE="${2:-$DEFAULT_IMAGE}"

command -v lsblk  >/dev/null 2>&1 || die "lsblk not found"
command -v findmnt >/dev/null 2>&1 || die "findmnt not found"

# ------------------------------------------------------------------
# Safety checks -- these exist because a wrong device argument here
# means silently destroying the wrong disk.
# ------------------------------------------------------------------

[ -f "$IMAGE" ] || die "image file not found: $IMAGE"
[ -b "$DEVICE" ] || die "$DEVICE is not a block device"

DEV_TYPE=$(lsblk -no TYPE "$DEVICE" 2>/dev/null | head -1)
[ "$DEV_TYPE" = "disk" ] || die "$DEVICE is not a whole disk (type=$DEV_TYPE) -- pass the whole-disk device, not a partition"

ROOT_SRC=$(findmnt -no SOURCE / || true)
ROOT_DISK=$(lsblk -no PKNAME "$ROOT_SRC" 2>/dev/null || true)
if [ -n "$ROOT_DISK" ] && [ "/dev/$ROOT_DISK" = "$DEVICE" ]; then
    die "$DEVICE appears to be this machine's own root disk -- refusing to touch it"
fi

DEVICE_SIZE_HUMAN=$(lsblk -dno SIZE "$DEVICE")
DEVICE_MODEL=$(lsblk -dno MODEL "$DEVICE" | sed 's/ *$//')
IMAGE_SIZE_HUMAN=$(du -h "$IMAGE" | cut -f1)

echo "=================================================="
echo " Image : $IMAGE  ($IMAGE_SIZE_HUMAN compressed)"
echo " Device: $DEVICE  ($DEVICE_SIZE_HUMAN, model: ${DEVICE_MODEL:-unknown})"
echo "=================================================="
echo "THIS WILL ERASE EVERYTHING CURRENTLY ON $DEVICE."
read -r -p "Type 'yes' to continue: " CONFIRM
[ "$CONFIRM" = "yes" ] || die "aborted by user"

# ------------------------------------------------------------------
# Unmount any partitions currently mounted from the target device
# ------------------------------------------------------------------
log "Unmounting any mounted partitions on $DEVICE"
for part in $(lsblk -lno NAME "$DEVICE" | tail -n +2); do
    MOUNTPOINT=$(lsblk -no MOUNTPOINT "/dev/$part" 2>/dev/null || true)
    if [ -n "$MOUNTPOINT" ]; then
        echo "  unmounting /dev/$part from $MOUNTPOINT"
        sudo umount "/dev/$part"
    fi
done

# ------------------------------------------------------------------
# Flash -- prefer bmaptool (faster: skips empty space, decompresses
# on the fly, prints its own live progress) and fall back to a
# straight decompress-and-dd pipeline with dd's own status=progress
# reporting if bmaptool isn't installed.
# ------------------------------------------------------------------
START_TIME=$(date +%s)

decompressor_for() {
    case "$1" in
        *.bz2) echo "bzcat" ;;
        *.gz)  echo "zcat" ;;
        *)     echo "cat" ;;
    esac
}

if command -v bmaptool >/dev/null 2>&1; then
    BMAP_FILE="${IMAGE%.*}.bmap"
    log "Flashing with bmaptool"
    if [ -f "$BMAP_FILE" ]; then
        echo "  using bmap: $BMAP_FILE"
        sudo bmaptool copy --bmap "$BMAP_FILE" "$IMAGE" "$DEVICE"
    else
        echo "  no .bmap file found next to the image, copying without one"
        sudo bmaptool copy "$IMAGE" "$DEVICE"
    fi
else
    log "bmaptool not found, falling back to decompress | dd"
    DECOMP=$(decompressor_for "$IMAGE")
    echo "  $DECOMP '$IMAGE' | dd of=$DEVICE bs=4M status=progress conv=fsync"
    "$DECOMP" "$IMAGE" | sudo dd of="$DEVICE" bs=4M status=progress conv=fsync
fi

log "Flushing write cache (sync)"
sync

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

log "Done in ${ELAPSED}s -- resulting partitions on $DEVICE:"
lsblk "$DEVICE"

echo
echo "Flash complete. Safe to remove $DEVICE now."
