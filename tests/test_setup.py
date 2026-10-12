from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
import setup

class SetupTests(unittest.TestCase):
    def test_preservation_download_needs_explicit_permission(self):
        with patch('builtins.input', side_effect=['2', 'n']):
            with self.assertRaisesRegex(RuntimeError, 'No original data was downloaded'):
                setup.choose_data()
    def test_existing_data_can_be_reused(self):
        with patch('builtins.input', return_value=''):
            self.assertEqual(setup.choose_data(Path('/existing/data')), ['--data','/existing/data'])
    def test_quoted_data_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'My data';folder.mkdir()
            with patch('builtins.input', side_effect=['1', f"'{folder}'"]):
                self.assertEqual(setup.choose_data(), ['--data',str(folder)])
    def test_bad_original_data_is_rejected_before_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'Missing RESOURCE.MAP'):
                setup.validate_data_choice(['--data', temporary])

    def test_noninteractive_setup_explains_advanced_mode(self):
        with patch.object(setup.sys.stdin, 'isatty', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'interactive terminal'):
                setup.main()
    def test_dependency_commands_are_structured_not_shell_evaluated(self):
        for distro, manager in [('debian','apt'), ('fedora','dnf'), ('arch','pacman'), ('suse','zypper')]:
            args=setup.dependency_command(distro)
            self.assertEqual(args[:2], ['sudo',manager])
        with self.assertRaises(RuntimeError): setup.dependency_command(None)
    def test_cancel_does_not_install_anything(self):
        with patch.object(setup.sys.stdin,'isatty',return_value=True), \
             patch('setup.os.geteuid',return_value=1000), \
             patch('setup.existing_install',return_value=(None,None)), \
             patch('setup.validate_data_choice'), \
             patch('setup.choose_data',return_value=['--data','/source']), \
             patch('setup.gui_available',return_value=True), \
             patch('setup.build_packages_available',return_value=True), \
             patch('setup.rust_available',return_value=True), \
             patch('setup.confirm',return_value=False), \
             patch('setup.run_quiet') as run, patch('setup.prepare_rust') as rust:
            setup.main()
            run.assert_not_called();rust.assert_not_called()
    def test_update_reuses_engine_without_build_dependencies_or_rust(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch('setup.LOG',Path(temporary)/'setup.log'), \
             patch.object(setup.sys.stdin,'isatty',return_value=True), \
             patch('setup.os.geteuid',return_value=1000), \
             patch('setup.existing_install',return_value=(Path('/data'),Path('/engine'))), \
             patch('setup.validate_data_choice'), \
             patch('setup.choose_data',return_value=['--data','/data']), \
             patch('setup.gui_available',return_value=True), \
             patch('setup.confirm',return_value=True), \
             patch('setup.run_quiet') as run, patch('setup.rust_available') as check, \
             patch('setup.build_packages_available') as packages, patch('setup.prepare_rust') as rust:
            setup.main()
            self.assertIn('--binary',run.call_args.args[0])
            packages.assert_not_called();check.assert_not_called();rust.assert_not_called()
    def test_fresh_setup_installs_only_after_confirmation_then_checks_again(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch('setup.LOG',Path(temporary)/'setup.log'), \
             patch.object(setup.sys.stdin,'isatty',return_value=True), \
             patch('setup.os.geteuid',return_value=1000), \
             patch('setup.read_release',return_value={'ID':'debian'}), \
             patch('setup.existing_install',return_value=(None,None)), \
             patch('setup.validate_data_choice'), \
             patch('setup.choose_data',return_value=['--data','/source']), \
             patch('setup.gui_available',side_effect=[False,True]), \
             patch('setup.build_packages_available',return_value=True), \
             patch('setup.rust_available',return_value=False), \
             patch('setup.confirm',return_value=True), \
             patch('setup.subprocess.run') as packages, patch('setup.run_quiet') as run, \
             patch('setup.prepare_rust') as rust:
            setup.main()
            self.assertEqual(packages.call_args.args[0][:2],['sudo','apt'])
            rust.assert_called_once();run.assert_called_once()
    def test_fresh_rust_setup_preserves_existing_profiles_and_defaults(self):
        with patch.dict(os.environ, {}, clear=False), \
             patch('setup.shutil.which', return_value=None), \
             patch('setup.urllib.request.urlopen') as response, \
             patch('setup.run_quiet') as run, patch('setup.rust_available', return_value=True):
            response.return_value.__enter__.return_value.read.return_value = b'# test installer'
            setup.prepare_rust()
            args = run.call_args.args[0]
            self.assertIn('--no-modify-path', args)
            self.assertIn('--no-update-default-toolchain', args)

    def test_rust_update_does_not_change_the_users_default_toolchain(self):
        with patch.dict(os.environ, {}, clear=False), \
             patch('setup.shutil.which',return_value='/bin/rustup'), \
             patch('setup.run_quiet') as run, patch('setup.rust_available',return_value=True):
            setup.prepare_rust()
            self.assertEqual(run.call_args.args[0][1:4],['toolchain','install','stable'])
            self.assertEqual(os.environ['RUSTUP_TOOLCHAIN'],'stable')
            self.assertNotIn('default',run.call_args.args[0])

if __name__ == '__main__': unittest.main()
