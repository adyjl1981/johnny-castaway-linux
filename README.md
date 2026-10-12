<p align="center"><img src="assets/johnny-castaway.svg" width="128" alt="Johnny's island"></p>

# Johnny Castaway for Linux

Johnny's original island animations, with a settings window and optional idle playback. Install on Ubuntu, Debian, Linux Mint, Fedora, Arch/Manjaro or openSUSE. The installer detects the desktop's capabilities and offers **manual playback when automatic idle activation is unavailable**.

The animation engine is [Wilson Reborn](https://github.com/antigerme/wilson-reborn). You provide the original game data; it is not included in this repository.

## What works where?

Distro and desktop are separate choices: Fedora GNOME has the same idle interface as Ubuntu GNOME; Ubuntu KDE Wayland has different capabilities.

| Desktop/session | Manual playback | Automatic idle activation |
| --- | --- | --- |
| GNOME, Wayland or X11 | Yes | Mutter idle counter + GNOME screen shield |
| KDE Plasma, X11 | Yes | X11 idle counter + KDE locker |
| Cinnamon, MATE, XFCE, X11 | Yes | X11 idle counter + corresponding locker |
| KDE Plasma, Wayland | Yes | Manual mode; KDE does not expose this idle-time query on Wayland |
| Other Wayland desktops, including sway | Yes, where the engine can create a window | Manual mode |
| Other X11 desktops | Yes | Only if a supported locker status interface is present |
| Systems without a systemd user session | Yes | Manual mode |
| Systems without GTK/PyGObject | Yes, using `--no-gui` | Manual mode, without the settings window |

Automatic mode is enabled only after **both an idle counter and a running supported lock-status interface are verified**, with a working systemd user manager. XWayland's idle counter is never used to estimate a Wayland session's activity. Lock status is read without starting or changing any locker. Unsupported sessions show a disabled automatic checkbox and an explanation; **Start now** still works.

Desktop interfaces can vary by version and configuration. The table describes implemented behavior, not a claim that every full desktop combination has been tested. See the validation section below.

## Install

Run from your desktop session, **without sudo**. Python 3.9+ is required. Clone this project:

```sh
git clone https://github.com/adyjl1981/johnny-castaway-linux.git
cd johnny-castaway-linux
```

Print the dependency command for your distro:

```sh
./install.sh --print-deps
```

Install the prerequisites using your package manager, then install a current stable Rust toolchain using [Rust's official instructions](https://rust-lang.org/tools/install). The pinned Linux build requires Rust and Cargo **1.85.0 or newer**. Both normal installation and `--check` verify their versions before downloading data or building, and explain how to update an old toolchain. `--binary` skips the Rust checks. The installer prints commands but **does not run sudo or install system packages**.

| Family | Dependency command |
| --- | --- |
| Ubuntu, Debian, Mint, Pop!_OS, Zorin | `sudo apt install git build-essential pkg-config libasound2-dev libwayland-dev libxkbcommon-dev libx11-dev libxss1 python3-gi gir1.2-gtk-4.0` |
| Fedora | `sudo dnf install git gcc pkgconf-pkg-config alsa-lib-devel wayland-devel libxkbcommon-devel libX11-devel libXScrnSaver python3-gobject gobject-introspection gtk4 libglvnd-gles` |
| Arch, Manjaro, EndeavourOS | `sudo pacman -S --needed git base-devel pkgconf alsa-lib wayland libxkbcommon libx11 libxss python-gobject gtk4` |
| openSUSE | `sudo zypper install git gcc pkgconf-pkg-config alsa-devel wayland-devel libxkbcommon-devel libX11-devel libXss1 python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-4_0 dejavu-fonts` |

Package availability depends on release and enabled repositories. Prefer current supported releases with GTK 4. For other distros, install equivalent libraries or use the manual/no-GUI options below. Immutable systems such as Fedora Silverblue need the equivalent host package provisioning or a correctly integrated development container; the installer does not manage immutable OS layers.

Check prerequisites and the current desktop without installing:

```sh
./install.sh --check
```

Install using your original files:

```sh
./install.sh --data /path/to/original-data
# or
./install.sh --data /path/to/scrantic-run.zip
```

The data folder must contain `RESOURCE.MAP` and `RESOURCE.001`. Include `SCRANTIC.EXE` or `SCRANTIC.SCR` for original sounds; these files are read for sound extraction and **never executed**. The original installer ZIP is not supported by this wrapper.

An explicit personal-use download option uses the [Internet Archive preservation copy](https://archive.org/details/johnny-castaway-screensaver). Use it only if entitled to a copy:

```sh
./install.sh --fetch-data
```

The download is checked against a fixed SHA-256. Only recognized data entries are extracted into your application directory. Original art, data, sounds and Windows executables are excluded from Git.

The engine is built natively for the installing machine using pinned commit `2d302f56580cdcfd7a94c095e77f6bfd19f129bd` and `cargo build --release --locked -p wilson`. This avoids distributing an Ubuntu binary that might require a newer libc than another distro provides. CPU architectures beyond the tested x86_64 builds depend on upstream/compiler support and remain unverified.

## Smaller/manual installations

Use a trusted existing Wilson Reborn binary built for your distro and architecture to skip Rust and the development libraries:

```sh
./install.sh --binary /path/to/wilson --data /path/to/original-data
```

Its runtime libraries must still be installed (including ALSA for an audio-enabled build). The installer checks that the engine can load before replacing the application.

Without GTK or a systemd user session, manual playback is still available:

```sh
./install.sh --no-gui --binary /path/to/wilson --data /path/to/original-data
```

`--no-gui` can also be used with a normal source build. The application-menu entry launches playback directly. To run it from a terminal:

```sh
python3 ~/.local/share/johnny-castaway/launcher.py --play
python3 ~/.local/share/johnny-castaway/launcher.py --play --mute --windowed
```

A headless machine needs a graphical display to show the animation. There is no Flatpak, AppImage or distro package yet.

## Controls

Open **Johnny Castaway** from your application menu. Choose an idle delay from 1 to 240 minutes, select sound, and use **Save settings**. Default idle playback starts after five minutes, muted. Add `--no-enable` during installation to keep automatic playback disabled.

The GUI also exposes the engine's picture and animation options:

| Control | Choices |
| --- | --- |
| Windowed playback | Window or fullscreen |
| Animation speed | 25–400%, with 100% matching the original |
| Image scaling | Fit, stretch, whole pixel sizes (integer), or widescreen extension |
| Image filtering | Nearest, linear, xBR, or xBRZ |
| Sea/sky smoothing | On or off (off preserves original dithering) |
| Day/night | Original 8-hour cycle or real 24-hour clock |

**Save settings** persists these options for manual and automatic playback. Changes take effect on the next launch. **Start now** previews the current controls without requiring a save. Where idle playback is running, it pauses that service and restores it when manual playback ends. Press a key or click to leave the animation. The no-GUI launcher offers the same manual fullscreen playback without GTK or D-Bus.

Diagnostics:

```sh
python3 ~/.local/share/johnny-castaway/launcher.py --doctor
python3 ~/.local/share/johnny-castaway/launcher.py idle --probe
```

## Secure locking

Johnny is an animation on the **unlocked desktop**, not a password lock or a replacement for your desktop's secure lock screen. The project never changes locking, blanking or suspend settings and never calls inhibition or simulated-activity APIs.

Automatic playback stops when activity resumes, the existing locker activates, or its status checks fail. When a manual session has a supported locker status interface, it also stops on locking or interface failure. When no status interface is available (including the no-GUI launcher), manual playback is an ordinary fullscreen app: the desktop's own secure lock screen covers it, and the app may keep running behind it. Keep your normal secure locker enabled.

If your desktop blanks or locks before Johnny's selected delay, you will not see automatic playback. You can select a shorter Johnny delay without changing secure locking. Fullscreen playback uses the engine's selected display; this integration does not implement multi-monitor coverage.

## Files and removal

Standard paths (XDG overrides are respected):

| Item | Path |
| --- | --- |
| Application, engine and local game data | `~/.local/share/johnny-castaway/` |
| Settings | `~/.config/johnny-castaway/settings.json` |
| Optional idle service | `~/.config/systemd/user/johnny-castaway-idle.service` |
| Engine configuration and story progress | `~/.local/state/wilson-reborn/` |

Before each launch, the integration synchronizes its managed options to the engine configuration, including turning booleans off; unrelated intro, story and other engine settings are preserved. Existing delay/mute settings migrate automatically to the expanded settings format.

Moving or deleting the checkout after installation does not affect playback. Reinstalling replaces the app/data and preserves your saved delay and sound preference. Installing on a session without idle support disables automatic activation; it can be enabled from the GUI later in a supported session.

On systems with a user service manager:

```sh
systemctl --user status johnny-castaway-idle.service
journalctl --user -u johnny-castaway-idle.service
systemctl --user disable --now johnny-castaway-idle.service
```

Run `./uninstall.sh` to remove idle activation and the menu shortcut. It preserves local data, settings and story progress, and works when systemctl is absent.

## Development and validation

```sh
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q johnny_castaway install.py launcher.py
```

[Linux compatibility CI](https://github.com/adyjl1981/johnny-castaway-linux/actions) checks Ubuntu 24.04, Debian stable, Fedora, Arch and openSUSE Tumbleweed containers. Each job installs the documented libraries, runs the wrapper tests, opens the GTK fallback window under Xvfb, queries a real X11 idle counter, and builds/runs the pinned engine. Ubuntu checks the minimum Rust 1.85.0 toolchain; the other jobs use current stable Rust. No copyrighted data is used in CI.

Live Ubuntu 26.04.1 / GNOME 50.1 / Wayland testing verified original animation frames, all 23 sounds, audio cues, automatic activation, GUI settings and manual playback. The upstream engine/data tests passed (123 tests, one ignored). Wrapper tests cover desktop selection, lock precedence, activity exit, safe failure, XWayland rejection, native/manual fallbacks, distro detection and safe archive extraction.

Container tests verify packages, buildability and isolated GUI/X11 behavior. They do **not** boot full KDE, Cinnamon, MATE or XFCE sessions, verify their password-lock/unlock cycles, or test other CPU architectures. Those need community/interactive testing. Please report your distro, desktop, session type and `--doctor` output when filing compatibility issues.

## Credits and license

- Original Johnny Castaway: Sierra/Dynamix (1992). Their original game data remains copyrighted and is not redistributed here.
- Engine: [Wilson Reborn](https://github.com/antigerme/wilson-reborn), GPL-3.0-or-later. Its source and license remain upstream; this repository contains the integration rather than a copy of the engine.
- This project's code and newly drawn SVG island illustration: MIT license.

The [KDE locker implementation](https://github.com/KDE/kscreenlocker/blob/master/interface.cpp) explicitly rejects its idle-time query on Wayland. Locker interfaces are based on [Cinnamon](https://github.com/linuxmint/cinnamon-screensaver/blob/master/libcscreensaver/org.cinnamon.ScreenSaver.xml), [XFCE](https://github.com/xfce-mirror/xfce4-screensaver/blob/master/src/gs-listener-dbus.c), [MATE](https://github.com/mate-desktop/mate-screensaver/blob/master/src/gs-listener-dbus.c), and GNOME's read-only screen-shield/idle APIs.

This is an independent fan integration, not affiliated with Sierra, Dynamix or the engine maintainers. Source review and pinned dependencies are not a complete security audit.
