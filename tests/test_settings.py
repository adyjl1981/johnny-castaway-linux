from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from johnny_castaway import common
from johnny_castaway.idle import Playback

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name, path in [('CONFIG', root/'settings.json'), ('ENGINE_CONFIG', root/'engine.txt')]:
            patcher = patch.object(common, name, path)
            patcher.start(); self.addCleanup(patcher.stop)
    def test_existing_settings_upgrade_without_losing_delay_or_mute(self):
        common.CONFIG.write_text('{"minutes": 12, "muted": false}')
        settings = common.load_settings()
        self.assertEqual(settings['minutes'], 12)
        self.assertFalse(settings['muted'])
        self.assertEqual(settings['speed'], 100)
        self.assertEqual(settings['scale'], 'fit')
    def test_all_picture_options_saved_and_loaded(self):
        settings = dict(common.DEFAULTS, speed=275, scale='extend', filter='xbrz',
                        windowed=True, dedither=True, daynight='real24h')
        common.save_settings(8, False, settings)
        self.assertEqual(common.load_settings(), dict(settings, minutes=8, muted=False))
    def test_invalid_values_rejected(self):
        for value in ({'speed':24}, {'speed':401}, {'speed':True}, {'scale':'invalid'},
                      {'filter':'shell command'}, {'daynight':'invalid'}, {'dedither':'false'},
                      {'windowed':1}, {'muted':None}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                common.validate_settings(value)
    def test_false_booleans_override_existing_engine_configuration(self):
        common.ENGINE_CONFIG.write_text('# keep this\nwindowed=true\nmute=true\ndedither=true\nstory=true\nintro_secs=7\n')
        settings = dict(common.DEFAULTS, muted=False)
        common.prepare_engine_config(settings)
        text = common.ENGINE_CONFIG.read_text()
        for line in ('windowed=false', 'mute=false', 'dedither=false', 'story=true', 'intro_secs=7', '# keep this'):
            self.assertIn(line, text)
    def test_command_passes_selected_engine_options(self):
        settings = dict(common.DEFAULTS, speed=200, scale='stretch', filter='xbr',
                        windowed=True, dedither=True, daynight='real24h')
        args = common.command(True, settings)
        for flag, value in [('--speed','200'), ('--scale','stretch'), ('--filter','xbr'), ('--daynight','real24h')]:
            self.assertEqual(args[args.index(flag)+1], value)
        for flag in ('--windowed', '--dedither', '--mute'):
            self.assertIn(flag, args)
    def test_idle_playback_receives_the_same_saved_options(self):
        calls = []
        settings = dict(common.DEFAULTS, speed=50, scale='integer', filter='nearest')
        class Child:
            def poll(self): return None
        player = Playback(lambda args, **kw: calls.append(args) or Child(), prepare=common.prepare_engine_config)
        player.update(False, 300000, 300000, True, settings)
        self.assertEqual(calls[0], common.command(True, settings))
        self.assertIn('speed=50', common.ENGINE_CONFIG.read_text())

if __name__ == '__main__': unittest.main()
