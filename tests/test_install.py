from pathlib import Path
import tempfile
import unittest
import zipfile
from install import copy_data

class DataTests(unittest.TestCase):
    def test_only_data_is_copied_from_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'input.zip'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('nested/RESOURCE.MAP', b'map')
                archive.writestr('nested/RESOURCE.001', b'data')
                archive.writestr('../../run.sh', b'bad')
            copy_data(source, root / 'out')
            self.assertEqual({p.name for p in (root/'out').iterdir()}, {'RESOURCE.MAP', 'RESOURCE.001'})
            self.assertFalse((root/'run.sh').exists())
    def test_missing_resource_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            (source/'RESOURCE.MAP').write_bytes(b'map')
            with self.assertRaises(ValueError): copy_data(source, root/'out')

if __name__ == '__main__': unittest.main()
