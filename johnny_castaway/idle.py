"""Idle playback which always yields to the existing desktop locker."""
import argparse
import logging
import signal
import subprocess
import time
from .desktop import Monitor
from .common import APP, command, load_settings, prepare_engine_config

class Playback:
    def __init__(self, launch=subprocess.Popen, prepare=prepare_engine_config):
        self.child = None
        self.armed = True
        self.launch = launch
        self.prepare = prepare

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

    def update(self, locked, idle_ms, threshold_ms, muted, settings=None):
        if locked or idle_ms < threshold_ms:
            self.stop()
            self.armed = True
        elif self.armed and self.child is None:
            options = dict(load_settings() if settings is None else settings)
            options['muted'] = muted
            self.prepare(options)
            self.child = self.launch(command(muted, options), cwd=APP)
            self.armed = False
            logging.info('Started idle playback')
        if self.child is not None and self.child.poll() is not None:
            logging.info('Playback exited: %s', self.child.returncode)
            self.child = None

    def unavailable(self):
        self.stop()
        self.armed = False  # require observed activity before retrying

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
        print('backend=%s automatic=%s reason=%s' % (monitor.name, monitor.supported, monitor.reason))
        if monitor.supported:
            print('locked=%s idle_ms=%s' % monitor.status())
        monitor.close()
        return
    if not monitor.supported:
        logging.info('Manual mode: %s', monitor.reason)
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
                playback.update(locked, idle, threshold * 1000, settings['muted'], settings)
            except Exception as exc:
                playback.unavailable()
                logging.error('Checks failed; playback stopped: %s', exc)
            time.sleep(1)
    finally:
        playback.stop()
        monitor.close()

if __name__ == '__main__':
    main()
