"""Actual GTK/X11 checks in Xvfb; no real desktop locker or copyrighted data."""
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from johnny_castaway.desktop import X11Idle
os.environ['XDG_SESSION_TYPE'] = 'x11'
monitor = X11Idle()
first = monitor.idle_ms()
time.sleep(0.1)
assert monitor.idle_ms() >= first
monitor.close()
print('PASS: actual X11 idle query')

from gi.repository import GLib
from johnny_castaway.gui import Controls
from johnny_castaway import gui, common
errors = []
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    common.CONFIG = root/'settings.json'
    common.ENGINE_CONFIG = root/'engine-config.txt'
    engine = root/'wilson'
    engine.write_text('#!/bin/sh\nexec sleep 30\n')
    engine.chmod(0o755)
    original_command = gui.command
    gui.command = lambda muted=False, settings=None: [str(engine)]
    app = Controls()
    app.register(None)
    app.activate()
    loop = GLib.MainLoop()
    assert not app.automatic, 'No supported locker exists in this isolated Xvfb session'
    assert not app.enabled.get_sensitive()
    app.speed.set_value(275)
    app.scale.set_selected(3)
    app.filter.set_selected(2)
    app.windowed.set_active(True)
    app.dedither.set_active(True)
    app.daynight.set_selected(1)
    expected = app.playback_settings()
    assert expected['scale'] == 'extend' and expected['filter'] == 'xbr'
    assert expected['daynight'] == 'real24h' and expected['speed'] == 275
    def check():
        if app.busy:
            return True
        try:
            assert common.load_settings() == expected
            assert 'windowed=true' in common.ENGINE_CONFIG.read_text()
            assert 'speed=275' in common.ENGINE_CONFIG.read_text()
            assert app.child is not None and app.child.poll() is None, app.message.get_text()
            # An unavailable idle interface must not kill manually started playback.
            app.check_playback()
            assert app.child.poll() is None
            app.close(None)
            app.window.destroy()
            print('PASS: GTK fallback controls and manual playback without locker/systemd')
        except Exception as exc:
            errors.append(str(exc))
            app.close(None)
        loop.quit()
        return False
    def begin_playback():
        if app.busy:
            return True
        app.start(None)
        GLib.timeout_add(1000, check)
        return False
    app.save(None)
    GLib.timeout_add(100, begin_playback)
    def timeout():
        errors.append('GUI smoke timed out')
        app.close(None)
        loop.quit()
        return False
    GLib.timeout_add(15000, timeout)
    loop.run()
    gui.command = original_command
if errors:
    raise RuntimeError(errors)
