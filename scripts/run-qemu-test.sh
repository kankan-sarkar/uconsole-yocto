#!/bin/bash
# Build (if needed) and boot uconsole-image-qemu-test under QEMU, for
# fast pre-flash sanity checks -- see kas-qemu.yml and
# meta-uconsole-sdr/recipes-core/images/uconsole-image-qemu-test.bb
# for what this can and can't actually validate. Run from the repo
# root (where kas-qemu.yml lives).
#
# Usage:
#   ./scripts/run-qemu-test.sh            # build (only if needed) + boot
#   ./scripts/run-qemu-test.sh --build    # force a rebuild first
#   ./scripts/run-qemu-test.sh --no-vnc   # serial/terminal only, no display
#
# Display: defaults to QEMU's VNC server bound to all interfaces
# (runqemu's "publicvnc" keyword) since hs01 is a headless box reached
# over SSH -- point any VNC client at hs01:5901 (display :1) to see
# the actual Weston/OOBE framebuffer. Boot/kernel/systemd messages
# still print directly to this terminal either way.

set -euo pipefail

cd "$(dirname "$0")/.."

BUILD_DIR="build-qemu-test"
FORCE_BUILD=0
DISPLAY_ARGS="publicvnc"

for arg in "$@"; do
    case "$arg" in
        --build) FORCE_BUILD=1 ;;
        --no-vnc) DISPLAY_ARGS="nographic" ;;
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

echo "==> Booting under QEMU (kvm, $DISPLAY_ARGS, slirp networking)"
echo "    VNC clients: connect to hs01:5901 if using the default display mode."
kas shell kas-qemu.yml -c "runqemu qemux86-64 kvm slirp $DISPLAY_ARGS"
