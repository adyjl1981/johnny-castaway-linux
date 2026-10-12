#!/bin/sh
# For isolated CI containers only. Installs dependencies as the container's root.
set -eu
. /etc/os-release
case "$ID" in
  ubuntu|debian)
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends git build-essential pkg-config libasound2-dev libwayland-dev libxkbcommon-dev libx11-dev libxss1 python3-gi gir1.2-gtk-4.0 xvfb dbus-x11 xauth curl ca-certificates
    ;;
  fedora)
    dnf install -y --setopt=install_weak_deps=False git gcc pkgconf-pkg-config alsa-lib-devel wayland-devel libxkbcommon-devel libX11-devel libXScrnSaver python3-gobject gtk4 xorg-x11-server-Xvfb dbus-daemon xauth curl-minimal ca-certificates
    ;;
  arch)
    pacman -Syu --noconfirm --needed git base-devel pkgconf alsa-lib wayland libxkbcommon libx11 libxss python-gobject gtk4 xorg-server-xvfb dbus xorg-xauth curl ca-certificates
    ;;
  opensuse-tumbleweed|opensuse-leap)
    zypper --non-interactive refresh
    zypper --non-interactive install --no-recommends git gcc pkgconf-pkg-config alsa-devel wayland-devel libxkbcommon-devel libX11-devel libXss1 python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-4_0 xorg-x11-server-Xvfb dbus-1 xauth curl ca-certificates
    ;;
  *) echo "No CI package list for $ID" >&2; exit 1 ;;
esac
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q johnny_castaway install.py launcher.py
sh -n install.sh uninstall.sh
pkg-config --exists alsa wayland-client xkbcommon x11
/usr/bin/python3 install.py --print-deps
Xvfb :99 -screen 0 800x600x24 -nolisten tcp >/tmp/johnny-xvfb.log 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
export DISPLAY=:99 GDK_BACKEND=x11 GSK_RENDERER=cairo
count=0
while [ ! -S /tmp/.X11-unix/X99 ]; do
    count=$((count + 1))
    if [ "$count" -gt 10 ]; then cat /tmp/johnny-xvfb.log; exit 1; fi
    sleep 1
done
dbus-run-session /usr/bin/python3 scripts/smoke-desktop.py
if [ "${BUILD_ENGINE:-0}" = 1 ]; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o /tmp/johnny-rustup.sh
    sh /tmp/johnny-rustup.sh -y --profile minimal
    export PATH="$HOME/.cargo/bin:$PATH"
    git clone https://github.com/antigerme/wilson-reborn.git /tmp/wilson-reborn
    git -C /tmp/wilson-reborn checkout --detach 2d302f56580cdcfd7a94c095e77f6bfd19f129bd
    cargo build --manifest-path /tmp/wilson-reborn/Cargo.toml --release --locked -p wilson
    /tmp/wilson-reborn/target/release/wilson --help
fi
