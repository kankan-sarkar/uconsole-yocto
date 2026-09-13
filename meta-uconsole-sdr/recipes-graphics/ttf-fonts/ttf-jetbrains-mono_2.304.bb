require recipes-graphics/ttf-fonts/ttf.inc

SUMMARY = "JetBrains Mono, the typeface the uConsole UI is designed around"
DESCRIPTION = "Monospace typeface specified throughout ui-mocks/uconsole_terminal_ui/DESIGN.md: \
every typography level in that design system, from headlines down to \
status-bar labels, is JetBrains Mono. Pulled in by uconsole-theme, \
whose stylesheets name it explicitly -- without it Qt silently falls \
back to whatever else is installed and the UI stops matching the \
mockups."
HOMEPAGE = "https://www.jetbrains.com/lp/mono/"

LICENSE = "OFL-1.1"
LIC_FILES_CHKSUM = "file://OFL.txt;md5=43dc1a748ef82aa746d6a645d52578a9"

SRC_URI = "https://github.com/JetBrains/JetBrainsMono/releases/download/v${PV}/JetBrainsMono-${PV}.zip"
SRC_URI[sha256sum] = "6f6376c6ed2960ea8a963cd7387ec9d76e3f629125bc33d1fdcd7eb7012f7bbf"

# The zip has no wrapping directory -- OFL.txt and fonts/ sit at the top
# level, so it unpacks straight into WORKDIR.
S = "${WORKDIR}"

# Only the weights DESIGN.md's typography scale actually uses (400, 500,
# 600, 700). The release ships 32 files -- every weight, matching
# italics, and a separate no-ligature "NL" family -- which is ~8MB of
# rootfs for glyphs nothing in this image references. ttf.inc's own
# do_install would install all of them, hence the override.
UCONSOLE_FONT_WEIGHTS = "Regular Medium SemiBold Bold"

do_install() {
    install -d ${D}${datadir}/fonts/truetype/
    for weight in ${UCONSOLE_FONT_WEIGHTS}; do
        install -m 0644 ${S}/fonts/ttf/JetBrainsMono-${weight}.ttf \
            ${D}${datadir}/fonts/truetype/
    done
}

FILES:${PN} = "${datadir}/fonts"
