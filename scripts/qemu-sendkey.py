#!/usr/bin/env python3
"""Send key presses into the running QEMU guest, via QMP.

Pairs with qemu-screenshot.py: that one shows what the UI looks like,
this one drives it, so a UI change can be exercised end to end without
anyone sitting at the screen -- press Ctrl+Alt+Space, screenshot the
command palette, compare against the mockup.

Keys are QEMU qcode names (a full list lives in QEMU's qapi ui.json);
the common ones here are letters a-z, digits 0-9, and ctrl/alt/shift,
spc, ret, esc, tab, up, down, left, right.

    ./scripts/qemu-sendkey.py ctrl-alt-spc     # one combo
    ./scripts/qemu-sendkey.py t e r m          # a sequence of presses
    ./scripts/qemu-sendkey.py ret
"""
import argparse
import json
import os
import socket
import sys

DEFAULT_SOCK = "/tmp/uconsole-qemu-qmp.sock"


class QmpError(RuntimeError):
    pass


class Qmp:
    def __init__(self, sock_path, timeout=10):
        if not os.path.exists(sock_path):
            raise QmpError(
                f"No QMP socket at {sock_path}. Is QEMU running, and was it "
                "started by run-qemu-test.sh (which sets the socket up)?")
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect(sock_path)
        self._conn = self._sock.makefile("rwb")
        self._conn.readline()  # greeting
        self._send({"execute": "qmp_capabilities"})

    def _send(self, obj):
        self._conn.write((json.dumps(obj) + "\n").encode())
        self._conn.flush()
        while True:
            line = self._conn.readline()
            if not line:
                raise QmpError("QMP connection closed unexpectedly")
            msg = json.loads(line)
            if "event" in msg:      # async events interleave with replies
                continue
            if "error" in msg:
                raise QmpError(f"QMP error: {msg['error']}")
            return msg

    def send_keys(self, combo):
        """combo is like 'ctrl-alt-spc' -- all pressed together."""
        keys = [{"type": "qcode", "data": k} for k in combo.split("-")]
        self._send({"execute": "send-key", "arguments": {"keys": keys}})

    def close(self):
        self._conn.close()
        self._sock.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("combos", nargs="+", metavar="COMBO",
                    help="key combos, e.g. ctrl-alt-spc, or single keys")
    ap.add_argument("--socket", default=DEFAULT_SOCK,
                    help=f"QMP socket path (default: {DEFAULT_SOCK})")
    ap.add_argument("--delay", type=float, default=0.15,
                    help="seconds between presses (default: 0.15)")
    args = ap.parse_args()

    try:
        qmp = Qmp(args.socket)
    except (QmpError, OSError) as e:
        print(f"sendkey failed: {e}", file=sys.stderr)
        return 1

    import time
    try:
        for combo in args.combos:
            qmp.send_keys(combo)
            print(f"sent {combo}")
            time.sleep(args.delay)
    except QmpError as e:
        print(f"sendkey failed: {e}", file=sys.stderr)
        return 1
    finally:
        qmp.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
