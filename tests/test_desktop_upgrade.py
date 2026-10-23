import bootstrap
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import paths
import runner
import transcribe


def icacls(*args):
    subprocess.run(['icacls',*map(str,args)],check=True,capture_output=True)


@unittest.skipUnless(os.name=='nt','Windows ACLs')
class SharedV1FolderTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.root=Path(directory.name)/'HocTap_Zoom';self.data=self.root/'Du_lieu_ung_dung';self.data.mkdir(parents=True)
        # Exactly the command the app shows the owner, aimed at this test folder.
        subprocess.run(paths.V1_LOCK.replace(str(paths.V1_ROOT),str(self.root)),check=True,capture_output=True)
        patcher=patch.multiple(paths,DESKTOP=True,V1_ROOT=self.root,V1_DATA=self.data);patcher.start();self.addCleanup(patcher.stop)

    def test_locked_v1_folder_is_adopted(self):
        self.assertTrue(paths.private_path(self.data))
        self.assertTrue(paths.v1_private())

    def test_folder_other_accounts_can_change_or_read_is_not_adopted(self):
        icacls(self.root,'/grant','*S-1-5-11:(OI)(CI)(M)')
        self.assertFalse(paths.private_path(self.data))
        self.assertFalse(paths.v1_private())
        icacls(self.root,'/remove:g','*S-1-5-11')
        self.assertTrue(paths.v1_private())
        icacls(self.data,'/grant','*S-1-5-32-545:(R)')
        self.assertFalse(paths.v1_private())

    def test_link_in_place_of_the_folder_is_not_adopted(self):
        target=self.root/'elsewhere';target.mkdir()
        self.data.rmdir();subprocess.run(['cmd','/c','mklink','/J',str(self.data),str(target)],check=True,capture_output=True)
        self.assertTrue(self.data.is_dir())
        self.assertFalse(paths.v1_private())

    def test_shared_v1_model_folder_is_not_used(self):
        models=self.root/'Cong_cu'/'models';models.mkdir(parents=True)
        self.assertEqual(transcribe.model_root(),models)
        icacls(models,'/grant','*S-1-5-11:(OI)(CI)(M)')
        self.assertEqual(transcribe.model_root(),paths.DATA/'models')


class SharedSdkTests(unittest.TestCase):
    def test_bot_refuses_an_sdk_other_accounts_could_have_placed(self):
        with tempfile.TemporaryDirectory() as directory:
            sdk=Path(directory).resolve()
            with patch.multiple(runner,EXE=Path(__file__),DESKTOP=True,SDK=sdk,MANAGED_SDK=sdk,sdk_present=lambda:True,private_path=lambda path:False):
                with self.assertRaisesRegex(ValueError,'không thuộc riêng'):runner.launch({},'jwt')

    @unittest.skipIf(os.name=='nt','POSIX')
    def test_private_path_is_windows_only(self):
        self.assertFalse(paths.private_path(Path.home()))


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
