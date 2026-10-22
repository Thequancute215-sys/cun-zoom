import bootstrap
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import paths


class WindowsUpgradeTests(unittest.TestCase):
    def test_v1_vaults_are_copied_and_sources_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)
            (data/'quyen_zoom.dpapi').write_bytes(b'v1-zoom')
            (data/'calendar.dpapi').write_bytes(b'v1-calendar')
            with patch.object(paths,'DESKTOP',True),patch.object(paths,'DATA',data):
                paths.migrate_legacy()
            self.assertEqual((data/'zoom.vault').read_bytes(),b'v1-zoom')
            self.assertEqual((data/'calendar.vault').read_bytes(),b'v1-calendar')
            self.assertTrue((data/'quyen_zoom.dpapi').is_file())
            self.assertTrue((data/'calendar.dpapi').is_file())

    def test_existing_v2_vault_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)
            (data/'quyen_zoom.dpapi').write_bytes(b'v1-zoom')
            (data/'zoom.vault').write_bytes(b'v2-zoom')
            with patch.object(paths,'DESKTOP',True),patch.object(paths,'DATA',data):
                paths.migrate_legacy()
            self.assertEqual((data/'zoom.vault').read_bytes(),b'v2-zoom')

    def test_docker_and_linux_never_adopt_v1_files(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)
            (data/'quyen_zoom.dpapi').write_bytes(b'v1-zoom')
            with patch.object(paths,'DESKTOP',False),patch.object(paths,'DATA',data):
                paths.migrate_legacy()
            self.assertFalse((data/'zoom.vault').exists())

    def test_v1_data_folder_keeps_v1_lesson_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'HocTap_Zoom';data=root/'Du_lieu_ung_dung';data.mkdir(parents=True)
            with patch.object(paths,'DESKTOP',True),patch.object(paths,'DATA',data.resolve()),patch.object(paths,'V1_ROOT',root),patch.object(paths,'V1_DATA',data),patch.dict(os.environ,{},clear=False):
                os.environ.pop('CUN_ZOOM_RECORDINGS_DIR',None)
                self.assertEqual(paths.default_recordings(),root)

    def test_new_install_uses_its_own_lesson_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory).resolve()
            with patch.object(paths,'DESKTOP',False),patch.object(paths,'DATA',data),patch.dict(os.environ,{},clear=False):
                os.environ.pop('CUN_ZOOM_RECORDINGS_DIR',None)
                self.assertEqual(paths.default_recordings(),data/'lessons')


if __name__=='__main__':
    unittest.main()
