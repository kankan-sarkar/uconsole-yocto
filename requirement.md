# Yocto Build Requirements: uConsole CM4 Field Operations & SDR Rig

## 1. Hardware Requirements
### 1.1 Host Machine (Build Server)
Yocto builds are resource-intensive. Your local development machine must meet the following:
* **OS:** Ubuntu 22.04 LTS or Debian 12 (native or WSL2).
* **CPU:** Multi-core processor (8+ cores recommended for faster BitBake execution).
* **RAM:** Minimum 16GB (32GB+ highly recommended).
* **Storage:** At least 250GB of free SSD space (Yocto artifacts and sstate-cache grow quickly).
* **Network:** High-speed internet for downloading source tarballs and git repositories.

### 1.2 Target Hardware
* **Core:** ClockworkPi uConsole with Raspberry Pi Compute Module 4 (CM4 Wi-Fi Lite, 4GB RAM).
* **Storage:** NVMe SSD installed via CM4 adapter (for OS boot and high-speed data logging).
* **Expansion:** Hacker Gadgets AIO v2 board.
* **Peripherals:** 
  * AC1200 USB Wi-Fi dongle.
  * USB-to-Ethernet adapter.
  * Appropriate antennas for RTL-SDR and LoRa operation.

---

## 2. Recreating the Build Process (Host Environment)
To rebuild this custom OS from scratch, a headless Linux host (Debian/Ubuntu 22.04+) is required. Due to the intensive nature of cross-compiling the Linux kernel and Qt6, the host should ideally have 16GB+ RAM. If using an 8GB machine (e.g. Intel N100), you **must** restrict thread counts to prevent Out-Of-Memory (OOM) crashes.

### 2.1 Install Dependencies
Install the required host dependencies to compile cross-toolchains, kernels, and C/C++ applications:
```bash
sudo apt-get update
sudo apt-get install gawk wget git diffstat unzip texinfo gcc \
build-essential chrpath socat cpio python3 python3-pip python3-pexpect \
xz-utils debianutils iputils-ping python3-git python3-jinja2 libegl-dev libsdl2-dev \
pylint xterm python3-subunit mesa-common-dev zstd liblz4-tool locales
```

### 2.2 Configure Locales & AppArmor (Crucial for Ubuntu 24.04+)
Yocto's `bitbake` parser strictly requires an English UTF-8 locale.
```bash
sudo locale-gen en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```
Furthermore, on Ubuntu 24.04, AppArmor heavily restricts user namespaces which instantly crashes BitBake. You must temporarily disable this restriction before building:
```bash
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
```

### 2.3 Install Kas and Build
We use `kas` instead of traditional repo manifests to automatically fetch and configure all Yocto layers based on the `kas-project.yml` file.
```bash
# Install Kas
sudo pip3 install kas

# (Optional) If on a low RAM machine (8GB), edit kas-project.yml 
# and restrict BB_NUMBER_THREADS and PARALLEL_MAKE to "2".

# Run the build inside a multiplexer so SSH disconnects don't kill it
tmux
kas build kas-project.yml
```

---

## 3. Yocto Layer Architecture
The build requires the Poky reference distribution and several community layers to support the CM4, networking, and Python/GUI stacks. 

* **Base & Core:**
  * `poky` (The core Yocto build system).
  * `meta-openembedded` (Provides `meta-oe`, `meta-python`, `meta-networking`).
  * `meta-sdr` (Provides GNU Radio, RTL-SDR, GQRX, and other SDR dependencies).
  * `meta-security` (Provides Kali-style penetration testing and security auditing tools).
  * `meta-qt6` (Required for Qt-based SDR UI applications like SDRangel or GQRX).
* **Hardware Support (BSP):**
  * `meta-raspberrypi` (CM4 kernel, bootfiles, and VC4 graphics drivers).
* **Custom Meta Layer (`meta-uconsole-field`):**
  * Contains the `uconsole-cm4.conf` machine definition.
  * Holds custom `.bbappend` files for the `config.txt` display and PCIe overrides.
  * Includes the AIO v2 power management daemon (`evdev` -> `gpiod` keypress scripts).

