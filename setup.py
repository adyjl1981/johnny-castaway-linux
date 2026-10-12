#!/usr/bin/python3
"""Guided personal setup. Administrative changes require an explicit confirmation."""
import contextlib
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from install import ROOT, check_rust_toolchain, copy_data
from johnny_castaway.distro import PACKAGES, family, read_release

LOG = ROOT / 'setup.log'

def confirm(message):
    return input(message + ' [y/N]: ').strip().lower() in ('y', 'yes')

def gui_available():
    try:
        return subprocess.run([sys.executable, '-c',
            'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk'],
            capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def build_packages_available():
    if any(shutil.which(tool) is None for tool in ('git', 'cc', 'pkg-config')):
        return False
    return subprocess.run(['pkg-config', '--exists', 'alsa', 'wayland-client',
                           'xkbcommon', 'x11'], capture_output=True).returncode == 0

def rust_available():
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            check_rust_toolchain()
        return True
    except RuntimeError:
        return False

def existing_install():
    share = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    app = share / 'johnny-castaway'
    data = app / 'data'
    if not all((data / name).is_file() for name in ('RESOURCE.MAP', 'RESOURCE.001')):
        data = None
    binary = app / 'wilson'
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return data, None
    try:
        usable = subprocess.run([str(binary), '--help'], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        usable = False
    return data, binary if usable else None

def choose_data(existing=None):
    print('\nChoose the original Johnny Castaway data:')
    if existing:
        print('  1. Keep the data from my existing installation')
        print('  2. Use another original data folder or ZIP')
        print('  3. Download the Internet Archive preservation copy')
        choice = input('Choice [1]: ').strip() or '1'
        if choice == '1':
            return ['--data', str(existing)]
        own, download = '2', '3'
    else:
        print('  1. Use my original data folder or scrantic-run.zip')
        print('  2. Download the Internet Archive preservation copy')
        choice = input('Choice [1]: ').strip() or '1'
        own, download = '1', '2'
    if choice == download:
        print('The original data is copyrighted. This download is for personal use; use it only if entitled to a copy.')
        if not confirm('Use this preservation copy?'):
            raise RuntimeError('Setup cancelled. No original data was downloaded.')
        return ['--fetch-data']
    if choice == own:
        text = input('Drag the folder/ZIP into this terminal, or enter its path: ').strip()
        # Terminal drag-and-drop commonly shell-quotes paths containing spaces.
        parts = shlex.split(text)
        path = Path(parts[0] if len(parts) == 1 else text).expanduser().resolve()
        if not text or not path.exists():
            raise RuntimeError('That path was not found. Run setup again and choose the data folder or ZIP.')
        return ['--data', str(path)]
    raise RuntimeError('Invalid choice. Run setup again and choose one of the listed options.')

def validate_data_choice(args):
    if args[0] == '--data':
        # Check the user's files before offering administrative/package changes.
        with tempfile.TemporaryDirectory(prefix='johnny-data-check-') as temporary:
            copy_data(Path(args[1]), Path(temporary) / 'data')

def dependency_command(distro):
    text = PACKAGES.get(distro)
    if not text:
        raise RuntimeError('Automatic package installation is not available for this distro. See README prerequisites.')
    return shlex.split(text)

def run_quiet(command, message):
    print(message, flush=True)
    with LOG.open('a') as log:
        log.write('\n' + shlex.join(map(str, command)) + '\n')
        log.flush()
        process = subprocess.Popen(command, stdout=log, stderr=log)
        ticks = 0
        while True:
            try:
                code = process.wait(timeout=2)
                break
            except subprocess.TimeoutExpired:
                if sys.stdout.isatty():
                    print('\r' + message + ' ' + '|/-\\'[ticks % 4], end='', flush=True)
                ticks += 1
            except BaseException:
                process.terminate()
                process.wait()
                raise
        if sys.stdout.isatty():
            print('\r' + message + '   ')
        if code:
            raise RuntimeError(f'This step did not complete. Details are in {LOG}. Fix the reported issue and run setup again.')

def prepare_rust():
    cargo_home = Path(os.environ.get('CARGO_HOME', Path.home() / '.cargo'))
    os.environ['PATH'] = str(cargo_home / 'bin') + os.pathsep + os.environ.get('PATH', '')
    rustup = shutil.which('rustup')
    if rustup:
        run_quiet([rustup, 'toolchain', 'install', 'stable', '--profile', 'minimal'], 'Preparing the build toolchain…')
    else:
        with tempfile.TemporaryDirectory(prefix='johnny-rustup-') as temporary:
            script = Path(temporary) / 'rustup-init.sh'
            with urllib.request.urlopen('https://sh.rustup.rs', timeout=60) as response:
                contents = response.read(1_000_001)
            if len(contents) > 1_000_000:
                raise RuntimeError('Unexpectedly large Rust installer download; setup stopped.')
            script.write_bytes(contents)
            run_quiet(['sh', str(script), '-y', '--profile', 'minimal', '--no-modify-path',
                       '--no-update-default-toolchain', '--default-toolchain', 'stable'], 'Preparing the build toolchain…')
    # Select stable for this setup and its build only; do not change the user's default/overrides.
    os.environ['RUSTUP_TOOLCHAIN'] = 'stable'
    if not rust_available():
        raise RuntimeError('The toolchain is still unavailable. See setup.log and the README for help.')

def main():
    if not sys.stdin.isatty():
        raise RuntimeError('Guided setup needs an interactive terminal. Use install.sh --help for scripted installation options.')
    if os.geteuid() == 0:
        raise RuntimeError('Run ./install.sh as your normal desktop user, without sudo. Setup asks for administrator permission only for system packages.')
    print('Johnny Castaway — guided setup')
    print('This will install the app for your account. Your screen-lock settings stay unchanged.')
    release = read_release()
    print('Detected:', release.get('PRETTY_NAME', 'Linux'))
    installed_data, installed_binary = existing_install()
    data_args = choose_data(installed_data)
    validate_data_choice(data_args)
    binary = installed_binary if installed_binary and confirm('Reuse the working animation engine from your existing installation?') else None
    packages_needed = not gui_available() or (binary is None and not build_packages_available())
    rust_needed = binary is None and not rust_available()
    package_args = dependency_command(family(release)) if packages_needed else None
    print('\nSetup will:')
    if packages_needed:
        print('  • Install/update the required system packages (administrator password may be needed).')
    if rust_needed:
        print('  • Install/update the Rust build toolchain for your account.')
    print('  • Install the control panel and animation engine for your account.')
    print('  • Enable idle playback where supported (five minutes by default); otherwise offer manual playback.')
    if not confirm('Continue with setup?'):
        print('Cancelled. No packages or application files were changed.')
        return
    LOG.write_text('Johnny Castaway guided setup\n')
    if package_args:
        # Leave the distro installer on the terminal so password/transaction prompts remain visible.
        print('Installing the required system packages…')
        subprocess.run(package_args, check=True)
        if not gui_available() or (binary is None and not build_packages_available()):
            raise RuntimeError('Some dependencies are still missing. See README prerequisites or use --no-gui for manual playback.')
    if rust_needed:
        prepare_rust()
    args = [sys.executable, str(ROOT / 'install.py'), *data_args]
    if binary:
        args += ['--binary', str(binary)]
    run_quiet(args, 'Installing Johnny Castaway… this may take several minutes.')
    print('\nDone! Open Johnny Castaway from your application menu to adjust settings or start playback.')
    print('Automatic playback is available on supported desktops. Your normal secure lock screen still takes precedence.')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('\nSetup stopped:', exc, file=sys.stderr)
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nSetup cancelled.', file=sys.stderr)
        raise SystemExit(1)
