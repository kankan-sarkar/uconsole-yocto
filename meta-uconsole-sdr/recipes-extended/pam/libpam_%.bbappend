FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += "file://common-auth"

do_install:append() {
    install -m 0644 ${WORKDIR}/common-auth ${D}${sysconfdir}/pam.d/common-auth
}

RDEPENDS:${PN} += "pam-plugin-faillock"
