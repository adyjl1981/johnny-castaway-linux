import subprocess
import unittest
from unittest.mock import patch
from install import check_rust_toolchain

class ToolchainTests(unittest.TestCase):
    def run_versions(self, rustc, cargo):
        with patch('install.subprocess.check_output', side_effect=[rustc, cargo]):
            check_rust_toolchain()
    def test_minimum_and_newer_toolchains(self):
        for version in ('1.85.0', '1.98.1', '2.0.0'):
            with self.subTest(version=version):
                self.run_versions(f'rustc {version} (build)', f'cargo {version} (build)')
    def test_old_compiler_stops_with_update_guidance(self):
        with self.assertRaisesRegex(RuntimeError, '1.85.0.*1.84.1'):
            self.run_versions('rustc 1.84.1 (build)', 'cargo 1.85.0 (build)')
    def test_old_cargo_rejected_even_with_new_compiler(self):
        with self.assertRaisesRegex(RuntimeError, 'found cargo 1.84.0'):
            self.run_versions('rustc 1.85.0 (build)', 'cargo 1.84.0 (build)')
    def test_prerelease_of_minimum_not_accepted_as_stable_minimum(self):
        with self.assertRaises(RuntimeError):
            self.run_versions('rustc 1.85.0-beta.1 (build)', 'cargo 1.85.0 (build)')
    def test_missing_or_broken_compiler(self):
        for error in (FileNotFoundError(), subprocess.CalledProcessError(1, 'rustc'),
                      subprocess.TimeoutExpired('rustc', 10)):
            with self.subTest(error=type(error).__name__):
                with patch('install.subprocess.check_output', side_effect=error):
                    with self.assertRaisesRegex(RuntimeError, 'Cannot run rustc'):
                        check_rust_toolchain()
    def test_unrecognized_output_is_not_silently_accepted(self):
        with self.assertRaisesRegex(RuntimeError, 'Cannot determine'):
            self.run_versions('unexpected output', 'cargo 1.85.0 (build)')

if __name__ == '__main__': unittest.main()
