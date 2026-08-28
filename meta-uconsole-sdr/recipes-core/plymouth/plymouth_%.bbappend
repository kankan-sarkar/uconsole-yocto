# meta-oe's plymouth recipe only defaults PACKAGECONFIG "drm" on
# x86/x86-64 (PACKAGECONFIG:append:x86). Without it, plymouth has no
# way to draw to the DSI panel before Weston starts -- the CM4's VC4
# KMS driver (MACHINE_FEATURES "vc4graphics") is exactly what the drm
# renderer needs, so force it on for this machine.
PACKAGECONFIG:append = " drm"

# "initrd" is on by default (PACKAGECONFIG ??= "pango initrd") and
# pulls in plymouth-initrd -> dracut, which isn't provided by any layer
# here. We don't want it anyway: this build skips initramfs entirely
# (see INITRAMFS_IMAGE_BUNDLE in the machine conf) by compiling the
# SD/NVMe drivers directly into the kernel.
PACKAGECONFIG:remove = "initrd"
