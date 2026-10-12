import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parent.parent

class PortableInstallTests(unittest.TestCase):
    def test_manual_install_without_gi_or_systemd(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root/'source'; data.mkdir()
            (data/'RESOURCE.MAP').write_bytes(b'synthetic map')
            (data/'RESOURCE.001').write_bytes(b'synthetic data')
            binary = root/'engine'; binary.write_text('#!/bin/sh\nexit 0\n'); binary.chmod(0o755)
            env = os.environ.copy()
            env.update(HOME=str(root/'home'), XDG_CONFIG_HOME=str(root/'config'),
                       XDG_DATA_HOME=str(root/'share'), XDG_STATE_HOME=str(root/'state'), PATH='/nonexistent',
                       DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent')
            result = subprocess.run(['/usr/bin/python3','-S',str(ROOT/'install.py'),
                '--no-gui','--binary',str(binary),'--data',str(data)],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            desktop = (root/'share/applications/Johnny-Castaway.desktop').read_text()
            self.assertIn('--play', desktop)
            self.assertTrue((root/'share/johnny-castaway/wilson').is_file())
            played = subprocess.run(['/usr/bin/python3','-S',
                str(root/'share/johnny-castaway/launcher.py'),'--play'], env=env)
            self.assertEqual(played.returncode, 0)
            # Guided upgrades reuse both engine and data from the installed directory.
            upgraded = subprocess.run(['/usr/bin/python3','-S',str(ROOT/'install.py'),
                '--no-gui','--binary',str(root/'share/johnny-castaway/wilson'),
                '--data',str(root/'share/johnny-castaway/data')], env=env,
                capture_output=True, text=True)
            self.assertEqual(upgraded.returncode, 0, upgraded.stdout+upgraded.stderr)
            self.assertEqual((root/'share/johnny-castaway/data/RESOURCE.001').read_bytes(), b'synthetic data')

if __name__ == '__main__': unittest.main()
