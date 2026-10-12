"""GNOME idle playback which always yields to its screen shield."""
import argparse
import logging
import signal
import subprocess
import time
from gi.repository import Gio
from .common import APP, command, load_settings

class Playback:
    def __init__(self, launch=subprocess.Popen):
        self.child = None
        self.armed = True
        self.launch = launch

    def stop(self):
        if self.child is not None:
            if self.child.poll() is None:
                self.child.terminate()
                try:
                    self.child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait()
            self.child = None

    def update(self, locked, idle_ms, threshold_ms, muted):
        if locked or idle_ms < threshold_ms:
            self.stop()
            self.armed = True
        elif self.armed and self.child is None:
            self.child = self.launch(command(muted), cwd=APP)
            self.armed = False
            logging.info('Started idle playback')
        if self.child is not None and self.child.poll() is not None:
            logging.info('Playback exited: %s', self.child.returncode)
            self.child = None

    def unavailable(self):
        self.stop()
        self.armed = False  # require observed activity before retrying

class Monitor:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def call(self, dest, path, interface, method):
        return self.bus.call_sync(dest, path, interface, method, None, None,
                                 Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]

    def status(self):
        locked = self.call('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver',
                           'org.gnome.ScreenSaver', 'GetActive')
        idle = self.call('org.gnome.Mutter.IdleMonitor', '/org/gnome/Mutter/IdleMonitor/Core',
                         'org.gnome.Mutter.IdleMonitor', 'GetIdletime')
        return locked, idle

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--seconds', type=int, help='Temporary test threshold')
    args = parser.parse_args()
    if args.seconds is not None and args.seconds < 1:
        parser.error('seconds must be positive')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    monitor = Monitor()
    if args.probe:
        print('locked=%s idle_ms=%s' % monitor.status())
        return
    playback = Playback()
    running = True
    def shutdown(*unused):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        while running:
            try:
                settings = load_settings()
                threshold = args.seconds if args.seconds is not None else settings['minutes'] * 60
                locked, idle = monitor.status()
                playback.update(locked, idle, threshold * 1000, settings['muted'])
            except Exception as exc:
                playback.unavailable()
                logging.error('Checks failed; playback stopped: %s', exc)
            time.sleep(1)
    finally:
        playback.stop()

if __name__ == '__main__':
    main()
