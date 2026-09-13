#!/bin/bash
# Boot the QEMU test image, drive the shell UI, and assert that it
# actually rendered -- unattended.
#
# This is the loop the UI work runs on. Change the shell, run this, look
# at two PNGs. It exists because "did it render?" turned out to be a
# question nothing else could answer: the compositor can be active, the
# Wayland socket accepting clients, the app's own logs clean, and the
# screen still blank (see weston.service.d/10-uconsole-vt.conf). Only a
# screenshot distinguishes those, so the screenshot is the test.
#
# Usage:
#   ./scripts/qemu-verify.sh              # boot, capture, assert
#   ./scripts/qemu-verify.sh --build      # rebuild the image first
#   ./scripts/qemu-verify.sh --keep       # leave QEMU running afterwards
#   ./scripts/qemu-verify.sh --out-dir /tmp/shots
#
# Exit status is the point: 0 only if every capture had real content on
# screen. Non-zero means look at the PNGs.

set -uo pipefail

cd "$(dirname "$0")/.."

OUT_DIR="${OUT_DIR:-qemu-shots}"
QMP_SOCK="${QMP_SOCK:-/tmp/uconsole-qemu-qmp.sock}"
BOOT_TIMEOUT="${BOOT_TIMEOUT:-180}"
SETTLE="${SETTLE:-8}"
BUILD=0
KEEP=0

while [ $# -gt 0 ]; do
    case "$1" in
        --build)   BUILD=1; shift ;;
        --keep)    KEEP=1; shift ;;
        --out-dir) OUT_DIR="$2"; shift 2 ;;
        -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

mkdir -p "$OUT_DIR"

# run-qemu-test.sh is a wrapper around `kas shell -c runqemu`, which is
# itself a wrapper around qemu-system -- so the pid we background here
# is several levels above the process actually holding the display.
# Killing just that pid orphans QEMU, and the next run then finds a
# stale QMP socket and a VNC port already bound. Give the whole thing
# its own process group and signal the group.
QEMU_PGID=""
cleanup() {
    if [ -n "$QEMU_PGID" ] && [ "$KEEP" -eq 0 ]; then
        echo "Shutting QEMU down (process group $QEMU_PGID)"
        kill -TERM -- "-$QEMU_PGID" 2>/dev/null || true
        # Give it a moment to release the socket and VNC port, then
        # insist -- a hung qemu would block the next run otherwise.
        for _ in 1 2 3 4 5; do
            kill -0 -- "-$QEMU_PGID" 2>/dev/null || break
            sleep 1
        done
        kill -KILL -- "-$QEMU_PGID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

export QMP_SOCK

# A socket left behind by a previous run would make the wait below
# succeed instantly and every screenshot talk to nothing.
rm -f "$QMP_SOCK"

echo "== booting =="
BOOT_ARGS=(--vnc)
[ "$BUILD" -eq 1 ] && BOOT_ARGS+=(--build)
setsid ./scripts/run-qemu-test.sh "${BOOT_ARGS[@]}" > "$OUT_DIR/boot.log" 2>&1 &
QEMU_PID=$!
# setsid makes the child a session/group leader, so its pid is the pgid.
QEMU_PGID=$QEMU_PID

waited=0
until [ -S "$QMP_SOCK" ]; do
    if ! kill -0 "$QEMU_PID" 2>/dev/null; then
        echo "QEMU exited before it came up. Last of $OUT_DIR/boot.log:" >&2
        tail -20 "$OUT_DIR/boot.log" >&2
        exit 1
    fi
    if [ "$waited" -ge "$BOOT_TIMEOUT" ]; then
        echo "No QMP socket after ${BOOT_TIMEOUT}s -- giving up." >&2
        tail -20 "$OUT_DIR/boot.log" >&2
        exit 1
    fi
    sleep 2
    waited=$((waited + 2))
done
echo "QMP up after ${waited}s"

# The socket appears when QEMU starts, which is long before the guest
# has booted and Weston has anything on screen. Rather than guess a
# number, keep screenshotting until one comes back non-blank.
echo "== waiting for the shell to render =="
rendered=0
waited=0
while [ "$waited" -lt "$BOOT_TIMEOUT" ]; do
    if ./scripts/qemu-screenshot.py --check --socket "$QMP_SOCK" \
         -o "$OUT_DIR/home.png" >/dev/null 2>&1; then
        rendered=1
        break
    fi
    sleep 5
    waited=$((waited + 5))
done

if [ "$rendered" -ne 1 ]; then
    echo "FAIL: nothing ever rendered within ${BOOT_TIMEOUT}s." >&2
    ./scripts/qemu-screenshot.py --check --socket "$QMP_SOCK" -o "$OUT_DIR/home.png" || true
    exit 1
fi
echo "Home screen rendered after ~${waited}s:"
./scripts/qemu-screenshot.py --check --socket "$QMP_SOCK" -o "$OUT_DIR/home.png"

# Give it a moment to finish any entry animation before driving it.
sleep "$SETTLE"

echo "== command palette (Ctrl+Alt+Space) =="
./scripts/qemu-sendkey.py --socket "$QMP_SOCK" ctrl-alt-spc || {
    echo "FAIL: could not send the hotkey" >&2
    exit 1
}
sleep 3

status=0
./scripts/qemu-screenshot.py --check --socket "$QMP_SOCK" -o "$OUT_DIR/palette.png" || status=$?
if [ "$status" -ne 0 ]; then
    echo "FAIL: the palette capture came back blank." >&2
    exit 1
fi

# Leave it closed so a --keep session isn't left in a modal state.
./scripts/qemu-sendkey.py --socket "$QMP_SOCK" esc >/dev/null 2>&1 || true

echo
echo "PASS -- both captures have real content:"
ls -lh "$OUT_DIR"/home.png "$OUT_DIR"/palette.png
[ "$KEEP" -eq 1 ] && echo "QEMU left running (process group $QEMU_PGID)."
exit 0
