#!/usr/bin/python3
"""Settings, idle integration, diagnostics, or dependency-light manual playback."""
import os
import sys
from johnny_castaway.common import command

def main():
    args = sys.argv[1:]
    if '--play' in args:
        allowed = {'--play', '--mute', '--windowed'}
        if set(args) - allowed:
            raise SystemExit('Manual options: --play [--mute] [--windowed]')
        cmd = command('--mute' in args)
        if '--windowed' in args:
            cmd.append('--windowed')
        os.execv(cmd[0], cmd)
    elif args and args[0] == 'idle':
        sys.argv.pop(1)
        from johnny_castaway.idle import main as idle
        idle()
    elif '--doctor' in args:
        try:
            from johnny_castaway.desktop import detect, user_service_available
        except ImportError:
            print('GUI/idle libraries are not installed. Manual playback remains available with --play.')
            return
        monitor = detect()
        print('Desktop:', monitor.name)
        print('Automatic idle interface:', monitor.supported)
        services = user_service_available()
        print('User service manager:', services)
        print('Mode:', 'automatic + manual' if monitor.supported and services else 'manual')
        if monitor.reason:
            print(monitor.reason)
        monitor.close()
    else:
        from johnny_castaway.gui import main as gui
        gui()

if __name__ == '__main__':
    main()
