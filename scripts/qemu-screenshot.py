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
    ./scripts/qemu-screenshot.py --check         # exit 2 if nothing rendered
    ./scripts/qemu-screenshot.py --socket /tmp/other-qmp.sock

--check turns this into an assertion rather than an artifact: it counts
what's actually in the framebuffer and fails when one flat colour
covers the whole screen. That's the signature of the compositor bug
this project hit -- Weston running, healthy in every log, painting to a
surface nothing scans out -- and it's the only symptom that bug has.

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


def read_ppm(path):
    """Parse QEMU's binary PPM (P6). Returns (width, height, pixels)."""
    with open(path, "rb") as f:
        data = f.read()

    # Header is whitespace-separated tokens, with #-comments allowed
    # anywhere between them: magic, width, height, maxval, then exactly
    # one whitespace byte before the pixel data starts.
    tokens, pos = [], 0
    while len(tokens) < 4:
        while pos < len(data) and data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":
            while pos < len(data) and data[pos:pos + 1] != b"\n":
                pos += 1
            continue
        start = pos
        while pos < len(data) and not data[pos:pos + 1].isspace():
            pos += 1
        tokens.append(data[start:pos])
    pos += 1  # the single whitespace byte after maxval

    if tokens[0] != b"P6":
        raise ValueError(f"not a binary PPM (magic {tokens[0]!r})")
    width, height, maxval = (int(t) for t in tokens[1:4])
    if maxval != 255:
        raise ValueError(f"unsupported maxval {maxval}")
    return width, height, data[pos:pos + width * height * 3]


def analyse(path, sample_step=7):
    """How much is actually on this screen?

    The failure this exists to catch is a compositor that is running,
    reports itself healthy, and paints nothing anyone can see -- which
    looks identical to success in every log. A framebuffer that is one
    flat colour is the signature.

    Sampling every Nth pixel rather than all of them: at 1920x1080
    that's the difference between instant and not, and a blank screen
    is blank at any sampling rate.
    """
    from collections import Counter

    width, height, pixels = read_ppm(path)
    counts = Counter()
    for i in range(0, len(pixels) - 2, 3 * sample_step):
        counts[pixels[i:i + 3]] += 1
    total = sum(counts.values()) or 1
    dominant, dominant_n = counts.most_common(1)[0]
    return {
        "width": width,
        "height": height,
        "colours": len(counts),
        "dominant": "#%02x%02x%02x" % tuple(dominant),
        "dominant_share": dominant_n / total,
    }


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
    ap.add_argument("--check", action="store_true",
                    help="report what's on screen, and fail if it looks blank")
    ap.add_argument("--blank-threshold", type=float, default=0.99,
                    metavar="F",
                    help="with --check, treat the screen as blank when one "
                         "colour covers at least this share (default: 0.99)")
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

    blank = False
    if args.check:
        try:
            st = analyse(tmp_ppm)
        except (ValueError, OSError) as e:
            print(f"could not analyse the framebuffer: {e}", file=sys.stderr)
            return 1
        blank = st["dominant_share"] >= args.blank_threshold
        print(f"{st['width']}x{st['height']}, {st['colours']} distinct colours, "
              f"{st['dominant_share']:.1%} of it {st['dominant']}")
        if blank:
            print("SCREEN LOOKS BLANK -- one flat colour. If a compositor is "
                  "running and reporting healthy, suspect it isn't on the "
                  "active VT (see weston.service.d/10-uconsole-vt.conf).",
                  file=sys.stderr)

    if args.ppm:
        print(f"wrote {tmp_ppm} ({os.path.getsize(tmp_ppm)} bytes)")
        return 2 if blank else 0

    if not shutil.which("pnmtopng"):
        fallback = os.path.splitext(args.output)[0] + ".ppm"
        shutil.move(tmp_ppm, fallback)
        print(f"pnmtopng not found (apt-get install netpbm); kept raw PPM: {fallback}")
        return 2 if blank else 0

    with open(args.output, "wb") as png:
        subprocess.run(["pnmtopng", tmp_ppm], stdout=png, check=True)
    os.unlink(tmp_ppm)
    print(f"wrote {args.output} ({os.path.getsize(args.output)} bytes)")
    return 2 if blank else 0


if __name__ == "__main__":
    sys.exit(main())
