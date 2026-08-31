FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://nvme-fastboot.cfg \
    file://uconsole-pmic-rtc.cfg \
    file://uconsole-display-panel.cfg \
    file://clockworkpi-uconsole-overlay.dts \
    file://panel-cwu50.c \
    file://ocp8178_bl.c \
"

# NOTE: previously appended KERNEL_FEATURES += "cfg/smp.scc" here. That
# .scc feature-merge mechanism belongs to the linux-yocto kernel-cache
# convention; linux-raspberrypi fetches the RPi Foundation's own kernel
# tree directly and doesn't carry that feature repo, so the reference
# was unresolvable. Removed -- also redundant, since SMP is already on
# in the stock CM4 (quad-core) defconfig.

# ------------------------------------------------------------------
# AIO v2 board hardware support: DSI panel (cwu50), backlight
# (ocp8178), and PMIC (AXP221) devicetree overlay.
#
# None of these three exist in the stock RPi Foundation kernel tree
# this recipe builds -- they're ClockworkPi's own additions, living
# only in their fork (cuu/ClockworkPi-linux). Rather than switch this
# recipe's SRC_URI to that fork entirely (a much bigger, riskier
# change -- it tracks a newer kernel line (6.12 vs this recipe's
# 5.15) with no guarantee the rest of this BSP's config still applies
# cleanly), the two driver files and the overlay are cherry-picked
# in directly and wired into the existing source tree's Kconfig/
# Makefile/overlay list via sed against anchor lines confirmed
# present in the real rpi-5.15.y source before writing this.
#
# panel-cwu50.c needed one real adaptation for the 5.15 DRM panel API
# (see the comment at that line in the file); ocp8178_bl.c did not.
# Neither has been build- or hardware-tested yet -- treat the first
# CI run touching this as the real test, and the first physical boot
# as the real test of whether the panel actually lights up.
do_configure:prepend() {
    # Devicetree overlay: drop the file in and register it in the
    # overlays' own Makefile (an explicit dtbo-y list, not a wildcard
    # glob -- confirmed by reading the real Makefile first).
    cp "${WORKDIR}/clockworkpi-uconsole-overlay.dts" \
        "${S}/arch/arm/boot/dts/overlays/clockworkpi-uconsole-overlay.dts"
    sed -i \
        '/^dtbo-\$(CONFIG_ARCH_BCM2835) += \\$/a\	clockworkpi-uconsole.dtbo \\' \
        "${S}/arch/arm/boot/dts/overlays/Makefile"

    # DSI panel driver. Anchored on the (verified-unique) tab-indented
    # "depends on DRM && DRM_PANEL" line right under the "Display
    # Panels" menu heading -- confirmed via a real dry run that a
    # bare ^depends... anchor (no leading \t) silently matches
    # nothing, since GNU sed doesn't fuzz leading whitespace.
    cp "${WORKDIR}/panel-cwu50.c" "${S}/drivers/gpu/drm/panel/panel-cwu50.c"
    sed -i \
        '/^\tdepends on DRM && DRM_PANEL$/a\
\
config DRM_PANEL_CWU50\
	tristate "CWU50 panel"\
	depends on OF\
	depends on DRM_MIPI_DSI\
	depends on BACKLIGHT_CLASS_DEVICE\
	help\
	  ClockworkPi uConsole AIO v2 board DSI panel.' \
        "${S}/drivers/gpu/drm/panel/Kconfig"
    sed -i \
        '/^# SPDX-License-Identifier: GPL-2.0$/a\obj-$(CONFIG_DRM_PANEL_CWU50) += panel-cwu50.o' \
        "${S}/drivers/gpu/drm/panel/Makefile"

    # Backlight driver
    cp "${WORKDIR}/ocp8178_bl.c" "${S}/drivers/video/backlight/ocp8178_bl.c"
    sed -i \
        '/^endif # BACKLIGHT_CLASS_DEVICE$/i\
config BACKLIGHT_OCP8178\
	tristate "OCP8178 Backlight Driver"\
	depends on GPIOLIB\
	help\
	  ClockworkPi uConsole AIO v2 board backlight controller.\

' \
        "${S}/drivers/video/backlight/Kconfig"
    sed -i \
        '/^# Backlight & LCD drivers$/a\obj-$(CONFIG_BACKLIGHT_OCP8178)		+= ocp8178_bl.o' \
        "${S}/drivers/video/backlight/Makefile"
}