---

## 4. Target System Configuration

### 4.1 Storage & Boot
* **Init System:** The image must use `systemd` as the init manager (rather than sysvinit) to allow aggressive parallelization of boot services and faster startup times.
* **Boot Sequence (SD & NVMe):** The CM4 EEPROM must be flashed separately via `usbboot` to prioritize SD Card first, then NVMe PCIe booting (`BOOT_ORDER=0xf461` where `1` is SD and `6` is NVMe). This allows initial development and testing on an SD card, while easily transitioning to the SSD later.
* **Universal Image Format:** The Yocto build must generate a `.wic` image with a GPT partition table, a VFAT boot partition, and an EXT4 root filesystem suitable for `dd` flashing directly to *either* an SD card (`/dev/mmcblk0`) or the NVMe drive (`/dev/nvme0n1`). By compiling both the SD (MMC) and NVMe drivers directly into the kernel, we skip `initramfs` entirely to shave seconds off the boot time regardless of the storage medium used.

### 4.2 Power & Hardware Integration
* **GPIO Power Rails:** The Hacker Gadgets AIO v2 requires explicit activation:
  * **GPIO 23:** Toggles the internal USB hub / SDR module.
  * **GPIO 27:** Toggles the GPS module.
* **RTC Support:** The AIO v2 board includes a battery-backed Real Time Clock (RTC). The I2C RTC driver (e.g., `ds1307` or `ds3231` depending on the exact chip) must be enabled in the kernel, with `hwclock` synced during boot.
* **Hotkey Daemon:** A custom Python daemon using `python-evdev` running as a `systemd` background service to intercept keyboard matrix combinations and toggle GPIO states dynamically without rebooting.
* **Battery Management (BMS):** I2C driver integration for the uConsole's PMIC (e.g., AXP228/AXP221) to expose battery level and charging status to the OS and Wayland compositor.

### 4.3 Networking
* **USB Ethernet:** Native kernel driver inclusion (`kernel-module-asix`, `usbnet`).
* **AC1200 Wi-Fi:** Integration of out-of-tree RTL8812AU drivers via DKMS or Yocto kernel module recipes for monitor mode and packet injection.
* **Network Management:** `NetworkManager` included for easy UI/CLI toggling of interfaces.

### 4.4 Audio Subsystem (For FM/Voice Demodulation)
* **Audio Server:** `pipewire` or `pulseaudio` alongside `alsa-utils` must be included and configured to route demodulated analog audio (e.g., from FM radio or HAM voice) directly to the uConsole's built-in speakers or headphone jack.

---

## 5. Software & Tooling Stack

### 5.1 RF & SDR (Native Kali/DragonOS-style Tools)
Cross-compile and include the following for wireless monitoring, heavily inspired by DragonOS:
* **Hardware Abstraction:** `SoapySDR` framework and associated modules (`soapy-rtlsdr`, `soapy-hackrf`) to allow maximum compatibility across different SDR hardware.
* **Core SDR Tools:**
  * `rtl-sdr` & `hackrf` base libraries and CLI tools.
  * `sdrangel`, `gqrx`, `CubicSDR`, or `SDR++` (Optimized SDR interfaces for local RF visualization).
  * `gnuradio` (Headless/CLI flowgraphs recommended to avoid GUI bloat on the CM4).
* **Signal Analysis & Hacking:**
  * `aircrack-ng` suite (for AC1200 Wi-Fi analysis).
  * `kismet` (for headless or lightweight UI RF environment mapping).
  * `urh` (Universal Radio Hacker for IoT/LoRa protocol reversing).
  * `inspectrum` or `sigDigger` (for offline signal analysis and demodulation).
