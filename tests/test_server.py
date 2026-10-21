import bootstrap
import json
import threading
import unittest
import urllib.error
import urllib.request
from server import Service


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=Service(port=0)
        threading.Thread(target=cls.service.http.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.service.http.shutdown();cls.service.http.server_close()

    def request(self,path,data=None,token=True,origin=None):
        headers={}
        if token:headers['X-App-Token']=self.service.token
        if origin:headers['Origin']=origin
        request=urllib.request.Request(self.service.base+path,data=json.dumps(data or {}).encode() if data is not None else None,headers=headers)
        return urllib.request.urlopen(request,timeout=5)

    def test_health_and_frontend_resources(self):
        with self.request('/health') as response:
            self.assertEqual(json.load(response)['product'],'CunZoom')
        with self.request('/') as response:
            page=response.read().decode()
            self.assertIn('Phòng Zoom',page)
            self.assertNotIn('__TOKEN__',page)
            self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])

    def test_state_requires_token_and_same_origin(self):
        with self.assertRaises(urllib.error.HTTPError) as result:self.request('/status',{},token=False)
        self.assertEqual(result.exception.code,403)

    def test_local_design_assets_and_no_font_path_traversal(self):
        for path in ['/tokens.css', '/fonts.css', '/fonts/inter-400.ttf', '/fonts/space-grotesk-700.ttf']:
            with self.request(path) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(len(response.read()), 100)
        for path in ['/fonts/../../src/server.py', '/fonts/unknown.ttf']:
            with self.assertRaises(urllib.error.HTTPError) as result:self.request(path)
            self.assertEqual(result.exception.code,404)
        with self.assertRaises(urllib.error.HTTPError) as result:self.request('/status',{},origin='https://evil.example')
        self.assertEqual(result.exception.code,403)

    def test_credentials_and_arbitrary_paths_are_not_web_assets(self):
        for path in ['/quyen_zoom.dpapi','/calendar.dpapi','/../src/server.py','/session.json']:
            with self.assertRaises(urllib.error.HTTPError) as result:self.request(path)
            self.assertEqual(result.exception.code,404)

    def test_bot_requires_explicit_consent(self):
        import vault
        vault.save(self.service.vault,{'client_id':'synthetic','client_secret':'synthetic','public_client_id':'synthetic'})
        try:
            with self.assertRaises(ValueError) as result:self.service.action('/start-bot',{'meeting_id':'12345678901'})
            self.assertIn('xác nhận',str(result.exception).lower())
        finally:self.service.vault.unlink(missing_ok=True)

    def test_no_arbitrary_file_reader(self):
        with self.assertRaises(ValueError):self.service.action('/library/read',{'id':'C:/Windows/win.ini','kind':'transcript'})


if __name__=='__main__':unittest.main()
