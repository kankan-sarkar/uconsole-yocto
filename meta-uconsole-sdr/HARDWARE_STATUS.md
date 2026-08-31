# AIO v2 board hardware support status

Added 2026-08-31, prompted by a pre-flash hardware check: does this
image actually support the uConsole's onboard keyboard, power button,
DSI display, and AIO v2/battery board? At the time, the answer was no
to all four -- this project's kernel config only had generic
"AXP228 family on i2c_arm" assumptions with no matching devicetree
node, no keyboard USB-host-mode overlay, and no DSI panel driver at
all. This document tracks what was found and fixed, and -- just as
important -- what is still genuinely unverified.

Everything below was checked directly against ClockworkPi's own
reference implementation: `clockworkpi/uConsole` (their published
config.txt, keyboard firmware, schematics) and their kernel fork
`cuu/ClockworkPi-linux` (branch `rpi-6.12.y`), not assumed or guessed.

## Confirmed and fixed

* **Keyboard.** The uConsole keyboard is its own MCU (Arduino-style
  firmware, `clockworkpi/uConsole` `Code/uconsole_keyboard/`) that
  presents to Linux as a plain USB HID device once the CM4's USB-OTG
  controller is forced into host mode. Added `dtoverlay=dwc2,dr_mode=host`
  to `RPI_EXTRA_CONFIG` in `uconsole-cm4.conf` -- a stock, mainline
  overlay, no custom kernel needed. `uconsole-hotkey.py` already
  scanned for it by name; unchanged.

* **PMIC (AXP221) and power button.** ClockworkPi's real overlay
  (`clockworkpi-uconsole-overlay.dts`, fetched and imported verbatim)
  wires an **AXP221** PMIC on **i2c0 @0x34** -- not the generic
  "AXP228 family on i2c_arm (i2c1)" this project previously assumed
  in `uconsole-pmic-rtc.cfg`'s comments, with no matching devicetree
  node at all. The kernel CONFIG symbols chosen back then
  (`CONFIG_MFD_AXP20X`, `CONFIG_INPUT_AXP20X_PEK`, etc.) turned out to
  already be correct -- AXP221 is a listed compatible string in
  mainline's `drivers/mfd/axp20x-i2c.c` -- so only the devicetree
  node was actually missing. The power button is the PMIC's PEK
  function, exposed as a plain `KEY_POWER` evdev device named
  `axp20x-pek` (mainline `drivers/input/misc/axp20x-pek.c`, read
  directly before relying on it): a single press/release pair, no
  built-in short/long distinction from the kernel.

  * **Power-on from off** is pure PMIC hardware behavior (silicon
    reacting to the PEK pin, active before Linux or even U-Boot is
    running) -- nothing to implement.
  * **Software behavior** (added to `uconsole-hotkey.py`): a press
    held under 5s launches a new shutdown-menu GUI
    (`uconsole-power-menu`, in the `uconsole-panel` package -- Shut
    Down / Restart / Cancel); held >=5s triggers
    `systemctl poweroff --force` directly, without waiting for
    release.
  * **Hardware failsafe**: the AXP221 PEK driver also exposes its own
    silicon-level forced-poweroff timer via a `shutdown` sysfs
    attribute (one of 4000/6000/8000/10000ms, not freely settable).
    `uconsole-hotkey.py` sets it to 8000ms at startup -- a backstop
    that works even if Linux is completely hung and this daemon isn't
    scheduled at all.
  * `systemd-logind`'s own `HandlePowerKey` would otherwise also react
    to the same `KEY_POWER` events and race the daemon on every press
    -- disabled via a new `logind.conf.d` drop-in
    (`90-uconsole-power-button.conf`, `HandlePowerKey=ignore`,
    `HandlePowerKeyLongPress=ignore`).

* **DSI display.** The bigger gap: ClockworkPi's overlay declares a
  fully custom panel (`compatible = "cw,cwu50"`) and backlight
  (`compatible = "ocp8178-backlight"`) with real driver source
  (`panel-cwu50.c`, `ocp8178_bl.c`) that exists **only** in their
  kernel fork -- not in the stock RPi Foundation tree
  `linux-raspberrypi_5.15.bb` builds. Without it, the screen has no
  driver at all, regardless of anything at the software/Weston layer.
  Cherry-picked both files onto this recipe's 5.15 baseline (see
  `linux-raspberrypi_%.bbappend`) rather than switching the whole
  kernel source tree to ClockworkPi's 6.12-based fork -- a much larger
  change with no guarantee the rest of this BSP's kernel config still
  applies. `panel-cwu50.c` needed one confirmed API adaptation
  (`struct drm_panel`'s `prepare_prev_first` field is named
  `prepare_upstream_first` on 5.15 -- checked against the real
  `include/drm/drm_panel.h` on the `rpi-5.15.y` branch before making
  the change); `ocp8178_bl.c` used a stable enough API surface to need
  none. `RPI_EXTRA_CONFIG` also gained `ignore_lcd=1` and
  `max_framebuffers=2` from the same reference config.txt.

## Verified against the real build on hs01

The first CI run after this change succeeded, but "the build succeeded"
turned out not to mean "the config actually landed" -- checked
directly on hs01 rather than trusting that:

* The `sed`-based Kconfig/Makefile/overlay wiring in
  `linux-raspberrypi_%.bbappend` **did** land correctly in the real
  source tree (`tmp/work-shared/uconsole-cm4/kernel-source/` -- not
  the per-recipe workdir, a kernel-yocto-specific detail found the
  hard way while chasing this down). `arch/arm64/boot/dts/overlays`
  turned out to be a symlink to `arch/arm/boot/dts/overlays`, so the
  overlay Makefile edit (targeting the `arm` path, matching the real
  upstream Makefile's own location) was correct as written.
* But **`CONFIG_DRM_PANEL_CWU50` and `CONFIG_BACKLIGHT_OCP8178` were
  silently "not set" in the final `.config`** despite
  `uconsole-display-panel.cfg` requesting `=y` for both. Root cause:
  the stock defconfig has `CONFIG_BACKLIGHT_CLASS_DEVICE=m`, and both
  new symbols `depends on` it -- Kconfig's dependency solver drops a
  `=y` request back to unset with no error or warning when a
  dependency is only `=m`, rather than failing loudly. Fixed by also
  promoting `CONFIG_BACKLIGHT_CLASS_DEVICE=y` in the same fragment
  (safe: a module can depend on a built-in fine, so this doesn't
  break whatever else already used it as `=m`).
* This is exactly the kind of thing "the build succeeded" doesn't
  catch -- a `.cfg` fragment requesting a symbol that then silently
  fails its own dependency check produces a perfectly green build
  with the driver just... not enabled. Worth remembering next time
  a kernel `.cfg` fragment is added here: check the actual `.config`
  for the requested symbol, don't just check the task didn't fail.

* **Second round, same lesson, different mechanism.** After promoting
  `BACKLIGHT_CLASS_DEVICE=y`, `DRM_PANEL_CWU50` and `BACKLIGHT_OCP8178`
  were *still* silently "not set" -- but this time not from an unmet
  Kconfig dependency. Verified by hand on hs01: force-setting both
  with the kernel's own `scripts/config` and re-running a real
  `make olddefconfig` against the exact same `.config` kept them `=y`
  with no complaint, proving both symbols' actual dependencies were
  already fully satisfied. The likely real cause: kernel-yocto's own
  fragment-merge step checks requested symbols against
  `yocto-kernel-cache`'s symbol-audit database, and brand-new symbols
  this project just introduced aren't in it -- so the request gets
  silently filtered rather than merged, even though the symbol is
  perfectly valid in the (patched) source tree. Worked around with a
  `do_configure:append()` that force-sets just these two symbols via
  `scripts/config` after the normal config step, then re-runs
  `olddefconfig` -- the exact mechanism confirmed working by hand,
  not a guess.

## Third round: the kernel now builds and boots the driver code, but the overlay wasn't shipped

With the two Kconfig-merge fixes above, `linux-raspberrypi` actually
built clean: `panel-cwu50.ko` (module -- `DRM_PANEL_CWU50` ended up
`=m`, not `=y`, because its `depends on DRM` couldn't be satisfied by
`CONFIG_DRM=m`; `scripts/config -e` + a real `olddefconfig` downgraded
it to the best achievable value rather than dropping it, which is
fine -- confirmed the `.ko` is packaged and actually installed into
the real rootfs) and `ocp8178_bl` (built-in, `=y`, confirmed in the
final `.config`). Two more real compile errors surfaced and got fixed
along the way, both genuine 5.15-vs-6.12 kernel API drift caught by
the actual build, not guessed: `backlight_ops.controls_device` doesn't
exist on 5.15 (`check_fb` instead), and `mipi_dsi_driver.remove`
returns `int` here, not `void`.

But the devicetree overlay itself was never built at all, despite
being correctly added to the overlays Makefile's `dtbo-y` list --
confirmed empirically: nothing named `clockworkpi-uconsole` exists
anywhere in the build output tree, yet dozens of *other* overlays in
that same Makefile list did build. The actual gate turned out to be a
separate variable, `RPI_KERNEL_DEVICETREE_OVERLAYS` (from
`rpi-base.inc`) -- every overlay that did build/deploy was a member of
it. Added `clockworkpi-uconsole.dtbo` to it in `uconsole-cm4.conf`.
Without this, `RPI_EXTRA_CONFIG`'s `dtoverlay=clockworkpi-uconsole`
line in config.txt would have referenced an overlay that was never
even compiled -- the firmware would have failed to apply it at boot
(silently or with a boot-log error, untested which).

## Genuinely still unverified

* **Neither driver has been build-tested or run on real hardware.**
  The Kconfig/Makefile/overlay wiring was verified with a real dry
  run of the exact `sed` commands against synthetic copies of the
  actual anchor lines (a bug was caught and fixed this way -- an
  early version of the panel Kconfig injection silently matched
  nothing because the real anchor line is tab-indented and the first
  attempt's pattern wasn't). That confirms the *plumbing*; it does not
  confirm the drivers compile clean against 5.15's exact headers
  beyond the one field rename already found, and it says nothing
  about whether the panel actually lights up, the touch/orientation
  is right, or backlight brightness behaves -- only real hardware can
  answer that.
* **The RTC (ds3231/ds1307, `dtoverlay=i2c-rtc,ds3231` on i2c_arm)
  predates this check and was left as-is.** It is *not* part of
  ClockworkPi's reference overlay above, which raises a real
  question: is there actually a separate ds3231 RTC chip on the AIO v2
  board, or was that an unverified assumption from earlier in this
  project? Left alone rather than guessed at either way -- flagging
  it here rather than silently removing possibly-real config.
* **GPIO pin numbers, reset polarity, and panel rotation** in the
  imported overlay are taken verbatim from ClockworkPi's own file,
  not independently re-derived from a schematic -- correct only to
  the extent their reference is accurate for this specific CM4/AIO v2
  revision.

**Bottom line before flashing:** this is a real, evidence-based fix
for a real gap, not a guess -- but "compiles and the sed plumbing is
right" and "the screen turns on" are different claims. Treat the
first CI build touching this as confirmation of the former; only a
physical boot confirms the latter.
