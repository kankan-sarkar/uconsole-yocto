SUMMARY = "uConsole RF/network security auditing tools (requirement.md 5.1, 3)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

PACKAGE_ARCH = "${MACHINE_ARCH}"

inherit packagegroup

# kismet is intentionally not here -- no Yocto recipe exists for it in
# any layer this project pulls in, and its build (meson + protobuf-c
# codegen + a dozen-odd libs) is substantial enough that hand-writing
# one without a real build machine to iterate on isn't credible. See
# SDR_TOOLS_STATUS.md.
RDEPENDS:${PN} = " \
    aircrack-ng \
"
