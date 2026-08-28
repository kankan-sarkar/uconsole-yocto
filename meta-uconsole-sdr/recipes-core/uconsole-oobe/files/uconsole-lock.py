#!/usr/bin/env python3
import sys
import hashlib
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QLinearGradient, QColor

import uconsole_theme

PIN_FILE = "/etc/uconsole_pin.sha256"
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 30  # seconds, base for exponential backoff

DIGIT_KEYS = {
    Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2",
    Qt.Key.Key_3: "3", Qt.Key.Key_4: "4", Qt.Key.Key_5: "5",
    Qt.Key.Key_6: "6", Qt.Key.Key_7: "7", Qt.Key.Key_8: "8",
    Qt.Key.Key_9: "9",
}

# How long a freshly typed digit stays visible before collapsing back
# to the generic idle glyph. Long enough to confirm what was pressed,
# short enough that a shoulder-surfer can't line up a full sequence.
DIGIT_REVEAL_MS = 700

IDLE_GLYPH = "●"  # a single filled circle -- never multiplies with length


def make_backdrop(size):
    """Blurred full-screen background. Uses the OOBE profile image if
    one was set, otherwise a generated gradient in the current theme's
    colors -- either way this is a real Qt-rendered blur (QGraphicsBlurEffect
    over an offscreen widget), not a Wayland compositor effect, so it
    doesn't depend on what the compositor supports."""
    p = uconsole_theme.palette()

    if uconsole_theme.has_profile_image():
        base = QPixmap(uconsole_theme.PROFILE_IMAGE_FILE)
        base = base.scaled(
            size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        base = QPixmap(size)
        painter = QPainter(base)
        gradient = QLinearGradient(0, 0, 0, size.height())
        gradient.setColorAt(0, QColor(p["bg_top"]))
        gradient.setColorAt(1, QColor(p["bg_bottom"]))
        painter.fillRect(base.rect(), gradient)
        painter.end()

    holder = QLabel()
    holder.setPixmap(base)
    holder.resize(base.size())
    blur = QGraphicsBlurEffect()
    blur.setBlurRadius(28)
    holder.setGraphicsEffect(blur)
    blurred = holder.grab()

    # Darken so the glass card and text stay readable over any photo.
    painter = QPainter(blurred)
    painter.fillRect(blurred.rect(), QColor(0, 0, 0, 110))
    painter.end()
    return blurred


def circular_avatar(diameter=110):
    if not uconsole_theme.has_profile_image():
        return None
    src = QPixmap(uconsole_theme.PROFILE_IMAGE_FILE)
    if src.isNull():
        return None
    src = src.scaled(
        diameter, diameter, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    out = QPixmap(diameter, diameter)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(0, 0, diameter, diameter)
    painter.setClipPath(clip)
    x = (src.width() - diameter) // 2
    y = (src.height() - diameter) // 2
    painter.drawPixmap(-x, -y, src)
    painter.end()
    return out


class LockScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.attempts = 0
        self.entered_pin = ""
        self.locked_out = False

        try:
            with open(PIN_FILE, "r") as f:
                self.saved_hash = f.read().strip()
        except FileNotFoundError:
            print("PIN file not found! Falling back to unsecure mode.")
            sys.exit(0)

        self.reveal_timer = QTimer(self)
        self.reveal_timer.setSingleShot(True)
        self.reveal_timer.timeout.connect(self._collapse_indicator)

        self.init_ui()

    def init_ui(self):
        self.setWindowState(Qt.WindowState.WindowFullScreen)

        screen = QApplication.primaryScreen().size()
        self.setFixedSize(screen)

        self.background = QLabel(self)
        self.background.setPixmap(make_backdrop(screen))
        self.background.setGeometry(0, 0, screen.width(), screen.height())

        card = QWidget(self)
        card.setObjectName("glassCard")
        card.setFixedWidth(420)
        card.setStyleSheet(uconsole_theme.build_glass_qss())

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(36, 36, 36, 36)

        avatar_pix = circular_avatar()
        if avatar_pix is not None:
            avatar_label = QLabel()
            avatar_label.setPixmap(avatar_pix)
            avatar_label.setFixedSize(QSize(avatar_pix.width(), avatar_pix.height()))
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("SYSTEM LOCKED")
        self.status_label.setObjectName("titleLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # A single fixed-width glyph. It never grows with the number of
        # digits entered so far -- only its *content* changes, briefly,
        # to the digit just pressed. This is intentionally not a
        # QLineEdit: any built-in echo mode (including Password) still
        # renders one mark per character, which leaks PIN length.
        self.indicator = QLabel(IDLE_GLYPH)
        self.indicator.setObjectName("indicator")
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indicator.setFixedWidth(140)
        layout.addWidget(self.indicator, alignment=Qt.AlignmentFlag.AlignCenter)

        self.msg_label = QLabel("Type PIN, press ENTER")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.msg_label)

        card.setLayout(layout)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        if self.locked_out:
            return

        key = event.key()
        if key in DIGIT_KEYS:
            self.entered_pin += DIGIT_KEYS[key]
            self._flash_digit(DIGIT_KEYS[key])
        elif key == Qt.Key.Key_Backspace:
            self.entered_pin = self.entered_pin[:-1]
            self._collapse_indicator()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.attempt_unlock()

    def _flash_digit(self, digit):
        self.indicator.setText(digit)
        self.reveal_timer.start(DIGIT_REVEAL_MS)

    def _collapse_indicator(self):
        self.indicator.setText(IDLE_GLYPH)

    def attempt_unlock(self):
        entered_pin = self.entered_pin
        self.entered_pin = ""
        self._collapse_indicator()

        hashed_attempt = hashlib.sha256(entered_pin.encode()).hexdigest()

        if hashed_attempt == self.saved_hash:
            sys.exit(0)
        else:
            self.attempts += 1
            if self.attempts >= MAX_ATTEMPTS:
                self.trigger_backoff()
            else:
                self.msg_label.setText(f"AUTH FAILED. Attempts remaining: {MAX_ATTEMPTS - self.attempts}")
                self.msg_label.setStyleSheet("color: #ff4444; font-size: 15px; font-weight: bold;")

    def trigger_backoff(self):
        self.locked_out = True
        self.entered_pin = ""
        # Exponential backoff: doubles for every group of MAX_ATTEMPTS
        # failures past the initial threshold.
        penalty = LOCKOUT_TIME * (2 ** (self.attempts - MAX_ATTEMPTS))
        self.msg_label.setText(f"SYSTEM LOCKED DOWN. Wait {penalty}s.")
        self.msg_label.setStyleSheet("color: #ff4444; font-size: 16px; font-weight: bold;")

        QTimer.singleShot(penalty * 1000, self.reset_attempts)

    def reset_attempts(self):
        self.locked_out = False
        self.msg_label.setText("Type PIN, press ENTER")
        self.msg_label.setStyleSheet("")
        self.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    lock = LockScreen()
    lock.show()
    sys.exit(app.exec())
