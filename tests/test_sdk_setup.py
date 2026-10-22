import bootstrap
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import sdk_setup
import server
from server import Service

PACKAGE = 'zoom-sdk-csharp-wrapper-7.2.1.49056/'


def archive(path, extra=()):
    with zipfile.ZipFile(path, 'w') as bundle:
        bundle.writestr(PACKAGE + 'x64/bin/sdk.dll', b'x64-runtime')
        bundle.writestr(PACKAGE + 'x64/bin/ssb_sdk.dll', b'x64-helper')
        bundle.writestr(PACKAGE + 'x64/bin/ringtone/G Arpeggio.pcm', b'tone')
        bundle.writestr(PACKAGE + 'x64/zoom_sdk_c_sharp_wrap/h/zoom_sdk.h', b'header')
        bundle.writestr(PACKAGE + 'x86/bin/sdk.dll', b'x86-runtime')
        for name, data in extra:
            bundle.writestr(name, data)
    return path


class SdkSetupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_installs_only_the_x64_runtime(self):
        target = sdk_setup.install(archive(self.root / 'sdk.zip'), self.root / 'zoom-sdk')
        self.assertEqual((target / 'sdk.dll').read_bytes(), b'x64-runtime')
        self.assertTrue((target / 'ringtone/G Arpeggio.pcm').is_file())
        self.assertFalse((target / 'zoom_sdk_c_sharp_wrap').exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['sdk.zip', 'zoom-sdk'])

    def test_reinstall_replaces_previous_copy(self):
        target = self.root / 'zoom-sdk'
        target.mkdir()
        (target / 'stale.dll').write_bytes(b'old')
        sdk_setup.install(archive(self.root / 'sdk.zip'), target)
        self.assertFalse((target / 'stale.dll').exists())
        self.assertTrue((target / 'sdk.dll').is_file())

    def test_rejects_archive_without_windows_x64_runtime(self):
        path = self.root / 'other.zip'
        with zipfile.ZipFile(path, 'w') as bundle:
            bundle.writestr('zoom-meeting-sdk-linux/libmeetingsdk.so', b'linux')
        target = self.root / 'zoom-sdk'
        target.mkdir()
        (target / 'sdk.dll').write_bytes(b'kept')
        with self.assertRaises(ValueError):
            sdk_setup.install(path, target)
        self.assertEqual((target / 'sdk.dll').read_bytes(), b'kept')

    def test_rejects_file_that_is_not_a_zip(self):
        path = self.root / 'renamed.zip'
        path.write_bytes(b'not a zip archive')
        with self.assertRaises(ValueError):
            sdk_setup.install(path, self.root / 'zoom-sdk')
        self.assertFalse((self.root / 'zoom-sdk').exists())

    def test_rejects_path_traversal(self):
        path = archive(self.root / 'evil.zip', [(PACKAGE + 'x64/bin/../../../escape.dll', b'x')])
        with self.assertRaises(ValueError):
            sdk_setup.install(path, self.root / 'zoom-sdk')
        self.assertFalse((self.root / 'escape.dll').exists())

    def test_service_installs_into_managed_folder_only(self):
        managed = self.root / 'zoom-sdk'
        service = Service(port=0)
        try:
            service.choose_sdk_archive = lambda: str(archive(self.root / 'sdk.zip'))
            with patch.object(server, 'CONTAINER', False), patch.object(server, 'SDK', managed.resolve()), patch.object(server, 'MANAGED_SDK', managed):
                self.assertTrue(service.action('/sdk/install', {})['ok'])
            self.assertTrue((managed / 'sdk.dll').is_file())
            with patch.object(server, 'CONTAINER', False), patch.object(server, 'SDK', (self.root / 'elsewhere').resolve()), patch.object(server, 'MANAGED_SDK', managed):
                with self.assertRaises(ValueError):
                    service.action('/sdk/install', {})
            with patch.object(server, 'CONTAINER', True):
                with self.assertRaises(ValueError):
                    service.action('/sdk/install', {})
        finally:
            service.http.server_close()


if __name__ == '__main__':
    unittest.main()
