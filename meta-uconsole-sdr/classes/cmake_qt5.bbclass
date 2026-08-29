# Empty stub. The real cmake_qt5.bbclass came from meta-qt5, which has
# been removed entirely (see kas-project.yml for why: it conflicts
# with meta-qt6's qtbase, and this project needs Qt6 for its own PyQt6
# apps).
#
# gnuradio_git.bb (meta-sdr) does:
#   inherit ${@bb.utils.contains('PACKAGECONFIG', 'qtgui5', ' cmake_qt5', '', d)}
# Our gnuradio_git.bbappend does `PACKAGECONFIG:remove = "qtgui5"`, but
# .bbappend variable changes are only merged into the datastore *after*
# the base recipe's own file has fully parsed -- this inline ${@...}
# expression evaluates immediately, during the base file's own parse
# pass, so it still sees the unmodified default ("qtgui5 grc zeromq")
# and always tries to inherit cmake_qt5 regardless of the bbappend:
#   ParseError ... Could not inherit file classes/cmake_qt5.bbclass
#
# A bbappend can't retroactively change what an earlier inline
# ${@...} in the base .bb already saw -- there's no ordering that
# fixes this from the bbappend side. The class only needs to exist and
# load cleanly: PACKAGECONFIG *is* correctly resolved without qtgui5
# by the time any actual task runs (DEPENDS, EXTRA_OECMAKE, etc. all
# see the final merged value), so none of cmake_qt5's real behavior
# (Qt5-specific cmake toolchain/module paths) is ever exercised in
# this build.
