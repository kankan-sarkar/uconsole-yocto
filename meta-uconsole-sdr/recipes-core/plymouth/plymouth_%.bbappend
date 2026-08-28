# meta-oe's plymouth recipe only defaults PACKAGECONFIG "drm" on
# x86/x86-64 (PACKAGECONFIG:append:x86). Without it, plymouth has no
# way to draw to the DSI panel before Weston starts -- the CM4's VC4
# KMS driver (MACHINE_FEATURES "vc4graphics") is exactly what the drm
# renderer needs, so force it on for this machine.
PACKAGECONFIG:append = " drm"
