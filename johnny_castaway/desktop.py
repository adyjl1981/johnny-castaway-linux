"""Read-only desktop capability detection. Never modify or inhibit a locker."""
import ctypes
import ctypes.util
import os
from gi.repository import Gio, GLib
from .common import user_service_available

LOCKERS = (
    ('GNOME', 'org.gnome.ScreenSaver', '/org/gnome/ScreenSaver'),
    ('Cinnamon', 'org.cinnamon.ScreenSaver', '/org/cinnamon/ScreenSaver'),
    ('MATE', 'org.mate.ScreenSaver', '/org/mate/ScreenSaver'),
    ('XFCE', 'org.xfce.ScreenSaver', '/org/xfce/ScreenSaver'),
    ('KDE / freedesktop', 'org.freedesktop.ScreenSaver', '/org/freedesktop/ScreenSaver'),
)

class UnsupportedDesktop(RuntimeError):
    pass

class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [('window', ctypes.c_ulong), ('state', ctypes.c_int),
                ('kind', ctypes.c_int), ('til_or_since', ctypes.c_ulong),
                ('idle', ctypes.c_ulong), ('event_mask', ctypes.c_ulong)]

class X11Idle:
    """Query real X11 only. XWayland does not report the whole Wayland session."""
    def __init__(self, environ=None):
        env = os.environ if environ is None else environ
        if env.get('XDG_SESSION_TYPE') != 'x11' or not env.get('DISPLAY'):
            raise UnsupportedDesktop('A real X11 session is required for X11 idle detection.')
        x11 = ctypes.util.find_library('X11')
        xss = ctypes.util.find_library('Xss')
        if not x11 or not xss:
            raise UnsupportedDesktop('Install the X11 and libXScrnSaver runtime libraries for idle detection.')
        self.x11 = ctypes.CDLL(x11)
        self.xss = ctypes.CDLL(xss)
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.x11.XCloseDisplay.restype = ctypes.c_int
        self.xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                 ctypes.POINTER(XScreenSaverInfo)]
        self.xss.XScreenSaverQueryInfo.restype = ctypes.c_int
        self.display = self.x11.XOpenDisplay(env['DISPLAY'].encode())
        if not self.display:
            raise UnsupportedDesktop('Cannot open the X11 display.')
        self.root = self.x11.XDefaultRootWindow(self.display)
        try:
            self.idle_ms()  # verify before enabling automation
        except Exception:
            self.close()
            raise

    def idle_ms(self):
        info = XScreenSaverInfo()
        if not self.xss.XScreenSaverQueryInfo(self.display, self.root, ctypes.byref(info)):
            raise UnsupportedDesktop('The X11 screensaver extension is unavailable.')
        return int(info.idle)

    def close(self):
        if self.display:
            self.x11.XCloseDisplay(self.display)
            self.display = None

class SessionBus:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def call(self, dest, path, interface, method):
        return self.bus.call_sync(dest, path, interface, method, None, None,
                                 Gio.DBusCallFlags.NO_AUTO_START, 1500, None).unpack()[0]

    def owns(self, name):
        return self.bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
            'org.freedesktop.DBus', 'NameHasOwner', GLib.Variant('(s)', (name,)),
            None, Gio.DBusCallFlags.NONE, 1500, None).unpack()[0]

class Monitor:
    def __init__(self, bus=None, environ=None, x11_factory=X11Idle):
        self.bus = bus or SessionBus()
        self.env = os.environ if environ is None else environ
        self.locker = None
        self.idle = None
        self.name = 'Manual playback'
        self.reason = 'No supported idle interface was found.'
        self._detect(x11_factory)

    def _detect(self, x11_factory):
        desktop = self.env.get('XDG_CURRENT_DESKTOP', '').lower()
        candidates = sorted(LOCKERS, key=lambda item: item[0].lower() not in desktop)
        for label, dest, path in candidates:
            try:
                if self.bus.owns(dest):
                    active = self.bus.call(dest, path, dest, 'GetActive')
                    if not isinstance(active, bool):
                        continue
                    self.locker = (dest, path)
                    self.name = label
                    break
            except Exception:
                continue
        if not self.locker:
            self.reason = 'Your screen locker does not expose a supported status interface. Manual playback is available.'
            return
        if self.locker[0] == 'org.gnome.ScreenSaver':
            try:
                if self.bus.owns('org.gnome.Mutter.IdleMonitor'):
                    self._gnome_idle()
                    self.idle = self._gnome_idle
                    self.name = 'GNOME'
                    self.reason = ''
                    return
            except Exception:
                pass
        try:
            x11 = x11_factory(self.env)
            self.idle = x11.idle_ms
            self._x11 = x11
            self.name += ' (X11)'
            self.reason = ''
        except Exception as exc:
            self.reason = str(exc) + ' Manual playback is available.'

    @property
    def supported(self):
        return self.locker is not None and self.idle is not None

    def _gnome_idle(self):
        value = self.bus.call('org.gnome.Mutter.IdleMonitor',
            '/org/gnome/Mutter/IdleMonitor/Core', 'org.gnome.Mutter.IdleMonitor', 'GetIdletime')
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise UnsupportedDesktop('Invalid idle response')
        return value

    def locked(self):
        if self.locker is None:
            return None  # manual mode: the desktop still owns its secure lock screen
        dest, path = self.locker
        value = self.bus.call(dest, path, dest, 'GetActive')
        if not isinstance(value, bool):
            raise UnsupportedDesktop('Invalid lock response')
        return value

    def status(self):
        if not self.supported:
            raise UnsupportedDesktop(self.reason)
        return self.locked(), self.idle()

    def close(self):
        if hasattr(self, '_x11'):
            self._x11.close()


def detect():
    """Manual mode is a valid capability, including sessions without a bus."""
    try:
        return Monitor()
    except Exception:
        monitor = object.__new__(Monitor)
        monitor.locker = monitor.idle = None
        monitor.name = 'Manual playback'
        monitor.reason = 'Desktop status is unavailable. Manual playback is available.'
        return monitor
