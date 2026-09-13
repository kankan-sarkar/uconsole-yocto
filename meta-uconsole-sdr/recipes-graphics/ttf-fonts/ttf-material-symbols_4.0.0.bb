require recipes-graphics/ttf-fonts/ttf.inc

SUMMARY = "Material Symbols Outlined, the icon set the uConsole UI is drawn with"
DESCRIPTION = "Icon font used for the dock, the command palette and the hardware \
status bar -- the same set the mockups in ui-mocks/ are drawn with. \
Needed because the fonts otherwise in this image (JetBrains Mono, \
Liberation) carry no pictographs at all: glyphs like the gear or \
satellite dish render as empty boxes without it, which is exactly what \
the first themed build did."
HOMEPAGE = "https://fonts.google.com/icons"

LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/Apache-2.0;md5=89aea4e17d99a7cacdbeed46a0096b10"

# Pinned to a specific commit rather than a branch: this repository has
# no release tarball for the font itself, and raw.githubusercontent
# content is only reproducible when addressed by commit sha. 4.0.0 is
# the repository's release tag at the time of this commit (2026-09-11).
MATERIAL_ICONS_REV = "40a7a292a79d9394157e1ea24f83d52d5e17c556"

# The upstream filename contains square brackets (the variable-font axis
# list), which bitbake's SRC_URI parser treats specially -- hence the
# percent-encoded form and an explicit downloadfilename.
SRC_URI = "https://raw.githubusercontent.com/google/material-design-icons/${MATERIAL_ICONS_REV}/variablefont/MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D.ttf;downloadfilename=MaterialSymbolsOutlined-${PV}.ttf"
SRC_URI[sha256sum] = "bf4c94b08c06c6b17e9d1a2d54a68c3f2c3435454761d487768df137a81f851d"

S = "${WORKDIR}"

# ttf.inc's do_install globs for *.ttf, which works here, but the
# downloaded name carries the version -- install it under the family
# name fontconfig and the Qt stylesheets expect.
do_install() {
    install -d ${D}${datadir}/fonts/truetype/
    install -m 0644 ${S}/MaterialSymbolsOutlined-${PV}.ttf \
        ${D}${datadir}/fonts/truetype/MaterialSymbolsOutlined.ttf
}

FILES:${PN} = "${datadir}/fonts"
