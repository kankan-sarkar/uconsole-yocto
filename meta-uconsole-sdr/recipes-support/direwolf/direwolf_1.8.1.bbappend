# direwolf's scripts/CMakeLists.txt unconditionally installs three
# helper scripts alongside the main binary on non-Windows platforms
# (verified against upstream's scripts/CMakeLists.txt at this SRCREV):
#   dwespeak.sh      -- #!/bin/bash wrapper for text-to-speech alerts
#   telemetry-toolkit/telem-unit.pl   -- #!/usr/bin/perl
#   telemetry-toolkit/telem-volts.py  -- #!/usr/bin/env python3
# do_package_qa's file-rdeps check correctly flags that none of
# bash/perl/python3 are declared as runtime dependencies, so the
# scripts' shebangs would be dangling on a target image that doesn't
# happen to pull those interpreters in some other way. Declare them
# explicitly rather than suppressing the QA check -- these are genuine
# runtime requirements for scripts direwolf actually ships and are
# relevant to this project's APRS/telemetry use case.
RDEPENDS:${PN} += "bash perl python3-core"
