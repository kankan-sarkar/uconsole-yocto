"""
Shared theme source for every uConsole PyQt6 app (OOBE, lock screen,
control panel, and any future ones). The OOBE wizard's Theme page
writes the mode/accent choice to SETTINGS_FILE; everything else just
imports this module and calls build_qss()/palette()/accent_color()
instead of hardcoding colors, so a single choice actually propagates
system-wide instead of only affecting whichever app happened to
define it first.

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

DEFAULTS = {
    "theme_mode": "Dark",
    "accent_color": "#66fcf1",
}

PALETTES = {
    "Dark": {
        "bg_top": "#0b0c10",
        "bg_bottom": "#1f2833",
        "panel_bg": "rgba(31, 40, 51, 190)",
        "panel_border": "#45a29e",
        "fg": "#c5c6c7",
        "fg_title": "#ffffff",
    },
    "Light": {
        "bg_top": "#e8ecef",
        "bg_bottom": "#c9d2d8",
        "panel_bg": "rgba(255, 255, 255, 190)",
        "panel_border": "#45a29e",
        "fg": "#2b2f33",
        "fg_title": "#0b0c10",
    },
}


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
    return load_theme()["accent_color"]


def has_profile_image():
    return os.path.isfile(PROFILE_IMAGE_FILE)


def build_qss(extra_rules=""):
    """A stylesheet for flat, non-glass windows (OOBE-style pages)."""
    p = palette()
    accent = accent_color()
    return f"""
        QWidget {{ background-color: {p['bg_top']}; color: {p['fg']}; font-family: 'Courier New', monospace; }}
        QLabel {{ font-size: 16px; }}
        QLineEdit, QComboBox {{
            background-color: {p['bg_bottom']}; border: 2px solid {p['panel_border']};
            border-radius: 5px; padding: 8px; font-size: 16px; color: {p['fg_title']};
        }}
        QPushButton {{
            background-color: {p['panel_border']}; color: {p['bg_top']}; border: none;
            border-radius: 5px; padding: 12px; font-size: 16px; font-weight: bold;
        }}
        QPushButton:hover {{ background-color: {accent}; }}
        QRadioButton {{ font-size: 15px; }}
        {extra_rules}
    """


def build_glass_qss(extra_rules=""):
    """A stylesheet for the translucent 'glass card' look (lock screen)."""
    p = palette()
    accent = accent_color()
    return f"""
        #glassCard {{
            background-color: {p['panel_bg']};
            border: 1px solid {p['panel_border']};
            border-radius: 18px;
        }}
        QLabel {{ font-size: 16px; color: {p['fg']}; background: transparent; }}
        #titleLabel {{ font-size: 30px; font-weight: bold; color: {p['fg_title']}; }}
        #indicator {{
            border: 2px solid {accent}; border-radius: 8px;
            padding: 14px; font-size: 36px; color: {p['fg_title']};
            background-color: rgba(0, 0, 0, 60);
        }}
        {extra_rules}
    """
