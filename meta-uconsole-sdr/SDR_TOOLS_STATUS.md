# SDR/tool coverage status vs. requirement.md 5.1

This tracks which tools named in requirement.md actually made it into
`packagegroup-uconsole-sdr` / `packagegroup-uconsole-security`, and
which didn't -- with the reason, so "not done" doesn't get silently
lost. Checked against the OpenEmbedded Layer Index (kirkstone branch)
and each project's own upstream build files as of 2026-08.

## Packaged (recipe exists upstream or was added in this layer)

| Tool | Source |
|---|---|
| gnuradio (GUI plotting blocks off -- see below), rtl-sdr, libhackrf, gr-osmosdr | meta-sdr |
| aircrack-ng | meta-security |
| wireshark, NetworkManager, mosquitto(+clients) | meta-openembedded |
| gpsd (+gps-utils, bound to /dev/ttyS0) | meta-openembedded |
| cpufrequtils, htop, iotop, sysstat | meta-openembedded |
| pipewire, wireplumber | meta-openembedded (meta-multimedia) |
| netdata, nginx | meta-openembedded (meta-webserver) |
| soapysdr, soapysdr-module-rtlsdr, soapysdr-module-hackrf | new recipes in this layer, git-pinned to tagged releases |
| rtl_433, multimon-ng, direwolf, dump1090 | new recipes in this layer, git-pinned to tagged releases |
| gqrx | new recipe in this layer, pinned to upstream `v2.17.7`, built against Qt6 |

The "new recipes" rows above are hand-written for this project. Their
upstream repos, tags, and license files were verified against the
actual GitHub repos; direwolf, dump1090, and gqrx have since been
confirmed building successfully against real CI, the rest have not yet
had a clean build reach them -- treat the first `bitbake` run against
each as the real test, not this list.

## Previously removed, now restored

* **gqrx** -- meta-sdr's bundled recipe (`gqrx_git.bb`, pinned to the
  old 2.15.9 release) was Qt5-only (`inherit cmake_qt5`), which
  conflicted with this project's own Qt6 PyQt6 desktop apps (a single
  bitbake build can't resolve two providers for the recipe name
  `qtbase`). It was dropped entirely for that reason -- see git history
  (`6fa2bd7`, `bccd071`) for the original removal.

  Restored via a new local recipe (`gqrx_2.17.7.bb`) pinned to
  upstream's current release, which added a `FORCE_QT6` CMake option
  (confirmed against the real `CMakeLists.txt` at that tag) that builds
  against Qt6's `qtbase`/`qtsvg` directly -- no Qt5 layer needed.
  meta-sdr's own `gqrx_git.bb` stays `BBMASK`'d out (see
  `gqrx_bbmask` in `kas-project.yml`) so only this recipe is used.

## Not packaged -- no viable Yocto recipe found anywhere

These aren't in any layer this project pulls in, and weren't added
here either, because each would need an original recipe written
against a build system with a deep, partly-unpackaged dependency
chain -- real work that needs a live build machine to iterate against,
not something to hand-wave into existence from static inspection:

* **kismet** -- meson, protobuf-c codegen, ~15 libraries (libnl,
  libcap, sqlite3, protobuf, ...).
* **wayvnc** -- itself buildable, but depends on `neatvnc` and `aml`,
  neither of which are packaged either. Three unpackaged recipes deep.
* **inspectrum / sigDigger** -- both need `liquid-dsp`, which isn't
  packaged anywhere either.
* **urh** (Universal Radio Hacker) -- Python + Cython extension build
  with its own bundled native DSP code.
* **SDRangel, CubicSDR, SDR++** -- large Qt/CMake (or wxWidgets, for
  CubicSDR) applications, each with a per-plugin dependency matrix
  (volk, codec2, rtaudio, airspyhf, limesuite, ...) that would each
  need their own recipes first.
* **WSJT-X, JS8Call (a WSJT-X fork), FLdigi, QSSTV** -- Qt/FLTK ham
  radio apps built against a patched Hamlib fork and portaudio; WSJT-X
  specifically also cross-compiles Fortran DSP code, which is a known
  pain point even in native builds.
* **SatDump** -- CMake, but pulls in volk, fftw, and an actively
  changing set of per-satellite demodulator plugins.
* **SDRTrunk** -- a Java/Gradle application. This isn't a "write a
  recipe" gap so much as a toolchain mismatch: it needs a JVM running
  persistently on-target, which cuts directly against this same
  requirement doc's section 5.5 concern about SDR tool memory pressure
  on a 4GB board.
* **python3-scipy** -- not packaged in oe-core, meta-python, or
  meta-openembedded as of kirkstone (python3-numpy is, and is
  included). scipy's BLAS/LAPACK/Fortran cross-compile requirements
  are substantial. `python3-pip` is in the image if a runtime
  `pip install` over the network is an acceptable stopgap.

If any of these are actually required rather than nice-to-have,
budget them as separate, individually-scoped recipe-writing tasks on
a real Yocto build host -- each is realistically hours of iteration
against build failures, not something to get right on the first try
from reading a CMakeLists.txt.
