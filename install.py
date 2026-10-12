#!/usr/bin/python3
"""Install into XDG user directories; original data is always kept local."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
UPSTREAM = 'https://github.com/antigerme/wilson-reborn.git'
REVISION = '2d302f56580cdcfd7a94c095e77f6bfd19f129bd'
DATA_URL = 'https://archive.org/download/johnny-castaway-screensaver/scrantic-run.zip'
DATA_SHA256 = '111c384aa44fc810c0453f524d8c02dee58ea3358ee788316b2fc1f2059afc56'
NAMES = ('RESOURCE.MAP', 'RESOURCE.001', 'SCRANTIC.EXE', 'SCRANTIC.SCR')

def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)

def copy_data(source, destination):
    """Copy only recognized data entries; never extract archive paths."""
    destination.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        files = {p.name.upper(): p for p in source.iterdir() if p.is_file()}
        for required in NAMES[:2]:
            if required not in files:
                raise ValueError('Missing ' + required)
        for name in NAMES:
            if name in files:
                shutil.copyfile(files[name], destination / name)
    else:
        with zipfile.ZipFile(source) as archive:
            files = {Path(n).name.upper(): n for n in archive.namelist()}
            for required in NAMES[:2]:
                if required not in files:
                    raise ValueError('Use an extracted data folder or scrantic-run.zip (not the installer ZIP).')
            for name in NAMES:
                if name in files:
                    info = archive.getinfo(files[name])
                    if info.file_size > 20_000_000:
                        raise ValueError('Unexpectedly large data entry')
                    (destination / name).write_bytes(archive.read(info))

def quoted(value, percent=False):
    value = str(value)
    if '\n' in value or '\r' in value:
        raise ValueError('Installation paths cannot contain newlines')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
    if percent:
        value = value.replace('%', '%%')
    return '"' + value + '"'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data = parser.add_mutually_exclusive_group(required=True)
    data.add_argument('--data', type=Path, help='Original RESOURCE files folder or scrantic-run.zip')
    data.add_argument('--fetch-data', action='store_true', help='Download verified Internet Archive data for personal use; use only if entitled to a copy')
    parser.add_argument('--binary', type=Path, help='Use an existing trusted Wilson Reborn binary instead of building')
    parser.add_argument('--no-enable', action='store_true', help='Install without starting automatic idle playback')
    args = parser.parse_args()
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk  # confirm GUI dependency before changes
    share = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')).resolve()
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')).resolve()
    app = share / 'johnny-castaway'
    with tempfile.TemporaryDirectory(prefix='johnny-install-') as temporary:
        stage = Path(temporary)
        source = args.data.resolve() if args.data else stage / 'scrantic-run.zip'
        if args.fetch_data:
            print('Downloading original data for personal use; it will not be included in Git or redistributed.')
            with urllib.request.urlopen(DATA_URL, timeout=120) as response:
                source.write_bytes(response.read(5_000_001))
            if hashlib.sha256(source.read_bytes()).hexdigest() != DATA_SHA256:
                raise ValueError('Original data checksum mismatch; refusing installation')
        copy_data(source, stage / 'data')
        if args.binary:
            binary = args.binary.resolve()
            if not binary.is_file() or not os.access(binary, os.X_OK):
                raise ValueError('Binary must be an executable file')
        else:
            for tool in ('git', 'cargo', 'cc', 'pkg-config'):
                if shutil.which(tool) is None:
                    raise RuntimeError('Missing ' + tool + '; see README prerequisites')
            run('pkg-config', '--exists', 'alsa', 'wayland-client', 'xkbcommon', 'x11')
            build = ROOT / 'build' / 'wilson-reborn'
            if not build.exists():
                build.parent.mkdir(parents=True, exist_ok=True)
                run('git', 'clone', UPSTREAM, str(build))
            else:
                remote = subprocess.check_output(['git', '-C', str(build), 'remote', 'get-url', 'origin'], text=True).strip()
                if remote != UPSTREAM:
                    raise ValueError('Unexpected upstream build directory remote')
                dirty = subprocess.check_output(['git', '-C', str(build), 'status', '--porcelain'], text=True)
                if dirty:
                    raise ValueError('Build checkout has local changes; preserve them and move it aside before installing')
            run('git', '-C', str(build), 'checkout', '--detach', REVISION)
            actual = subprocess.check_output(['git', '-C', str(build), 'rev-parse', 'HEAD'], text=True).strip()
            if actual != REVISION:
                raise ValueError('Upstream revision mismatch')
            run('cargo', 'build', '--release', '--locked', '-p', 'wilson', cwd=build)
            binary = build / 'target/release/wilson'
        # Everything needed is staged before stopping/replacing the existing install.
        app.mkdir(parents=True, exist_ok=True)
        subprocess.run(['systemctl', '--user', 'stop', 'johnny-castaway-idle.service'], capture_output=True)
        for name in ('johnny_castaway', 'assets'):
            shutil.copytree(ROOT / name, app / name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(ROOT / 'launcher.py', app / 'launcher.py')
        shutil.copyfile(binary, app / 'wilson')
        (app / 'wilson').chmod(0o755)
        if (app / 'data').exists():
            shutil.rmtree(app / 'data')
        shutil.copytree(stage / 'data', app / 'data')
        desktop_dir = share / 'applications'
        desktop_dir.mkdir(parents=True, exist_ok=True)
        (desktop_dir / 'Johnny-Castaway.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Johnny Castaway\n'
            'Comment=Settings and original Johnny Castaway animation\n'
            f'Exec=/usr/bin/python3 {quoted(app / "launcher.py", True)}\n'
            f'Icon={app / "assets/johnny-castaway.svg"}\nTerminal=false\nCategories=Game;\n')
        units = config / 'systemd/user'
        units.mkdir(parents=True, exist_ok=True)
        (units / 'johnny-castaway-idle.service').write_text(
            '[Unit]\nDescription=Johnny Castaway idle animation\n'
            'After=graphical-session.target\nPartOf=graphical-session.target\n\n'
            '[Service]\nType=simple\n'
            f'ExecStart=/usr/bin/python3 {quoted(app / "launcher.py", True)} idle\n'
            'Restart=on-failure\nRestartSec=10\n\n'
            '[Install]\nWantedBy=graphical-session.target\n')
    run('systemctl', '--user', 'daemon-reload')
    if args.no_enable:
        run('systemctl', '--user', 'disable', '--now', 'johnny-castaway-idle.service')
    else:
        run('systemctl', '--user', 'enable', '--now', 'johnny-castaway-idle.service')
    print('Installed. Open Johnny Castaway from your application menu.')

if __name__ == '__main__':
    main()
