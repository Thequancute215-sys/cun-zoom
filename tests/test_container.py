import bootstrap
import base64
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
import zipfile

import access_control
import library
import vault
from server import Service


class PortableVaultTests(unittest.TestCase):
    def test_authenticated_encryption_persists_and_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'zoom.vault';key=Path(directory)/'vault.key'
            from cryptography.fernet import Fernet
            key.write_bytes(Fernet.generate_key())
            with patch.object(vault,'WINDOWS',False),patch.dict(os.environ,{'CUN_ZOOM_KEY_FILE':str(key)}):
                vault.save(target,{'secret':'synthetic-private-value'})
                self.assertNotIn(b'synthetic-private-value',target.read_bytes())
                self.assertEqual(vault.load(target)['secret'],'synthetic-private-value')
                raw=bytearray(target.read_bytes());raw[len(raw)//2]^=1;target.write_bytes(raw)
                with self.assertRaises(ValueError):vault.load(target)
                key.unlink()
                with self.assertRaises(ValueError):vault.load(target)
                with self.assertRaises(ValueError):vault.save(target,{'secret':'no-fallback'})


class ContainerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        password=Path(self.directory.name)/'access.txt'
        password.write_text('synthetic-container-password-123456789')
        self.patches=[patch.object(access_control,'CONTAINER',True),patch('server.CONTAINER',True),
                      patch.dict(os.environ,{'CUN_ZOOM_ACCESS_KEY_FILE':str(password)})]
        for item in self.patches:item.start()
        self.service=Service(port=0)
        self.credentials='Basic '+base64.b64encode(b'cunzoom:synthetic-container-password-123456789').decode()
        threading.Thread(target=self.service.http.serve_forever,daemon=True).start()

    def tearDown(self):
        self.service.http.shutdown();self.service.http.server_close()
        for item in reversed(self.patches):item.stop()
        self.directory.cleanup()

    def request(self,path,body=None,auth=True,token=True,origin=None,host=None):
        headers={}
        if auth:headers['Authorization']=self.credentials
        if token:headers['X-App-Token']=self.service.token
        if origin:headers['Origin']=origin
        if host:headers['Host']=host
        req=urllib.request.Request(self.service.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        return urllib.request.urlopen(req,timeout=5)

    def test_html_and_api_require_login_but_health_has_no_private_data(self):
        for path,body in [('/',None),('/status',{}),('/app.js',None),('/library/download?id=anything',None)]:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request(path,body,auth=False)
            self.assertEqual(caught.exception.code,401)
        with self.request('/health',auth=False) as response:
            self.assertEqual(set(json.load(response)),{'product','version'})
        with self.request('/') as response:self.assertIn(self.service.token,response.read().decode())
        for path in ['/zoom.vault','/calendar.vault','/vault.key','/access-password.txt']:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request(path)
            self.assertEqual(caught.exception.code,404)

    def test_login_does_not_bypass_token_origin_or_host(self):
        for kwargs in [{'token':False},{'origin':'https://attacker.example'},{'host':'attacker.example'}]:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/status',{},**kwargs)
            self.assertEqual(caught.exception.code,403)
        with self.request('/status',{},origin=self.service.base) as response:self.assertTrue(json.load(response)['container'])

    def test_download_is_scoped_to_known_lesson(self):
        folder=Path(self.directory.name)/'lessons'/'Demo'/'Session'
        (folder/'01_Tai_lieu_goc').mkdir(parents=True)
        (folder/'buoi_hoc.json').write_text('{"subject":"Demo","title":"Session"}')
        (folder/'01_Tai_lieu_goc/am_thanh.wav').write_bytes(b'synthetic-test-audio')
        with patch.object(library,'preferences',return_value={'recordings_root':str(folder.parent.parent)}):
            identifier=library.listing()[0]['id']
            with self.request('/library/download?id='+identifier) as response:
                import io
                with zipfile.ZipFile(io.BytesIO(response.read())) as zipped:
                    self.assertIn('01_Tai_lieu_goc/am_thanh.wav',zipped.namelist())
                    self.assertFalse(any('vault' in name for name in zipped.namelist()))
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/library/download?id=../../vault.key')
            self.assertEqual(caught.exception.code,400)

    def test_container_oauth_uses_fixed_origin_and_pkce(self):
        with patch('server.vault.load',return_value={'client_secret':'synthetic','public_client_id':'synthetic'}):
            from urllib.parse import parse_qs,urlsplit
            result=parse_qs(urlsplit(self.service.begin_oauth()).query)
        self.assertEqual(result['redirect_uri'],[self.service.base+'/oauth/callback'])
        self.assertEqual(result['code_challenge_method'],['S256'])
        self.assertIsNone(next(iter(self.service.pending.values()))['listener'])
