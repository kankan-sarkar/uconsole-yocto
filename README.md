# uConsole SDR Field Rig — Yocto BSP

A custom Yocto/[kas](https://kas.readthedocs.io/) build turning the ClockworkPi
uConsole (Raspberry Pi CM4) into a battery-powered field SDR/RF rig: GNU
Radio, rtl-sdr/HackRF/SoapySDR, a PIN-secured lock screen and first-boot
wizard, LoRa/MQTT bridging, and dual SD-card/NVMe boot.

- Full design spec: [requirement.md](requirement.md)
- What's built vs. what still needs upstream recipe work:
  [meta-uconsole-sdr/SDR_TOOLS_STATUS.md](meta-uconsole-sdr/SDR_TOOLS_STATUS.md)
- **Read [SECURITY.md](SECURITY.md) before deploying this anywhere that
  matters** — it covers the local PIN/sudo trust model and the dual-use RF
  tooling included here.

## Quick start

Needs a Linux host (native or WSL2) — Ubuntu 22.04+/Debian 12, 8+ cores,
16GB+ RAM, 250GB+ free disk. Full host setup (locales, AppArmor, apt
dependencies) is in
[requirement.md §2](requirement.md#2-recreating-the-build-process-host-environment);
the short version:

```bash
sudo pip3 install kas

# Build takes hours — run it somewhere an SSH drop won't kill it.
tmux
kas build kas-project.yml
```

The finished image lands in `build/tmp/deploy/images/uconsole-cm4/` as a
`.wic.bz2` + `.wic.bmap` pair. Flash with `bmaptool` to either an SD card or
the CM4's NVMe drive — the same image boots from both (see
[requirement.md §4.1](requirement.md#41-storage--boot)).

On an 8GB or smaller build host, edit `kas-project.yml`'s `performance`
block and set `BB_NUMBER_THREADS`/`PARALLEL_MAKE` to `"2"` first, to avoid
OOM kills mid-build.

### Verifying in QEMU before flashing real hardware

`scripts/run-qemu-test.sh` builds and boots a lean `qemux86-64` sanity image
(no SDR/RF toolchain, nothing hardware-specific — see its own header
comment for exactly what it can and can't catch) in minutes instead of a
full flash cycle. On a build host with its own display, it just opens a
normal QEMU window:

```bash
./scripts/run-qemu-test.sh
```

Pass `--web` to view the guest's screen in a browser tab (noVNC, on
port 6080) with nothing to install on the viewing machine — the easiest
way to eyeball the GUI from a laptop while the image runs on the build
host. `--vnc` binds QEMU's VNC server for a native client instead, and
`--nographic` gives serial-only output with no display at all.

The script always exposes a QMP socket, which makes the UI scriptable
without anyone sitting at the screen:

```bash
./scripts/qemu-sendkey.py ctrl-alt-spc      # open the command palette
./scripts/qemu-screenshot.py -o shell.png   # grab the framebuffer
```

That pair is how the shell UI gets checked against `ui-mocks/` after a
change — drive it, capture it, compare — rather than by flashing an SD
card and squinting at the real panel.

## Repo layout

| Path | What |
|---|---|
| `kas-project.yml` | Layer set, machine/distro selection, local.conf fragments |
| `meta-uconsole-sdr/conf/` | Machine config (`uconsole-cm4`), layer.conf |
| `meta-uconsole-sdr/recipes-core/` | Custom apps (OOBE wizard, lock screen, hotkey daemon, control panel, shared theme module), the image recipe, and packagegroups |
| `meta-uconsole-sdr/recipes-support/` | SDR tool recipes with no existing upstream Yocto package (SoapySDR, rtl_433, multimon-ng, direwolf, dump1090) |
| `meta-uconsole-sdr/recipes-connectivity/` | LoRa↔MQTT bridge daemon |
| `meta-uconsole-sdr/recipes-graphics/` | Weston config, and the UI fonts (JetBrains Mono, Material Symbols) the shell names explicitly |
| `ui-mocks/` | Design reference the shell theme is built from — `DESIGN.md` holds the colour/spacing tokens |
| `meta-uconsole-sdr/recipes-kernel/`, `recipes-bsp/` | Kernel config fragments, boot config (`config.txt`) overrides |
| `meta-uconsole-sdr/recipes-{navigation,extended,core}/*.bbappend` | Small, targeted overrides to upstream recipes (gpsd device binding, plymouth DRM support, PAM lockout policy) |

Every custom recipe/script has a one-line `SUMMARY`/`DESCRIPTION` pointing at
what it's for — start with `meta-uconsole-sdr/recipes-core/images/uconsole-image.bb`
for the full list of what actually ships in the image, rather than trying to
read every recipe up front.

## CI

Two GitHub-hosted jobs run on every push/PR: a lint pass and a
`bitbake -n` dependency-resolution pass (no compilation — see
`.github/workflows/`). A third workflow, `build.yml`, runs a real
`kas build` on a self-hosted runner registered against this repo. It
only triggers on pushes to `main`, never on pull requests, so a public
fork can't run code on your hardware.

### Setting up the self-hosted runner on your own build machine

1. **Install the host dependencies** from
   [requirement.md §2](requirement.md#2-recreating-the-build-process-host-environment)
   (locales, the apt package list, `kas`) and do one full manual
   `kas build kas-project.yml` first, so the runner has a warm
   download/sstate cache to reuse rather than starting cold on every
   push (see step 4).

2. **Register a runner**: on GitHub, go to this repo's
   **Settings → Actions → Runners → New self-hosted runner**, pick
   Linux/x64, and follow the download + `./config.sh` commands it
   generates — they include a one-time registration token, so copy
   them from the page rather than reusing the ones below verbatim.
   When `config.sh` asks for labels, add `yocto-build` (required —
   `build.yml` targets `runs-on: [self-hosted, yocto-build]`); a
   runner name matching the machine's hostname makes multi-runner
   setups easier to read later.

   ```bash
   mkdir ~/actions-runner && cd ~/actions-runner
   curl -o actions-runner-linux-x64.tar.gz -L <URL from the GitHub page>
   tar xzf actions-runner-linux-x64.tar.gz
   ./config.sh --url https://github.com/<owner>/<repo> --token <TOKEN> --labels yocto-build
   ```

3. **Install it as a service** so it survives reboots and doesn't need
   a terminal left open:

   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

4. **(Optional) Share the cache with your manual build.** The runner
   does its own `actions/checkout` into a separate directory, so by
   default it builds into *that* checkout's `build/` and won't see the
   downloads/sstate from step 1. Point both at a shared location via
   the runner's own `.env` file — bitbake lists `DL_DIR` and
   `SSTATE_DIR` in `BB_ENV_PASSTHROUGH_ADDITIONS`, so the environment
   is enough and nothing machine-specific needs committing:

   ```bash
   # ~/actions-runner/.env
   DL_DIR=/path/to/your/checkout/build/downloads
   SSTATE_DIR=/path/to/your/checkout/build/sstate-cache
   ```

   The same file is where to set `KAS_VENV=/path/to/venv` if you
   installed `kas` into a virtualenv rather than onto the system
   `PATH` — a fresh tmux shell won't inherit the runner service's
   own `PATH`, so `build.yml` activates it explicitly when that's set.

5. **Live-viewing a build**: `build.yml` launches `kas build` inside a
   detached tmux session named `gh-actions-yocto-build` on the runner
   (rather than as the workflow step's own captured subprocess) —
   `tmux attach -t gh-actions-yocto-build` from that machine shows it
   live with a real tty. Keep ad-hoc manual builds in a *different*
   session: the workflow types into that one, so a manual build
   sitting in it will collide.

### Watching builds and grabbing failure logs

Copying a failure out of a Yocto build is otherwise genuinely annoying
— the build runs in tmux (so mouse selection fights the multiplexer),
the console log is thousands of lines, and the line that matters is
usually in a per-task logfile that the console output merely points at.

`scripts/build-log-server.py` serves the logs as plain text, so
select-all/copy just works:

```bash
./scripts/build-log-server.py --build-dir build --port 8080
# several trees (a manual checkout plus a runner's own _work checkout):
#   --build-dir build --build-dir ~/actions-runner/_work/<repo>/<repo>/build
# it always shows whichever built most recently
```

| Endpoint | What |
|---|---|
| `/errors` | **The one to copy when reporting a failure** — ERROR/WARNING lines plus the full contents of every per-task logfile bitbake referenced |
| `/tail?n=200` | Last n console lines — is it still moving? |
| `/console` | The entire console log |

It's read-only by construction (serves file contents, runs nothing), and
defaults to binding `0.0.0.0` for LAN access — pass `--host 127.0.0.1`
to keep it local. Logs aren't usually sensitive but do contain absolute
paths and package versions, so don't expose it to an untrusted network.

For the **live** pane — bitbake's progress display as it happens —
`scripts/build-terminal.sh` serves the build's tmux session over HTTP
using [ttyd](https://github.com/tsl0922/ttyd):

```bash
./scripts/build-terminal.sh                        # newest active session
./scripts/build-terminal.sh -s gh-actions-yocto-build
```

It's **read-only** unless you pass `--writable`: a stray keystroke into
a live bitbake pane is an easy way to wreck a multi-hour build. It also
pins the tmux window size, because otherwise attaching a browser
resizes the window to the smallest attached client and mangles the
progress display for everyone else watching.

On Debian/Ubuntu, note that the `ttyd` apt package ships its own
`ttyd.service` that auto-starts on port 7681 serving a login prompt —
`sudo systemctl disable --now ttyd.service` before running your own on
that port, or it'll fail to bind. The script checks for this and says
so rather than dying with a bare `EADDRINUSE`.

Both servers are per-machine plumbing, so if you want them running
permanently, their systemd units live on the build host rather than in
this repo.

## Status

This isn't a finished, field-tested product — it's a from-scratch Yocto BSP
built against a fairly ambitious spec, with recipes verified against real
upstream sources (correct tags, dependencies, and license checksums) but
**not yet build-tested end to end** on real hardware (no Yocto/Linux
toolchain was available while writing it). Expect the first `kas build` to
surface things a static read-through can't catch. See
`SDR_TOOLS_STATUS.md` for the list of spec'd tools that have no viable Yocto
recipe anywhere yet (kismet, SDRangel, WSJT-X, and a few others) and why.

## License

MIT — see [LICENSE](LICENSE). This repo contains build *recipes* (metadata
telling bitbake what to fetch and how to build it), not copies of the
software those recipes build; each tool retains its own upstream license
(mostly GPL-2.0, LGPL, and BSD/MIT-family — noted per-recipe).
