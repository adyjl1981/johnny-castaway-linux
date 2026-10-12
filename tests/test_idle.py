import subprocess
import unittest
from johnny_castaway.idle import Playback

class Child:
    def __init__(self):
        self.returncode = None
        self.stopped = False
    def poll(self): return self.returncode
    def terminate(self): self.stopped = True; self.returncode = -15
    def wait(self, **kwargs): return self.returncode

class IdleTests(unittest.TestCase):
    def setUp(self):
        self.children = []
        def launch(*args, **kwargs):
            child = Child()
            self.children.append(child)
            return child
        self.player = Playback(launch)
    def test_activity_closes_and_rearms(self):
        self.player.update(False, 300000, 300000, True)
        self.player.update(False, 0, 300000, True)
        self.assertTrue(self.children[0].stopped)
        self.player.update(False, 300000, 300000, True)
        self.assertEqual(len(self.children), 2)
    def test_lock_blocks_launch_and_stops_running_child(self):
        self.player.update(True, 600000, 300000, True)
        self.assertEqual(self.children, [])
        self.player.update(False, 600000, 300000, True)
        self.player.update(True, 600000, 300000, True)
        self.assertTrue(self.children[0].stopped)
    def test_failure_requires_activity_before_retry(self):
        self.player.update(False, 600000, 300000, True)
        self.player.unavailable()
        self.assertTrue(self.children[0].stopped)
        self.player.update(False, 600000, 300000, True)
        self.assertEqual(len(self.children), 1)
        self.player.update(False, 0, 300000, True)
        self.player.update(False, 600000, 300000, True)
        self.assertEqual(len(self.children), 2)
    def test_exit_does_not_relaunch_in_same_idle_period(self):
        self.player.update(False, 600000, 300000, True)
        self.children[0].returncode = 0
        self.player.update(False, 600000, 300000, True)
        self.player.update(False, 600000, 300000, True)
        self.assertEqual(len(self.children), 1)
    def test_changed_threshold_closes_playback(self):
        self.player.update(False, 300000, 300000, True)
        self.player.update(False, 300000, 600000, True)
        self.assertTrue(self.children[0].stopped)

if __name__ == '__main__': unittest.main()
