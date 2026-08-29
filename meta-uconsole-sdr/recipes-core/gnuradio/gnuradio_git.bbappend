# meta-sdr's gnuradio_git.bb defaults PACKAGECONFIG to "qtgui5 grc
# zeromq" -- "qtgui5" pulls in real Qt5 (qtbase, qwt-qt5,
# python3-pyqt5, meta-qt5's cmake_qt5 class) for GNU Radio's own Qt
# plotting widgets. We don't consume the gnuradio-qtgui subpackage
# anywhere (packagegroup-uconsole-sdr.bb only needs the base gnuradio
# RDEPENDS), and this project's own PyQt6 apps need Qt6's qtbase --
# a single build can't resolve "qtbase" to two different providers at
# once, and meta-qt5 has been dropped entirely (see kas-project.yml
# and the removal of gqrx from packagegroup-uconsole-sdr.bb for the
# other half of this). gnuradio-companion (grc) and the rest of the
# signal-processing blocks are unaffected -- only the separate Qt
# plotting widgets go away.
PACKAGECONFIG:remove = "qtgui5"
