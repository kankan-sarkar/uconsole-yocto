#!/usr/bin/env python3
"""Read-only web view of the most recent bitbake build logs.

Exists because copying a failure out of a long build is otherwise
genuinely annoying: the build runs in tmux (so mouse selection fights
the multiplexer), bitbake's console log is thousands of lines, and the
line that actually matters is usually not in the console log at all --
it's in a per-task logfile that the console output merely points at.

Endpoints (all plain text, so a browser renders them selectable and
Ctrl-A/Ctrl-C works):

    /            index with what's available and how stale it is
    /errors      the failure summary -- ERROR/WARNING lines from the
                 console log, followed by the full contents of every
                 per-task logfile bitbake referenced. This is the one
                 to copy when asking someone what broke.
    /console     the whole console log
    /tail?n=200  last n lines of the console log

Read-only by construction: it serves file contents and runs nothing.
Point it at a build directory and leave it running:

    ./scripts/build-log-server.py --build-dir build --port 8080

Binds 0.0.0.0 by default so it's reachable from another machine on the
LAN; pass --host 127.0.0.1 to keep it local. Build logs aren't usually
sensitive, but they do contain absolute paths and package versions, so
don't expose this to an untrusted network.
"""
import argparse
import glob
import html
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# bitbake writes this per MACHINE; console-latest.log is a symlink to
# the current build's console log, so it follows successive builds
# without needing to know the timestamped name.
COOKER_GLOB = "tmp/log/cooker/*/console-latest.log"

# bitbake emits this verbatim when a task fails, and the path it names
# is where the actual compiler/configure error lives.
FAILURE_LOG_RE = re.compile(r"Logfile of failure stored in:\s*(\S+)")

MAX_TASK_LOG_BYTES = 256 * 1024


def find_console_log(build_dirs):
    """Newest console-latest.log across all build_dirs, or None.

    Takes several directories because a machine typically has more than
    one build tree -- a manual checkout and a CI runner's own _work
    checkout, say -- and what you almost always want is "whatever built
    most recently", not to pick one by hand.
    """
    matches = []
    for build_dir in build_dirs:
        matches.extend(glob.glob(os.path.join(build_dir, COOKER_GLOB)))
    if not matches:
        return None
    return max(matches, key=lambda p: os.path.getmtime(p))


def read_text(path, limit=None):
    try:
        with open(path, "rb") as f:
            if limit is not None:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - limit))
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except OSError as e:
        return f"<could not read {path}: {e}>\n"


def describe_age(path):
    try:
        delta = time.time() - os.path.getmtime(path)
    except OSError:
        return "unknown"
    if delta < 90:
        return f"{int(delta)}s ago (looks live)"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    return f"{delta / 3600:.1f}h ago"


def build_error_report(console_path):
    """ERROR/WARNING lines plus every per-task logfile they point at."""
    text = read_text(console_path)
    lines = text.splitlines()

    interesting = [ln for ln in lines if ln.startswith(("ERROR:", "WARNING:"))]
    task_logs = []
    for ln in lines:
        m = FAILURE_LOG_RE.search(ln)
        if m and m.group(1) not in task_logs:
            task_logs.append(m.group(1))

    out = [f"# failure report from {console_path}",
           f"# log last modified: {describe_age(console_path)}",
           ""]

    if not interesting:
        out.append("No ERROR or WARNING lines in the console log.")
        out.append("If the build is still running, that's simply how far it's got.")
    else:
        out.append(f"=== {len(interesting)} ERROR/WARNING line(s) ===")
        out.append("")
        out.extend(interesting)

    if task_logs:
        out.append("")
        out.append(f"=== {len(task_logs)} referenced task log(s) ===")
        for p in task_logs:
            out.append("")
            out.append(f"--- {p} ---")
            if os.path.exists(p):
                out.append(read_text(p, limit=MAX_TASK_LOG_BYTES))
            else:
                out.append(f"<no longer on disk: {p}>")
                out.append("(bitbake removes these when a task is re-run successfully)")

    # The tail is what tells you whether the build is mid-task or has
    # stopped, which the ERROR lines alone don't.
    out.append("")
    out.append("=== last 40 console lines ===")
    out.append("")
    out.extend(lines[-40:])
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    build_dirs = ["build"]

    def _send(self, body, content_type="text/plain; charset=utf-8", status=200):
        payload = body.encode("utf-8", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        # Always revalidate: the whole point is seeing the current state.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        console = find_console_log(self.build_dirs)

        if route == "/":
            return self._send(self._index(console), "text/html; charset=utf-8")

        if console is None:
            searched = "\n".join(f"  {d}/{COOKER_GLOB}" for d in self.build_dirs)
            return self._send(
                "No bitbake console log found. Searched:\n" + searched + "\n"
                "Either no build has started yet, or --build-dir points elsewhere.\n",
                status=404,
            )

        if route == "/errors":
            return self._send(build_error_report(console))
        if route == "/console":
            return self._send(read_text(console))
        if route == "/tail":
            n = 200
            try:
                n = max(1, min(20000, int(parse_qs(parsed.query).get("n", ["200"])[0])))
            except ValueError:
                pass
            return self._send("\n".join(read_text(console).splitlines()[-n:]) + "\n")

        return self._send(f"Unknown path {route}\nTry / for the index.\n", status=404)

    def _index(self, console):
        watched = "".join(f"<li><code>{html.escape(d)}</code></li>" for d in self.build_dirs)
        if console is None:
            status = ("<p><strong>No console log found.</strong> Watching:</p>"
                      f"<ul>{watched}</ul>"
                      "<p>No build has started yet, or the build directories are elsewhere.</p>")
        else:
            status = (f"<p>Showing the most recently modified build log:<br>"
                      f"<code>{html.escape(console)}</code><br>"
                      f"Last modified: <strong>{html.escape(describe_age(console))}</strong></p>"
                      f"<details><summary>watching {len(self.build_dirs)} build dir(s)</summary>"
                      f"<ul>{watched}</ul></details>")
        return f"""<!doctype html>
<title>uConsole build logs</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 48rem; margin: 2rem auto; padding: 0 1rem; }}
 code {{ background: #f4f4f4; padding: .1rem .3rem; }}
 li {{ margin: .6rem 0; }}
</style>
<h1>uConsole build logs</h1>
{status}
<ul>
  <li><a href="/errors"><strong>/errors</strong></a> — failure summary: ERROR/WARNING
      lines plus the full contents of any per-task logfile bitbake pointed at.
      <em>Copy this one when reporting a build failure.</em></li>
  <li><a href="/tail?n=200">/tail?n=200</a> — last n console lines (is it still moving?)</li>
  <li><a href="/console">/console</a> — the entire console log</li>
</ul>
<p>All endpoints are plain text, so select-all / copy works directly —
no tmux selection to fight.</p>
"""

    def log_message(self, fmt, *args):
        pass  # don't spam the journal with one line per poll


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-dir", action="append", metavar="DIR",
                    help="bitbake build directory to watch; repeat for several "
                         "(e.g. a manual checkout and a CI runner's). "
                         "Default: build")
    ap.add_argument("--port", type=int, default=8080, help="port to listen on (default: 8080)")
    ap.add_argument("--host", default="0.0.0.0",
                    help="address to bind (default: 0.0.0.0; use 127.0.0.1 to keep it local)")
    args = ap.parse_args()

    Handler.build_dirs = [os.path.abspath(d) for d in (args.build_dir or ["build"])]
    print(f"watching {len(Handler.build_dirs)} build dir(s) on http://{args.host}:{args.port}/")
    for d in Handler.build_dirs:
        print(f"  {d}")
    HTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
