<p align="center"><img src="assets/johnny-castaway.svg" width="128" alt="Johnny's island"></p>

# Johnny Castaway for Ubuntu

Bring Johnny's tiny island back to your GNOME desktop, with a settings window and automatic idle playback. This project installs and controls [Wilson Reborn](https://github.com/antigerme/wilson-reborn), which plays the original Johnny Castaway animations and sound using your local game data.

## Features

- GTK 4 settings window: choose a delay from 1 to 240 minutes, toggle automatic playback and mute sound.
- **Start now** for manual fullscreen playback. Press a key or click to return.
- Five-minute idle delay and muted audio by default.
- Playback stops when activity resumes or GNOME's screen shield activates.
- Per-user installation, original island icon, and no changes to screen-lock settings.

## GNOME Wayland and secure locking

Johnny is an animation on your **unlocked desktop**, not a password lock or a replacement for GNOME's lock screen. GNOME owns the secure screen shield and will cover the animation when it locks. The helper also stops playback when the shield is active or its lock/idle checks fail. It never inhibits locking, blanking, or suspend.

If GNOME blanks or locks before the selected Johnny delay, you will not see idle playback. Choose a Johnny delay shorter than your existing blanking time if desired; keep secure locking enabled. The installer preserves all existing GNOME security settings, including settings that are already disabled.

This integration targets GNOME with `org.gnome.Mutter.IdleMonitor` and `org.gnome.ScreenSaver` available on the session bus. It is not an XScreenSaver module and does not promise support for KDE, sway or other desktops. Fullscreen playback uses the primary display; multi-monitor coverage is not implemented here.

## Install

Run from your GNOME desktop session, **without sudo**. Install system prerequisites separately:

```sh
sudo apt install git build-essential pkg-config libasound2-dev libwayland-dev libxkbcommon-dev libx11-dev python3-gi gir1.2-gtk-4.0
```

Install a current stable Rust toolchain using [Rust's official instructions](https://www.rust-lang.org/tools/install), then:

```sh
git clone https://github.com/adyjl1981/johnny-castaway-ubuntu.git
cd johnny-castaway-ubuntu
./install.sh --data /path/to/original-data
```

The data folder must contain `RESOURCE.MAP` and `RESOURCE.001`. Include `SCRANTIC.EXE` or `SCRANTIC.SCR` for the original sounds; these files are read for sound extraction and **never executed**. You may also pass `--data /path/to/scrantic-run.zip`. The original installer ZIP is not supported by this wrapper.

An explicit personal-use download option uses the [Internet Archive preservation copy](https://archive.org/details/johnny-castaway-screensaver). Use it only if you are entitled to a copy:

```sh
./install.sh --fetch-data
```

Downloads are checked against a fixed SHA-256 before use. Only recognized data entries are extracted, into the user's application directory. Original art, data, sounds and Windows executables are excluded from this repository.

The installer builds Wilson Reborn from pinned commit `2d302f56580cdcfd7a94c095e77f6bfd19f129bd` with `cargo build --release --locked -p wilson`. It does not execute upstream installation scripts. To use a trusted existing build:

```sh
./install.sh --binary /path/to/wilson --data /path/to/original-data
```

Add `--no-enable` to install without automatic idle activation. Then open **Johnny Castaway** in your application menu.

## Settings and files

The GUI's **Save settings** applies the delay, sound preference, and automatic-playback checkbox. **Start now** uses the current sound checkbox and temporarily pauses idle activation, restoring it when manual playback ends. Manual playback stops if GNOME locks or its lock interface becomes unavailable.

Standard paths (XDG overrides are respected):

| Item | Path |
| --- | --- |
| Application, engine and local game data | `~/.local/share/johnny-castaway/` |
| Settings | `~/.config/johnny-castaway/settings.json` |
| Idle service | `~/.config/systemd/user/johnny-castaway-idle.service` |
| Engine story progress | `~/.local/state/wilson-reborn/` |

Once installed, moving or deleting this checkout does not affect playback. Reinstalling replaces the application and data while preserving settings.

```sh
systemctl --user status johnny-castaway-idle.service
journalctl --user -u johnny-castaway-idle.service
systemctl --user disable --now johnny-castaway-idle.service
```

Run `./uninstall.sh` to remove idle activation and the menu shortcut. It preserves your local data, settings and story progress.

## Development and validation

```sh
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q johnny_castaway install.py launcher.py
```

The initial installation was tested on Ubuntu 26.04.1 LTS, GNOME 50.1, Wayland: original animations rendered, all 23 sounds loaded, audio cues played, and idle playback launched. Engine/data tests passed (123 tests, one ignored). The installed GTK window was also tested: saving/restoring the delay, starting and stopping manual fullscreen playback, and restoring the idle service all worked. Wrapper tests cover lock precedence, activity exit, safe failure, rearming, and archive extraction. Lock behavior is tested with simulated states; a real password-lock/unlock cycle still needs an interactive user check.

## Credits and license

- Original Johnny Castaway: Sierra/Dynamix (1992). Their original game data remains copyrighted and is not redistributed here.
- Animation engine: [Wilson Reborn](https://github.com/antigerme/wilson-reborn), GPL-3.0-or-later. Its source and license remain available upstream. This repository contains the Python integration, installer and original SVG icon, not a copy of that engine.
- This project's code and SVG island illustration: MIT license. The illustration is newly drawn and is not extracted game artwork.

This project is an independent fan integration, not affiliated with Sierra, Dynamix or Wilson Reborn's maintainers. Source review and pinned dependencies reduce uncertainty but are not a complete security audit.
