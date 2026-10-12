"""Dependency guidance; never execute package-manager commands automatically."""
import shlex
from pathlib import Path

PACKAGES = {
    'debian': 'sudo apt install git build-essential pkg-config libasound2-dev libwayland-dev libxkbcommon-dev libx11-dev libxss1 python3-gi gir1.2-gtk-4.0',
    'fedora': 'sudo dnf install git gcc pkgconf-pkg-config alsa-lib-devel wayland-devel libxkbcommon-devel libX11-devel libXScrnSaver python3-gobject gobject-introspection gtk4 libglvnd-gles',
    'arch': 'sudo pacman -S --needed git base-devel pkgconf alsa-lib wayland libxkbcommon libx11 libxss python-gobject gtk4',
    'suse': 'sudo zypper install git gcc pkgconf-pkg-config alsa-devel wayland-devel libxkbcommon-devel libX11-devel libXss1 python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-4_0 dejavu-fonts',
}

def read_release(path=Path('/etc/os-release')):
    result = {}
    try:
        for line in path.read_text().splitlines():
            if '=' not in line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            parts = shlex.split(value)
            result[key] = ' '.join(parts)
    except (OSError, ValueError):
        pass
    return result

def family(release):
    for token in (release.get('ID', '') + ' ' + release.get('ID_LIKE', '')).split():
        if token in ('debian', 'ubuntu', 'linuxmint', 'pop', 'zorin'):
            return 'debian'
        if token in ('fedora', 'rhel', 'centos', 'rocky', 'almalinux'):
            return 'fedora'
        if token in ('arch', 'manjaro', 'endeavouros'):
            return 'arch'
        if token in ('suse', 'opensuse', 'opensuse-tumbleweed', 'opensuse-leap'):
            return 'suse'
    return None

def guidance(release=None):
    release = read_release() if release is None else release
    command = PACKAGES.get(family(release))
    if command:
        return command + '\nAlso install a current stable Rust toolchain: https://rust-lang.org/tools/install'
    return ('Install Python 3.9+, PyGObject/GTK 4, git, a C compiler, pkg-config, ALSA/Wayland/'
            'X11/xkbcommon development libraries, and a current stable Rust toolchain. '
            'Package names vary; --binary and --no-gui can reduce prerequisites.')
