"""Small GTK 4 control panel; no changes to GNOME locking settings."""
import subprocess
import threading
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from .common import APP, SERVICE, command, load_settings, save_settings
from .desktop import detect, user_service_available

class Controls(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.github.johnnycastaway.Controls')
        self.child = None
        self.restore_idle = False
        self.busy = False
        self.monitor = detect()
        self.services = user_service_available()
        self.automatic = self.monitor.supported and self.services

    def do_activate(self):
        if self.get_active_window():
            self.get_active_window().present()
            return
        self.window = Gtk.ApplicationWindow(application=self, title='Johnny Castaway')
        self.window.set_default_size(420, 460)
        self.window.connect('close-request', self.close)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                      margin_top=28, margin_bottom=28, margin_start=28, margin_end=28)
        self.window.set_child(box)
        image = Gtk.Image.new_from_file(str(APP / 'assets' / 'johnny-castaway.svg'))
        image.set_pixel_size(112)
        box.append(image)
        title = Gtk.Label(label='A little island. A familiar castaway.')
        title.add_css_class('title-3')
        box.append(title)
        settings = load_settings()
        self.enabled = Gtk.CheckButton(label='Start automatically when I’m idle')
        self.enabled.set_active(self.automatic and self.is_enabled())
        self.enabled.set_sensitive(self.automatic)
        box.append(self.enabled)
        row = Gtk.Box(spacing=12)
        row.append(Gtk.Label(label='Start after', hexpand=True, xalign=0))
        self.minutes = Gtk.SpinButton.new_with_range(1, 240, 1)
        self.minutes.set_value(settings['minutes'])
        self.minutes.set_sensitive(self.automatic)
        row.append(self.minutes)
        row.append(Gtk.Label(label='minutes'))
        box.append(row)
        self.muted = Gtk.CheckButton(label='Mute sound')
        self.muted.set_active(settings['muted'])
        box.append(self.muted)
        buttons = Gtk.Box(spacing=12, homogeneous=True)
        self.save_button = Gtk.Button(label='Save settings')
        self.save_button.connect('clicked', self.save)
        self.start_button = Gtk.Button(label='Start now')
        self.start_button.add_css_class('suggested-action')
        self.start_button.connect('clicked', self.start)
        buttons.append(self.save_button)
        buttons.append(self.start_button)
        box.append(buttons)
        box.append(Gtk.Label(label='Press a key or click to leave the animation.\nYour desktop’s lock screen always takes precedence.', wrap=True))
        reason = self.monitor.reason or ('Automatic playback needs a systemd user session.' if not self.services else '')
        self.mode_text = 'Ready — ' + self.monitor.name if self.automatic else reason + ' Use Start now.'
        self.message = Gtk.Label(label=self.mode_text, wrap=True, xalign=0)
        self.message.add_css_class('dim-label')
        box.append(self.message)
        self.window.present()

    def is_enabled(self):
        if not self.automatic:
            return False
        return subprocess.run(['systemctl', '--user', 'is-enabled', SERVICE],
                              capture_output=True).returncode == 0

    def action(self, *args):
        if not self.services:
            return
        subprocess.run(['systemctl', '--user', *args, SERVICE], check=True,
                       capture_output=True, text=True)

    def worker(self, task, success):
        if self.busy:
            return
        self.busy = True
        self.save_button.set_sensitive(False)
        self.start_button.set_sensitive(False)
        def run():
            try:
                task()
                message = success
            except Exception as exc:
                message = 'Could not complete the action: ' + str(exc)
            GLib.idle_add(finish, message)
        def finish(message):
            self.busy = False
            self.save_button.set_sensitive(self.child is None)
            self.start_button.set_sensitive(self.child is None)
            self.message.set_text(message)
            return False
        threading.Thread(target=run, daemon=True).start()

    def save(self, unused):
        minutes = self.minutes.get_value_as_int()
        muted = self.muted.get_active()
        enabled = self.enabled.get_active()
        def task():
            save_settings(minutes, muted)
            if self.services:
                self.action('enable' if enabled and self.automatic else 'disable', '--now')
        self.worker(task, 'Saved. Idle playback ' + ('enabled.' if enabled else 'disabled.'))

    def start(self, unused):
        if self.child is not None:
            return
        muted = self.muted.get_active()
        def task():
            if self.monitor.locked():
                raise RuntimeError('Unlock your desktop first.')
            self.restore_idle = self.services and subprocess.run(['systemctl', '--user', 'is-active', SERVICE],
                                               capture_output=True).returncode == 0
            if self.services:
                self.action('stop')
            try:
                self.child = subprocess.Popen(command(muted), cwd=APP)
            except Exception:
                if self.restore_idle:
                    self.action('start')
                self.restore_idle = False
                raise
            GLib.idle_add(lambda: (GLib.timeout_add(500, self.check_playback), False)[1])
        self.worker(task, 'Playing. Press a key or click to return.')

    def check_playback(self):
        if self.child is None:
            return False
        try:
            locked = self.monitor.locked()
        except Exception:
            locked = True
        if locked and self.child.poll() is None:
            self.child.terminate()
        if self.child.poll() is None:
            return True
        self.child = None
        restore = self.restore_idle
        self.restore_idle = False
        if restore:
            self.worker(lambda: self.action('start'), 'Ready. Idle playback resumed.')
        else:
            self.message.set_text(self.mode_text)
            self.save_button.set_sensitive(True)
            self.start_button.set_sensitive(True)
        return False

    def close(self, unused):
        if self.busy:
            self.message.set_text('Please wait for the current action to finish.')
            return True
        if self.child is not None:
            self.child.terminate()
            try:
                self.child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait()
            self.child = None
        if self.restore_idle:
            try:
                self.action('start')
            except Exception:
                pass
        self.monitor.close()
        return False

def main():
    Controls().run(None)

if __name__ == '__main__':
    main()
