#!/usr/bin/env python3
"""Grab the running QEMU guest's framebuffer as a PNG, via QMP.

Checking that a service is "active (running)" says nothing about
whether anything actually rendered -- a Qt app can sit there happily
with a blank or half-drawn window. This captures what's genuinely on
the guest's screen, so UI changes can be checked without a VNC client
attached, and from a script.

scripts/run-qemu-test.sh always exposes the QMP socket this talks to.

    ./scripts/qemu-screenshot.py                 # -> qemu-screenshot.png
    ./scripts/qemu-screenshot.py -o before.png
    ./scripts/qemu-screenshot.py --socket /tmp/other-qmp.sock

QEMU's screendump writes PPM; this converts to PNG with pnmtopng
(netpbm) when available, since PPM is awkward to view. Pass --ppm to
keep the raw file instead.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile

DEFAULT_SOCK = "/tmp/uconsole-qemu-qmp.sock"


class QmpError(RuntimeError):
    pass


def qmp_screendump(sock_path, out_ppm, timeout=20):
    """Connect to QMP, negotiate, and dump the framebuffer to out_ppm."""
    if not os.path.exists(sock_path):
        raise QmpError(
            f"No QMP socket at {sock_path}.\n"
            "Is QEMU running, and was it started by run-qemu-test.sh "
            "(which sets up the socket)?"
        )

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(sock_path)
    conn = s.makefile("rwb")

    def send(obj):
        conn.write((json.dumps(obj) + "\n").encode())
        conn.flush()
        # QMP interleaves asynchronous events with command replies;
        # skip events until the actual return/error shows up.
        while True:
            line = conn.readline()
            if not line:
                raise QmpError("QMP connection closed unexpectedly")
            msg = json.loads(line)
            if "event" in msg:
                continue
            if "error" in msg:
                raise QmpError(f"QMP error: {msg['error']}")
            return msg

    try:
        conn.readline()          # server greeting
        send({"execute": "qmp_capabilities"})
        send({"execute": "screendump", "arguments": {"filename": out_ppm}})
    finally:
        conn.close()
        s.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="qemu-screenshot.png",
                    help="output file (default: qemu-screenshot.png)")
    ap.add_argument("--socket", default=DEFAULT_SOCK,
                    help=f"QMP socket path (default: {DEFAULT_SOCK})")
    ap.add_argument("--ppm", action="store_true",
                    help="keep QEMU's raw PPM instead of converting to PNG")
    args = ap.parse_args()

    # QEMU writes the dump itself, so it needs an absolute path it can
    # resolve -- its cwd is not this script's.
    tmp_ppm = os.path.abspath(
        args.output if args.ppm else
        os.path.join(tempfile.gettempdir(), "uconsole-screendump.ppm"))

    try:
        qmp_screendump(args.socket, tmp_ppm)
    except (QmpError, OSError) as e:
        print(f"screenshot failed: {e}", file=sys.stderr)
        return 1

    if not os.path.exists(tmp_ppm):
        print(f"QEMU reported success but {tmp_ppm} is missing "
              "(is QEMU running as a different user?)", file=sys.stderr)
        return 1

    if args.ppm:
        print(f"wrote {tmp_ppm} ({os.path.getsize(tmp_ppm)} bytes)")
        return 0

    if not shutil.which("pnmtopng"):
        fallback = os.path.splitext(args.output)[0] + ".ppm"
        shutil.move(tmp_ppm, fallback)
        print(f"pnmtopng not found (apt-get install netpbm); kept raw PPM: {fallback}")
        return 0

    with open(args.output, "wb") as png:
        subprocess.run(["pnmtopng", tmp_ppm], stdout=png, check=True)
    os.unlink(tmp_ppm)
    print(f"wrote {args.output} ({os.path.getsize(args.output)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
