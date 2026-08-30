# aircrack-ng's lib/osdep/linux.c independently #includes
# radiotap/radiotap.h -- the same header that's also compiled
# separately into libradiotap.a -- without whatever earlier header is
# meant to have the `__packed` macro (__attribute__((packed))) already
# in scope in that translation unit. radiotap.h's struct then closes
# with `} __packed;`, which without the macro defined parses as an
# accidental global tentative variable declaration (an
# anonymous-struct-typed identifier literally named __packed) instead
# of a packed-attribute struct. Since radiotap.h gets compiled
# separately into both libradiotap.a's own object and linux.o, each
# produces its own instance of that accidental global.
#
# GCC 10+ defaults to -fno-common, which correctly refuses to silently
# merge duplicate tentative definitions the way older GCC did,
# surfacing this at link time:
#
#   multiple definition of `__packed'; ... first defined here
#
# -fcommon restores the old linker tolerance (harmless here -- both
# instances are always-zero-initialized and never actually used as a
# real variable) without needing to patch upstream's header ordering.
CFLAGS:append = " -fcommon"
