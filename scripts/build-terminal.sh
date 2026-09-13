#!/bin/bash
# Serve a build's tmux session as a terminal in the browser, via ttyd.
#
# Companion to scripts/build-log-server.py: that one gives you the
# finished logs and a copy-ready failure report, this one gives you the
# live pane -- bitbake's progress display, as it happens, from any
# machine on the LAN.
#
# Usage:
#   ./scripts/build-terminal.sh                       # newest active session, read-only
#   ./scripts/build-terminal.sh -s gh-actions-yocto-build
#   ./scripts/build-terminal.sh --writable            # allow typing (see below)
#   ./scripts/build-terminal.sh -p 7682               # different port
#
# Read-only by default, deliberately: a stray keystroke into a live
# bitbake pane is an easy way to wreck a multi-hour build, and a
# browser tab left open on a phone in a pocket is exactly how that
# happens. --writable is there when you actually need to drive the
# session, and it prints a warning so it can't be forgotten quietly.
#
# Picking the session with `tmux list-sessions -F '#{session_activity}'`
# needs those single quotes: unquoted, bash treats the `#` as the start
# of a comment, eats the rest of the line, and leaves the command
# substitution unterminated. That failure is silent in the sense that
# ttyd still starts and still serves a page -- it's the shell *inside*
# that dies, so the browser shows a syntax error instead of the build.

set -euo pipefail

PORT="${PORT:-7681}"
SESSION=""
WRITABLE=0

while [ $# -gt 0 ]; do
    case "$1" in
        -s|--session) SESSION="$2"; shift 2 ;;
        -p|--port)    PORT="$2"; shift 2 ;;
        --writable)   WRITABLE=1; shift ;;
        -h|--help)    sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

command -v tmux >/dev/null || { echo "tmux is not installed" >&2; exit 1; }
command -v ttyd >/dev/null || { echo "ttyd is not installed" >&2; exit 1; }

if ! tmux list-sessions >/dev/null 2>&1; then
    echo "No tmux sessions are running -- start a build first." >&2
    exit 1
fi

if [ -z "$SESSION" ]; then
    # Most recently active session, newest first.
    SESSION="$(tmux list-sessions -F '#{session_activity} #{session_name}' \
               | sort -rn | head -1 | cut -d' ' -f2-)"
    echo "Using most recently active session: $SESSION"
elif ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "No such tmux session: $SESSION" >&2
    echo "Running sessions:" >&2
    tmux list-sessions -F '  #{session_name}' >&2
    exit 1
fi

# Attaching a browser resizes the tmux window to the smallest attached
# client, which mangles bitbake's progress display for everyone already
# watching. Pinning it costs nothing and is tmux 3.1+; older tmux just
# errors here, which is fine to ignore.
tmux set-option -t "$SESSION" window-size manual 2>/dev/null || true

if ss -ltn 2>/dev/null | grep -q ":${PORT}\b"; then
    echo "Port $PORT is already in use." >&2
    echo "On Debian/Ubuntu the ttyd apt package ships its own ttyd.service" >&2
    echo "on this port: sudo systemctl disable --now ttyd.service" >&2
    exit 1
fi

TTYD_ARGS=(-p "$PORT")
if [ "$WRITABLE" -eq 1 ]; then
    echo "WARNING: writable mode -- keystrokes go straight into the build pane."
else
    TTYD_ARGS+=(-R)
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "Serving session '$SESSION' at http://${IP:-localhost}:${PORT}/"
echo "Ctrl-C to stop serving (the build keeps running)."

exec ttyd "${TTYD_ARGS[@]}" tmux attach -t "$SESSION"
