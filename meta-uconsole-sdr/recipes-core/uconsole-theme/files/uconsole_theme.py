"""
Shared theme source for every uConsole PyQt6 app (OOBE, lock screen,
control panel, home screen, and any future ones). The OOBE wizard's
Theme page writes the mode/accent choice to SETTINGS_FILE; everything
else imports this module and calls build_qss()/palette()/accent_color()
instead of hardcoding colors, so a single choice actually propagates
system-wide instead of only affecting whichever app defined it first.

The palette and type scale come from the design system in
ui-mocks/uconsole_terminal_ui/DESIGN.md -- deep slate surfaces,
electric cyan as the interactive accent, phosphor green for healthy
status, JetBrains Mono throughout. Token names below match that file so
the two can be diffed against each other; the mockups in ui-mocks/*/
screen.png are what these are meant to reproduce.

This covers our own apps. It does NOT make arbitrary third-party Qt
apps (e.g. a future SDRangel/gqrx install) follow the theme -- that
would need a system-wide Qt platform theme (qt6ct + QT_QPA_PLATFORMTHEME)
sitting underneath every Qt app, which isn't set up here. See
SDR_TOOLS_STATUS.md.
"""
import json
import os

SETTINGS_FILE = "/etc/uconsole/settings.json"
PROFILE_IMAGE_FILE = "/etc/uconsole/profile.png"
SPLASH_IMAGE_FILE = "/usr/share/plymouth/themes/uconsole/splash.png"

# Named in every QSS this module builds. Provided by ttf-jetbrains-mono,
# which uconsole-theme RDEPENDS on -- if it were missing, Qt would fall
# back silently and the UI would stop matching the mockups, so the
# fallbacks here are only for running these scripts on a dev box.
FONT_FAMILY = "'JetBrains Mono', 'DejaVu Sans Mono', monospace"

# Material Symbols, from ttf-material-symbols. Kept separate from
# FONT_FAMILY because Qt stylesheets don't do CSS-style family
# fallback: the *first* matching family wins for the whole run, so a
# pictograph can't simply fall through to another font the way it does
# in a browser. Icon labels have to name this family explicitly.
ICON_FONT_FAMILY = "Material Symbols Outlined"

# Referenced by codepoint rather than by the ligature name used on the
# web ("terminal", "settings", ...): ligature substitution depends on
# shaping that Qt does not reliably apply to short label strings,
# whereas a codepoint always maps straight to the glyph. Values are
# from the font's own .codepoints manifest at the pinned revision.
ICONS = {
    "terminal": "",
    "settings": "",
    "folder": "",
    "monitoring": "",
    "wifi": "",
    "code": "",
    "search": "",
    "satellite": "",
    "thermostat": "",
    "bolt": "",
    "lock": "",
    "vpn_key": "",
    "network": "",
}


def icon(name):
    """Glyph for a Material Symbols icon name, or '' if unknown.

    Returns empty rather than raising so a missing icon degrades to a
    blank space instead of taking down a shell that is the only way to
    reach the device's UI.
    """
    return ICONS.get(name, "")


DEFAULTS = {
    "theme_mode": "Dark",
    "accent_color": "#7bd0ff",
}

# Surface ramp, foreground and outline tokens, straight from DESIGN.md.
# Dark is the designed-for case; Light is a derived equivalent kept
# because the OOBE wizard offers the choice and the lock screen has to
# stay legible in daylight.
PALETTES = {
    "Dark": {
        "background": "#081425",
        "surface": "#081425",
        "surface_lowest": "#040e1f",
        "surface_low": "#111c2d",
        "surface_container": "#152031",
        "surface_high": "#1f2a3c",
        "surface_highest": "#2a3548",
        "surface_bright": "#2f3a4c",
        "on_surface": "#d8e3fb",
        "on_surface_variant": "#c6c6cd",
        "outline": "#909097",
        "outline_variant": "#45464d",
        "primary": "#bec6e0",
        "secondary": "#7bd0ff",
        "on_secondary": "#00354a",
        "tertiary": "#45dfa4",
        "error": "#ffb4ab",
        # Legacy key names, kept so older call sites keep working.
        "bg_top": "#081425",
        "bg_bottom": "#111c2d",
        "panel_bg": "rgba(21, 32, 49, 190)",
        "panel_border": "#2a3548",
        "fg": "#d8e3fb",
        "fg_title": "#ffffff",
    },
    "Light": {
        "background": "#e8ecef",
        "surface": "#e8ecef",
        "surface_lowest": "#ffffff",
        "surface_low": "#dfe4e8",
        "surface_container": "#d5dbe0",
        "surface_high": "#c9d2d8",
        "surface_highest": "#bcc6ce",
        "surface_bright": "#ffffff",
        "on_surface": "#0b0c10",
        "on_surface_variant": "#41474d",
        "outline": "#6b7178",
        "outline_variant": "#b3bac0",
        "primary": "#2b3242",
        "secondary": "#00668a",
        "on_secondary": "#ffffff",
        "tertiary": "#00875a",
        "error": "#ba1a1a",
        "bg_top": "#e8ecef",
        "bg_bottom": "#c9d2d8",
        "panel_bg": "rgba(255, 255, 255, 200)",
        "panel_border": "#bcc6ce",
        "fg": "#2b2f33",
        "fg_title": "#0b0c10",
    },
}

# DESIGN.md's "Soft" shape language: a precise, engineered look rather
# than pill-shaped everything.
RADIUS = {"sm": 2, "default": 4, "md": 6, "lg": 8, "xl": 12}

# Condensed deliberately -- this display is 1280x480, so the scale
# starts at 2px to fit dense telemetry without reflowing.
SPACING = {"xs": 2, "sm": 4, "md": 8, "lg": 16, "xl": 24}