* **Decoding & Protocol Specific:**
  * `rtl_433` (For common ISM band radio protocol demodulation like weather stations, TPMS, and IoT sensors).
  * `rtl_fm` and `sox` (For lightweight, CLI-based FM/AM audio demodulation piped directly to the audio subsystem).
  * `multimon-ng` (For demodulating digital transmissions like POCSAG pagers, AFSK, and ZVEI).
  * `direwolf` (For HAM radio APRS / Packet Radio soundcard decoding).
  * `wsjtx`, `fldigi`, and `JS8Call` (For weak signal HAM radio decoding, FT8, WSPR, RTTY, etc.).
  * `QSSTV` (For decoding Slow Scan TV images).
  * `Satdump` (For downloading and decoding weather satellite imagery like NOAA/Meteor).
  * `SDRTrunk` (For decoding trunked radio systems like P25).
  * `dump1090` (For ADS-B aircraft tracking with the RTL-SDR).
  * `wireshark` / `tshark` (For deep packet inspection of captured RF network traffic).
  * `gpsd` and `gps-utils` (includes `xgps` and `xgpspeed`). **Note:** `gpsd` must be configured at the system level (via a `systemd` service) to permanently bind to `/dev/ttyS0`. GUI tools like `xgps` will then connect automatically to `localhost:2947` without needing manual port selection.

### 5.2 Python Development Environment
To support custom data gathering scripts and future hardware interfaces:
* `python3-core`, `python3-pip`.
* `python3-numpy`, `python3-scipy` (for local signal processing).
* `python3-paho-mqtt` (for custom IoT bridging scripts).
* `python3-pyqt6` or `PySide6` (for building portable UI tools).

### 5.3 UI & Gaming
Optimized for the uConsole's 1280x480 ultrawide screen:
* **Compositor:** Weston (Wayland) configured with a minimalist tiled layout to maximize screen real estate.
* **Custom Control Panel (Power/Performance):** A custom, lightweight PyQt6/PySide6 dashboard that can be summoned instantly via a dedicated hardware hotkey. This panel must expose toggles for:
  * CPU Governor switching (e.g., toggling between 'Power Save' and 'Performance' modes).
  * GPIO toggles (turning off the SDR/GPS modules when not in use).
  * Display brightness and Wi-Fi/Bluetooth state management.
* **Gaming:** SDL2 libraries included to natively support lightweight C/C++ retro ports (like `doomgeneric`) and Python `pygame` scripts.

### 5.4 Remote Access & Field Operations
* **SSH Server:** `openssh` or `dropbear` enabled by default for remote access via the USB-to-Ethernet or Wi-Fi interface.
* **VNC/RDP:** `wayvnc` (Wayland VNC server) for remote UI visualization (useful for headless SDR monitoring from a laptop).
* **Terminal Multiplexing:** `tmux` or `screen` to keep RF monitoring sessions alive during unstable field network connections.

### 5.5 System Telemetry & Profiling
Given the 4GB RAM constraint, close monitoring of SDR tool memory usage is critical.
* **Process Profiling:** Include packages like `htop`, `iotop`, and `sysstat` (provides `pidstat`, `iostat`) to profile individual process resource and I/O usage.
* **Telemetry Daemon:** Include a lightweight telemetry agent (e.g., `telegraf` or `netdata` in low-resource mode) to log system health, thermal thresholds, and per-process memory footprints over time to the NVMe for offline analysis.

### 5.6 IoT & Local Web Services
* **MQTT Broker & Client:** Include `mosquitto` and `mosquitto-clients` to serve as a local message bus for telemetry and radio data.
* **MQTT GUI Dashboard:** Since the CM4 has 4GB RAM, a lightweight web-based GUI like **MQTTX Web** is highly recommended. It can be hosted locally via Nginx to visualize and publish/subscribe to MQTT topics directly from the uConsole screen or a connected laptop. (Alternatively, a native tool like **MQTT Explorer** can be included if an AppImage/binary is preferred).
* **LoRa <-> MQTT Bridging:** Support for bi-directional messaging between the AIO v2 LoRa module and the local MQTT broker. This will be facilitated by custom Python daemon scripts using `paho-mqtt` and `python3-serial`.
* **Local Web Server:** Include `nginx` (recommended for lower memory footprint) or `apache2` for hosting local web dashboards, serving captured SDR files over the network, and providing a local deployment interface in the field.

---

