import unittest
from unittest.mock import patch
from johnny_castaway.desktop import Monitor, X11Idle, UnsupportedDesktop, LOCKERS, detect
from johnny_castaway.distro import family

class Bus:
    def __init__(self, owners, failure=None):
        self.owners = owners
        self.failure = failure
        self.active = False
    def owns(self, name): return name in self.owners
    def call(self, dest, path, interface, method):
        if dest == self.failure: raise RuntimeError('Unavailable')
        return self.active if method == 'GetActive' else 12345

class X11:
    def __init__(self, env):
        if env.get('XDG_SESSION_TYPE') != 'x11': raise UnsupportedDesktop('Wayland')
    def idle_ms(self): return 67890
    def close(self): pass

class DesktopTests(unittest.TestCase):
    def test_gnome_wayland_uses_mutter(self):
        bus = Bus({'org.gnome.ScreenSaver', 'org.gnome.Mutter.IdleMonitor'})
        monitor = Monitor(bus, {'XDG_SESSION_TYPE': 'wayland'}, X11)
        self.assertTrue(monitor.supported)
        self.assertEqual(monitor.status(), (False, 12345))
        bus.active = True
        self.assertTrue(monitor.locked())
    def test_all_named_x11_lockers(self):
        for name, dest, path in LOCKERS:
            with self.subTest(desktop=name):
                monitor = Monitor(Bus({dest}), {'XDG_SESSION_TYPE': 'x11'}, X11)
                self.assertTrue(monitor.supported)
                self.assertEqual(monitor.status(), (False, 67890))
    def test_kde_wayland_preserves_manual_lock_monitor(self):
        monitor = Monitor(Bus({'org.freedesktop.ScreenSaver'}), {'XDG_SESSION_TYPE': 'wayland'}, X11)
        self.assertFalse(monitor.supported)
        self.assertFalse(monitor.locked())
        with self.assertRaises(UnsupportedDesktop): monitor.status()
    def test_missing_locker_means_manual(self):
        monitor = Monitor(Bus(set()), {'XDG_SESSION_TYPE': 'x11'}, X11)
        self.assertFalse(monitor.supported)
        self.assertIsNone(monitor.locked())
    def test_locker_failure_is_not_treated_as_unlocked(self):
        bus = Bus({'org.xfce.ScreenSaver'})
        monitor = Monitor(bus, {'XDG_SESSION_TYPE': 'x11'}, X11)
        bus.failure = 'org.xfce.ScreenSaver'
        with self.assertRaises(RuntimeError): monitor.locked()
    def test_no_bus_still_allows_manual_mode(self):
        with patch('johnny_castaway.desktop.SessionBus', side_effect=RuntimeError('No bus')):
            monitor = detect()
        self.assertFalse(monitor.supported)
        self.assertIsNone(monitor.locked())
        monitor.close()
    def test_wayland_never_queries_xwayland_for_idle(self):
        with self.assertRaises(UnsupportedDesktop):
            X11Idle({'XDG_SESSION_TYPE': 'wayland', 'DISPLAY': ':0'})

class DistroTests(unittest.TestCase):
    def test_major_families_and_derivatives(self):
        for name, like, expected in [('ubuntu','','debian'), ('linuxmint','ubuntu debian','debian'),
            ('fedora','','fedora'), ('arch','','arch'), ('manjaro','arch','arch'),
            ('opensuse-tumbleweed','suse','suse'), ('opensuse-leap','suse opensuse','suse'),
            ('pop','ubuntu','debian'), ('debian','','debian')]:
            with self.subTest(name=name):
                self.assertEqual(family({'ID':name,'ID_LIKE':like}), expected)
    def test_unknown_distro(self):
        self.assertIsNone(family({'ID':'unknown'}))

if __name__ == '__main__': unittest.main()