def load_theme():
    theme = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        theme["theme_mode"] = data.get("theme_mode", theme["theme_mode"])
        theme["accent_color"] = data.get("accent_color", theme["accent_color"])
    except Exception:
        pass
    if theme["theme_mode"] not in PALETTES:
        theme["theme_mode"] = "Dark"
    return theme


def palette():
    theme = load_theme()
    return PALETTES[theme["theme_mode"]]


def accent_color():
    """The user's chosen accent, defaulting to the design's cyan.

    Kept separate from palette()['secondary'] on purpose: the OOBE
    wizard lets the user pick one, and that choice should win over the
    design default without altering the rest of the ramp.
    """
    return load_theme()["accent_color"]


def has_profile_image():
    return os.path.isfile(PROFILE_IMAGE_FILE)


def build_qss(extra_rules=""):
    """Stylesheet for standard, non-glass windows (OOBE pages, panels).

    Inputs render in the accent colour with a border that solidifies on
    focus, per DESIGN.md's "command line style inputs"; buttons are
    translucent with a crisp accent border until hovered, when they fill
    solid for unambiguous d-pad/keyboard feedback.
    """
    p = palette()
    accent = accent_color()
    return f"""
        QWidget {{
            background-color: {p['background']};
            color: {p['on_surface']};
            font-family: {FONT_FAMILY};
            font-size: 13px;
        }}
        QLabel {{ font-size: 13px; background: transparent; }}
        QLabel#title {{
            font-size: 20px; font-weight: 600; color: {p['on_surface']};
        }}
        QLabel#subtitle {{ font-size: 11px; color: {p['on_surface_variant']}; }}

        QLineEdit, QComboBox, QListWidget, QPlainTextEdit, QTextEdit {{
            background-color: {p['surface_lowest']};
            border: 1px solid {p['outline_variant']};
            border-radius: {RADIUS['default']}px;
            padding: {SPACING['md']}px;
            font-size: 13px;
            color: {p['on_surface']};
            selection-background-color: {accent};
            selection-color: {p['on_secondary']};
        }}
        QLineEdit:focus, QComboBox:focus, QListWidget:focus {{
            border: 1px solid {accent};
        }}
        QLineEdit::placeholder {{ color: {p['outline']}; }}

        QListWidget::item {{
            padding: {SPACING['md']}px;
            border-radius: {RADIUS['default']}px;
        }}
        QListWidget::item:selected {{
            background-color: {accent};
            color: {p['on_secondary']};
        }}

        QPushButton {{
            background-color: {p['surface_high']};
            color: {p['on_surface']};
            border: 1px solid {p['outline_variant']};
            border-radius: {RADIUS['default']}px;
            padding: {SPACING['md']}px {SPACING['lg']}px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover, QPushButton:focus {{
            background-color: {accent};
            color: {p['on_secondary']};
            border: 1px solid {accent};
        }}
        QPushButton:disabled {{
            color: {p['outline']};
            border: 1px solid {p['outline_variant']};
            background-color: {p['surface_low']};
        }}

        QRadioButton, QCheckBox {{ font-size: 13px; spacing: {SPACING['md']}px; }}
        QProgressBar {{
            border: 1px solid {p['outline_variant']};
            border-radius: {RADIUS['sm']}px;
            background-color: {p['surface_lowest']};
            text-align: center;
        }}
        QProgressBar::chunk {{ background-color: {p['tertiary']}; }}

        QSlider::groove:horizontal {{
            height: 4px; background: {p['surface_highest']};
            border-radius: {RADIUS['sm']}px;
        }}
        QSlider::handle:horizontal {{
            background: {accent}; width: 14px; margin: -6px 0;
            border-radius: {RADIUS['md']}px;
        }}
        {extra_rules}
    """


def build_glass_qss(extra_rules=""):
    """Stylesheet for the translucent 'glass card' surfaces.

    DESIGN.md establishes depth through translucency and ghost borders
    rather than drop shadows -- Qt has no backdrop-blur, so the frosted
    effect is approximated with a semi-transparent container over the
    dimmed background.
    """
    p = palette()
    accent = accent_color()
    return f"""
        #glassCard {{
            background-color: {p['panel_bg']};
            border: 1px solid {p['surface_highest']};
            border-radius: {RADIUS['lg']}px;
        }}
        #glassCard QLabel {{ background: transparent; }}
        QLabel {{
            font-size: 13px;
            color: {p['on_surface']};
            background: transparent;
            font-family: {FONT_FAMILY};
        }}
        #titleLabel {{
            font-size: 24px; font-weight: 700; color: {p['on_surface']};
        }}
        #sectionLabel {{
            font-size: 11px; font-weight: 500; letter-spacing: 1px;
            color: {p['on_surface_variant']};
        }}
        #indicator {{
            border: 1px solid {accent};
            border-radius: {RADIUS['lg']}px;
            padding: 14px; font-size: 32px;
            color: {p['on_surface']};
            background-color: {p['surface_lowest']};
        }}
        /* Status chips: ONLINE / CPU 42% / SECURE. */
        #chipOk {{
            color: {p['tertiary']}; border: 1px solid {p['tertiary']};
            border-radius: {RADIUS['sm']}px;
            padding: {SPACING['xs']}px {SPACING['sm']}px; font-size: 11px;
        }}
        #chipWarn {{
            color: {p['error']}; border: 1px solid {p['error']};
            border-radius: {RADIUS['sm']}px;
            padding: {SPACING['xs']}px {SPACING['sm']}px; font-size: 11px;
        }}
        {extra_rules}
    """