## 6. Boot Optimization & Energy Efficiency
To ensure the OS boots incredibly fast and preserves the uConsole's battery during long field deployments, the Yocto image must be tuned with the following constraints:
* **Kernel Tuning:** Strip the Linux kernel of unused drivers (e.g., legacy soundcards, unnecessary USB peripherals, redundant file systems) to reduce memory footprint and load times.
* **CPU Frequency Scaling:** Include `cpufrequtils` to dynamically scale the CM4's CPU governor. Default the governor to `ondemand` or `conservative` to save power, rather than `performance`.
* **Service Masking:** Disable unnecessary `systemd` services. Only launch the Weston compositor, NetworkManager, and MQTT/Telemetry daemons at boot. SDR GUIs should only be launched on-demand by the user.
* **Hardware Power-Down:** Disable unused hardware interfaces via `/boot/config.txt` (e.g., disable Bluetooth if not used, turn off the CM4 ACT/PWR LEDs, and disable HDMI outputs since the uConsole uses a DSI display).
* **Boot Profiling:** Use `systemd-analyze blame` during the development phase to profile and eliminate any boot bottlenecks.

---

## 7. Security & Access Control
Given the sensitive nature of field operations, the OS requires a strict, custom security model built around a local PIN system and a separate remote access credential.

* **First-Boot PIN Initialization:** On the very first boot, a setup wizard will prompt the user to establish a local PIN (minimum 5 digits). This PIN becomes the ultimate local root authority. **Warning:** If this PIN is lost, local administration is permanently locked out.
* **Local Privilege Escalation (Sudo):** Any major local changes—such as modifying hardware states, terminating critical services, or changing OS configurations—will prompt for this PIN instead of a standard password.
* **Exponential Backoff:** To prevent brute-force attacks on the local device, entering an incorrect PIN will trigger an exponential time delay before the next attempt is permitted.
* **Separate SSH Credentials:** To allow flexible remote administration without compromising local UI security, SSH access will use a separate password (or SSH keys) distinct from the local PIN. This dual-system approach ensures ease of use for remote operators.
* **Screen Timeout & Secure Lock Screen:**
  * **Configurable Timeout:** The user can configure an idle timeout after which the uConsole's DSI display and backlight completely power off to save battery.
  * **Background Persistence:** All background daemons (SDR logging, MQTT, Telemetry, etc.) will continue running seamlessly while the screen is off.
  * **Wake & Authenticate:** Pressing any key wakes the display and presents a highly customized, aesthetically pleasing lock screen.
  * **Obfuscated Input:** When entering the PIN on the lock screen, the input field will not reveal the character count (e.g., it will not show one asterisk per digit). This prevents shoulder-surfers from guessing the length of the PIN. The user can see the digits they are currently typing, but the UI will obfuscate the total count.

---

## 8. First-Boot Customization Wizard (OOBE)
To provide a premium out-of-the-box experience (OOBE), the OS will launch a comprehensive PyQt/PySide-based wizard on the very first boot. This tool will require the user to connect to a network to download aesthetic assets and configure their personal workspace.

The Customization Wizard must allow the user to configure the following:
* **Identity & Security:**
  * Set the primary 5-digit local security PIN.
  * Upload or select a custom User Profile Image (displayed on the lock screen).
* **Boot Aesthetics:**
  * Select or upload a custom-sized Splash Screen image (via `plymouth` integration) that displays during the kernel boot sequence before Wayland loads.
* **UI & Theme Customization:**
  * Select system-wide dark/light themes and accent colors for the Weston compositor and Qt applications.
  * Configure the UI layout (e.g., toggling between floating windows or a strict tiled layout for SDR software).
* **Application Defaults & Gaming:**
  * Select which SDR application opens by default when the hardware hotkey is pressed (e.g., SDRangel vs. GQRX).
  * Configure retro gaming directories (linking the ROMs folder for `doomgeneric` or `pygame` scripts).
* **Networking & Telemetry:**
  * Connect to local Wi-Fi via NetworkManager.
  * (Optional) Input remote MQTT broker credentials if bridging local telemetry to an external server.