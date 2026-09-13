#!/bin/bash
# Full kas build for CI, with the fetch phase retried.
#
# Split out of .github/workflows/build.yml because that step drives the
# build through `tmux send-keys`, and anything non-trivial written as a
# send-keys string has to survive two rounds of shell quoting. A file
# can be syntax-checked; an escaped one-liner can only be guessed at.
#
# The retry exists because the upstream Yocto git servers genuinely are
# flaky -- git.yoctoproject.org in particular fails TLS handshakes
# ("gnutls_handshake() failed: Error in the pull function") often
# enough to kill a build before a single task runs. Retrying the whole
# build would be wrong: a real compile failure would then burn hours
# repeating itself. So only `kas checkout`, which is network-only and
# cheap, is retried; `kas build` runs exactly once and its exit code is
# the job's.
#
# Usage:  ./scripts/ci-build.sh [kas-config.yml]
#
# KAS_VENV is honoured if set (kas installed into a virtualenv rather
# than on the system PATH). It has to be passed in explicitly by the
# caller -- a fresh tmux shell doesn't inherit the runner service's
# environment.

set -uo pipefail

cd "$(dirname "$0")/.."

CONFIG="${1:-kas-project.yml}"
RETRIES="${CHECKOUT_RETRIES:-3}"
RETRY_DELAY="${CHECKOUT_RETRY_DELAY:-30}"

if [ -n "${KAS_VENV:-}" ]; then
    # shellcheck disable=SC1091
    source "${KAS_VENV}/bin/activate"
fi

command -v kas >/dev/null || {
    echo "kas is not on PATH (set KAS_VENV if it's in a virtualenv)" >&2
    exit 127
}

attempt=1
until kas checkout "$CONFIG"; do
    if [ "$attempt" -ge "$RETRIES" ]; then
        echo "kas checkout failed $attempt times -- giving up." >&2
        echo "If this is the usual git.yoctoproject.org flakiness, just re-run the job." >&2
        exit 1
    fi
    echo "kas checkout failed (attempt $attempt/$RETRIES) -- retrying in ${RETRY_DELAY}s"
    attempt=$((attempt + 1))
    sleep "$RETRY_DELAY"
done

exec kas build "$CONFIG"
