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

## Repo layout

| Path | What |
|---|---|
| `kas-project.yml` | Layer set, machine/distro selection, local.conf fragments |
| `meta-uconsole-sdr/conf/` | Machine config (`uconsole-cm4`), layer.conf |
| `meta-uconsole-sdr/recipes-core/` | Custom apps (OOBE wizard, lock screen, hotkey daemon, control panel, shared theme module), the image recipe, and packagegroups |
| `meta-uconsole-sdr/recipes-support/` | SDR tool recipes with no existing upstream Yocto package (SoapySDR, rtl_433, multimon-ng, direwolf, dump1090) |
| `meta-uconsole-sdr/recipes-connectivity/` | LoRa↔MQTT bridge daemon |
| `meta-uconsole-sdr/recipes-kernel/`, `recipes-bsp/` | Kernel config fragments, boot config (`config.txt`) overrides |
| `meta-uconsole-sdr/recipes-{navigation,extended,core}/*.bbappend` | Small, targeted overrides to upstream recipes (gpsd device binding, plymouth DRM support, PAM lockout policy) |

Every custom recipe/script has a one-line `SUMMARY`/`DESCRIPTION` pointing at
what it's for — start with `meta-uconsole-sdr/recipes-core/images/uconsole-image.bb`
for the full list of what actually ships in the image, rather than trying to
read every recipe up front.

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
