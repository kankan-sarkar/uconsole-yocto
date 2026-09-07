# Real crash, found via QEMU testing and matching every real-hardware
# symptom: ModuleNotFoundError: No module named 'PyQt6.QtWidgets'.
# Every uConsole Qt6 GUI app (uconsole-oobe, uconsole-panel,
# uconsole-power-menu) imports QtWidgets classes (QApplication,
# QWidget, QVBoxLayout, QPushButton, ...), but meta-qt6's own
# python3-pyqt6 recipe (verified against the real recipe source at
# code.qt.io) hardcodes its enabled module list to
# QtCore/QtGui/QtNetwork/QtXml/QtQml/QtSql -- QtWidgets is simply
# never in it, for anyone, on any machine. This is why oobe.service
# crashed immediately on startup and Weston fell back to its own
# stock demo desktop (weston-terminal + clock) instead of ever
# showing the actual uConsole GUI -- on the real DSI panel and the
# CM4 IO board's HDMI output alike, confirming it was never a
# display-hardware issue at all.
#
# PYQT_MODULES is a plain bitbake variable the recipe's own
# do_configure() loops over to build --enable=<module> sip-build
# arguments -- appending here is picked up correctly, since bitbake
# resolves the variable's full value before generating that shell
# function's code. No extra DEPENDS/RDEPENDS needed: QtWidgets is
# part of qtbase itself (already a DEPENDS/RDEPENDS of this recipe),
# not a separate Qt6 module that needs pulling in.
PYQT_MODULES:append = " QtWidgets"
