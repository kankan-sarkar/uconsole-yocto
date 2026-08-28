# Security & Responsible Use

This is a personal/community hobby project, not a commercially supported
product. There's no dedicated security team and no SLA. Read this before you
build or, especially, deploy the resulting image anywhere that matters.

## This image includes dual-use RF/security tooling

`packagegroup-uconsole-security` and the `meta-rtlwifi` layer pull in:

- **aircrack-ng** — Wi-Fi security auditing suite.
- **rtl8812au** — an out-of-tree driver enabling monitor mode / packet
  injection on the AC1200 USB Wi-Fi dongle.

These are legitimate, widely-published open-source tools — the same ones
behind DragonOS, Kali, and similar distros. **Only use them against networks,
devices, and RF spectrum you own or have explicit written authorization to
test.** Unauthorized use can violate computer-crime law (e.g. the US CFAA) and
radio-transmission regulations (e.g. FCC Part 15) in your jurisdiction. You
are solely responsible for how you use this build.

## Local auth model — read this before you rely on it

- The **PIN set during first boot is the account password**, full stop. The
  OOBE wizard syncs it into `/etc/shadow` for `root` via `chpasswd`,
  specifically so unmodified `sudo`/PAM prompts *are* the PIN prompt. There is
  no separate "sudo password" hiding behind it.
- **If you lose the PIN, you lose local administration, permanently**, by
  design (see [requirement.md §7](requirement.md#7-security--access-control)).
  There's no recovery path built into this image short of reflashing.
- `pam_faillock` (see the `libpam` bbappend) gives a **fixed-delay** lockout
  on the PAM path (sudo, login, SSH password auth). **True exponential
  backoff only exists in the custom Qt lock screen** (`uconsole-lock.py`) —
  brute-force protection on SSH/sudo is weaker than on the on-screen lock.
- SSH (`openssh`) is enabled by default via the `ssh-server-openssh` image
  feature. Change the password (i.e. the PIN) from whatever you set at first
  boot before exposing this to any untrusted network, and consider key-only
  auth for field deployments.
- There is no secure boot, disk encryption, or signed-image verification.
  Anyone with physical access to the SD card or NVMe drive can read or modify
  the rootfs offline. Treat physical possession of the device as equivalent
  to root access.

## Reporting an issue

Please open a GitHub issue. For anything that could let someone remotely
compromise other people's already-deployed devices, a brief heads-up in the
issue without a full exploit write-up is appreciated while a fix lands —
otherwise, normal public issues are fine; this project doesn't have the
infrastructure for a formal private disclosure process.

## License disclaimer

This project is provided **as-is, with no warranty of any kind** — see
[LICENSE](LICENSE). That disclaimer applies in full to the security posture
described above.
