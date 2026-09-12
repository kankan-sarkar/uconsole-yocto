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
#   ./scripts/run-qemu-test.sh --vnc        # bind QEMU's VNC server instead, for viewing remotely
#   ./scripts/run-qemu-test.sh --nographic  # serial/terminal only, no display at all
#
# Display: defaults to a plain local QEMU window (runqemu's normal
# behavior when no display keyword is given), which is what you want on
# a build host with its own screen. --vnc instead binds QEMU's VNC
# server on all interfaces (display :1, port 5901) for viewing from
# another machine -- the mode to use on a headless box reachable only
# over SSH. Boot/kernel/systemd messages print directly to this
# terminal regardless of display mode.

set -euo pipefail

cd "$(dirname "$0")/.."

BUILD_DIR="build-qemu-test"
FORCE_BUILD=0
DISPLAY_ARGS=""

for arg in "$@"; do
    case "$arg" in
        --build) FORCE_BUILD=1 ;;
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

echo "==> Booting under QEMU (kvm, ${DISPLAY_ARGS:-local window}, slirp networking)"
if [ "$DISPLAY_ARGS" = "publicvnc" ]; then
    echo "    VNC server is bound on all interfaces -- point a client at this host, display :1 (port 5901)."
fi
# qemux86-64's own default qemuboot.conf allocates only 256MB. Real
# hardware has 4GB (requirement.md), and this image can now run two
# PyQt6/Wayland clients at once (uconsole-shell plus whatever's
# launched from it) -- bumped for headroom so a slow/thrashing test
# run doesn't get mistaken for a real hang, the way it briefly did
# while testing uconsole-shell for the first time.
kas shell kas-qemu.yml -c "runqemu qemux86-64 kvm slirp $DISPLAY_ARGS qemuparams=\"-m 512\""
