# Companion to uconsole-image.bb's EXTRA_USERS_PARAMS bring-up
# fallback (root password + forced first-login change): OpenSSH's
# compiled-in default is PermitRootLogin=prohibit-password (allows
# root over SSH only with a key, never a password), confirmed in the
# real oe-core sshd_config, which just leaves it commented out rather
# than setting it. Without this override the fallback password would
# work over serial but not SSH.
do_install:append() {
    sed -i -e 's:#PermitRootLogin prohibit-password:PermitRootLogin yes:' \
        ${D}${sysconfdir}/ssh/sshd_config
    if [ -e ${D}${sysconfdir}/ssh/sshd_config_readonly ]; then
        sed -i -e 's:#PermitRootLogin prohibit-password:PermitRootLogin yes:' \
            ${D}${sysconfdir}/ssh/sshd_config_readonly
    fi
}
