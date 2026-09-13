#!/bin/bash
# Build (if needed) and boot uconsole-image-qemu-test under QEMU, for
# fast pre-flash sanity checks -- see kas-qemu.yml and
# meta-uconsole-sdr/recipes-core/images/uconsole-image-qemu-test.bb
# for what this can and can't actually validate. Run from the repo
# root (where kas-qemu.yml lives).
#
# Usage:
#   ./scripts/run-qemu-test.sh              # build (only if needed) + boot in a local window
#   ./scripts/run-qemu-test.sh --build      # force a rebuild first
#   ./scripts/run-qemu-test.sh --web        # view the GUI in a browser (noVNC)
#   ./scripts/run-qemu-test.sh --vnc        # bind QEMU's VNC server, for a native VNC client
#   ./scripts/run-qemu-test.sh --nographic  # serial/terminal only, no display at all
#
# Display: defaults to a plain local QEMU window (runqemu's normal
# behavior when no display keyword is given), which is what you want on
# a build host with its own screen. --vnc instead binds QEMU's VNC
# server on all interfaces for a native VNC client on another machine.
# --web adds noVNC on top of that, so the guest's framebuffer shows up
# in a browser tab with nothing to install on the viewing machine --
# the easiest way to eyeball the uConsole GUI from a laptop while the
# image runs on the build host. Boot/kernel/systemd messages print
# directly to this terminal regardless of display mode.
#
# A QMP socket is always exposed (see QMP_SOCK below) so
# scripts/qemu-screenshot.py can grab the framebuffer as a PNG without
# a VNC client attached at all -- useful for scripted UI checks.

set -euo pipefail

cd "$(dirname "$0")/.."

BUILD_DIR="build-qemu-test"
FORCE_BUILD=0
DISPLAY_ARGS=""
WEB=0
VNC_PORT="${VNC_PORT:-5900}"
WEB_PORT="${WEB_PORT:-6080}"
NOVNC_ROOT="${NOVNC_ROOT:-/usr/share/novnc}"
QMP_SOCK="${QMP_SOCK:-/tmp/uconsole-qemu-qmp.sock}"

for arg in "$@"; do
    case "$arg" in
        --build) FORCE_BUILD=1 ;;
        --web) DISPLAY_ARGS="publicvnc"; WEB=1 ;;
        --vnc) DISPLAY_ARGS="publicvnc" ;;
        --nographic|--no-vnc) DISPLAY_ARGS="nographic" ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

export KAS_BUILD_DIR="$BUILD_DIR"

DEPLOY_DIR="$BUILD_DIR/tmp/deploy/images/qemux86-64"
IMAGE_LINK="$DEPLOY_DIR/uconsole-image-qemu-test-qemux86-64.qemuboot.conf"

if [ "$FORCE_BUILD" = "1" ] || [ ! -f "$IMAGE_LINK" ]; then
    echo "==> Building uconsole-image-qemu-test (build dir: $BUILD_DIR)"
    kas build kas-qemu.yml
else
    echo "==> Found existing build output, skipping build (use --build to force a rebuild)"
fi

WEBSOCKIFY_PID=""
cleanup() {
    if [ -n "$WEBSOCKIFY_PID" ]; then
        kill "$WEBSOCKIFY_PID" 2>/dev/null || true
    fi
    rm -f "$QMP_SOCK"
}
trap cleanup EXIT

if [ "$WEB" = "1" ]; then
    if [ ! -d "$NOVNC_ROOT" ]; then
        echo "noVNC not found at $NOVNC_ROOT (try: sudo apt-get install novnc websockify)" >&2
        echo "Set NOVNC_ROOT if it lives elsewhere." >&2
        exit 1
    fi
    command -v websockify >/dev/null 2>&1 || {
        echo "websockify not found (try: sudo apt-get install websockify)" >&2; exit 1; }

    # Bridges QEMU's plain VNC port to a WebSocket and serves noVNC's
    # own HTML/JS next to it, so a browser needs nothing installed.
    websockify --web="$NOVNC_ROOT" "$WEB_PORT" "localhost:$VNC_PORT" >/tmp/uconsole-websockify.log 2>&1 &
    WEBSOCKIFY_PID=$!
    sleep 1
    echo "==> Browser view: http://$(hostname -I | awk '{print $1}'):$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
    echo "    (noVNC -> localhost:$VNC_PORT; websockify log: /tmp/uconsole-websockify.log)"
fi

echo "==> Booting under QEMU (kvm, ${DISPLAY_ARGS:-local window}, slirp networking)"
if [ "$DISPLAY_ARGS" = "publicvnc" ] && [ "$WEB" != "1" ]; then
    echo "    VNC server is bound on all interfaces -- point a client at this host, port $VNC_PORT."
fi

# qemux86-64's own default qemuboot.conf allocates only 256MB. Real
# hardware has 4GB (requirement.md), and this image can now run two
# PyQt6/Wayland clients at once (uconsole-shell plus whatever's
# launched from it) -- bumped for headroom so a slow/thrashing test
# run doesn't get mistaken for a real hang, the way it briefly did
# while testing uconsole-shell for the first time.
#
# The QMP socket is what scripts/qemu-screenshot.py talks to; it costs
# nothing when unused and saves relaunching QEMU just to grab a frame.
#
# "serial" puts the kernel console and a getty on ttyS0, i.e. into this
# terminal. That's worth having in every mode, not just headless ones:
# without it the console owns the graphical display, so the VNC/local
# window shows a text login prompt and Weston's output is never what
# you see. With it, text goes here and the framebuffer is left to the
# compositor -- which is also what makes scripted checks possible,
# since the console becomes drivable from tmux.
rm -f "$QMP_SOCK"
kas shell kas-qemu.yml -c "runqemu qemux86-64 kvm slirp serial $DISPLAY_ARGS qemuparams=\"-m 512 -qmp unix:$QMP_SOCK,server,nowait\""
