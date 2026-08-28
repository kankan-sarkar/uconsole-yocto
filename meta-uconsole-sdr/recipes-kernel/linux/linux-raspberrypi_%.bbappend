FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://nvme-fastboot.cfg \
    file://uconsole-pmic-rtc.cfg \
"

# NOTE: previously appended KERNEL_FEATURES += "cfg/smp.scc" here. That
# .scc feature-merge mechanism belongs to the linux-yocto kernel-cache
# convention; linux-raspberrypi fetches the RPi Foundation's own kernel
# tree directly and doesn't carry that feature repo, so the reference
# was unresolvable. Removed -- also redundant, since SMP is already on
# in the stock CM4 (quad-core) defconfig.
