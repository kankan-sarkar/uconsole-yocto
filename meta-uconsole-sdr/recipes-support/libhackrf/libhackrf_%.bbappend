# meta-sdr's libhackrf_git.bb pins "git://github.com/mossmann/hackrf.git;
# branch=master", but that repo was transferred to
# github.com/greatscottgadgets/hackrf with its default branch renamed
# master -> main -- "master" doesn't exist upstream at all anymore, so
# do_fetch fails outright, no mirror can save it.
#
# The originally pinned SRCREV is still valid: verified via GitHub's
# compare API that greatscottgadgets/hackrf's 43e6f99f..main is
# "ahead_by": 1185, "behind_by": 0, i.e. the pinned commit is a genuine
# ancestor of current main. Only the URL/branch need fixing -- keep the
# same SRCREV rather than bumping ~1200 commits of unreviewed drift.
SRC_URI = "git://github.com/greatscottgadgets/hackrf.git;branch=main;protocol=https"
