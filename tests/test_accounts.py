import bootstrap
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import account_client
import vault
from server import Service


class AccountClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, value in [('DATA', self.root)]:
            p = patch.object(account_client, name, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(account_client, 'configuration', return_value='https://accounts.example.com')
        p.start(); self.addCleanup(p.stop)
        self.client = account_client.Client()

    def test_login_stores_session_encrypted_and_never_returns_it_to_browser(self):
        token = 'a' * 64
        with patch.object(self.client, 'request', return_value={'token': token, 'identity': 'test@example.com'}):
            result = self.client.action('otp/verify', {'challenge': 'c', 'code': '123456'})
        self.assertNotIn('token', result)
        self.assertNotIn(token.encode(), self.client.path.read_bytes())
        saved = vault.load(self.client.path)
        self.assertEqual(saved['token'], token)
        self.assertEqual(saved['origin'], self.client.url)
        self.assertTrue(saved['device_id'])

    def test_device_activation_and_expiring_cache_require_server_confirmation(self):
        self.client.credentials = {'token': 'a'*64, 'identity': 'test@example.com', 'device_id': 'b'*32}
        with patch.object(self.client, 'request', side_effect=[{'license_id': 'license'}, {'active': True, 'license_id': 'license', 'expires': 2000}]), patch('account_client.time.time', return_value=1000), patch('account_client.time.monotonic', return_value=100):
            self.client.action('devices/activate', {'license_id': 'license', 'device_id': 'evil'})
        with patch.object(self.client, 'request', side_effect=account_client.AccountError('offline')) as request, patch.object(self.client, 'check_later') as later:
            with patch('account_client.time.monotonic', return_value=100):
                self.assertTrue(self.client.authorized()); later.assert_not_called()
            # Close to expiry the cached answer still holds while a background check renews it.
            with patch('account_client.time.monotonic', return_value=159):
                self.assertTrue(self.client.authorized()); later.assert_called_once()
            with patch('account_client.time.monotonic', return_value=161):
                self.assertFalse(self.client.authorized())
                request.assert_not_called()
                self.assertFalse(self.client.authorized(wait=True))
                request.assert_called_once()
            self.assertEqual(self.client.checked_until, 0)

    def test_background_check_never_blocks_and_backs_off_after_failure(self):
        self.client.credentials = {'token': 'a'*64, 'device_id': 'b'*32, 'license_id': 'license'}
        started, release = threading.Event(), threading.Event()
        def slow(*_):
            started.set(); release.wait(5)
            raise account_client.AccountError('offline')
        with patch.object(self.client, 'request', side_effect=slow) as request:
            self.assertFalse(self.client.authorized())
            self.assertTrue(started.wait(5))
            # A second caller during the slow check returns at once and starts no second request.
            self.assertFalse(self.client.authorized())
            release.set()
            with self.client.checking:pass
            self.assertEqual(request.call_count, 1)
            self.assertGreater(self.client.retry_at, 0)
            self.assertFalse(self.client.authorized())
            self.assertEqual(request.call_count, 1)

    def test_desktop_forwards_orders_but_never_admin_routes(self):
        with patch.object(self.client, 'request', return_value={'plans': []}) as request:
            for route in ('plans', 'orders/create', 'orders/cancel'):
                self.client.action(route, {'plan_id': 'p'})
                self.assertEqual(request.call_args[0][0], route)
            for route in ('admin/grant', 'admin/orders/approve', 'admin/overview'):
                with self.assertRaises(account_client.AccountError): self.client.action(route, {})
            self.assertEqual(request.call_count, 3)

    def test_expired_or_wrong_license_is_rejected(self):
        self.client.credentials = {'token': 'a'*64, 'device_id': 'b'*32, 'license_id': 'license'}
        for result in ({'active': True, 'license_id': 'other', 'expires': 9999999999}, {'active': True, 'license_id': 'license', 'expires': 0}, {'active': False}):
            with patch.object(self.client, 'request', return_value=result):
                self.assertFalse(self.client.authorized(wait=True))

    def test_logout_clears_local_session_even_when_network_fails(self):
        self.client.credentials = {'token': 'a'*64, 'device_id': 'b'*32, 'license_id': 'license'}
        with patch.object(self.client, 'request', side_effect=account_client.AccountError('offline')):
            with self.assertRaises(account_client.AccountError): self.client.action('logout', {})
        self.assertNotIn('token', vault.load(self.client.path))
        self.assertFalse(self.client.authorized())


class AccountConfigurationTests(unittest.TestCase):
    def test_commercial_config_cannot_silently_disable_auth_or_redirect_credentials(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(account_client, 'RESOURCES', Path(temp)), patch.dict('os.environ', {'CUN_ZOOM_ACCOUNTS_URL': ''}):
            target = Path(temp)/'accounts-config.json'
            self.assertEqual(account_client.configuration(), '')
            for url in ('', 'http://remote.example', 'https://user:password@example.com', 'https://example.com/path', 'https://example.com?x=1'):
                target.write_text(json.dumps({'url': url}))
                with self.assertRaises(account_client.AccountError): account_client.configuration()
            target.write_text('{"url":"https://accounts.example.com"}')
            self.assertEqual(account_client.configuration(), 'https://accounts.example.com')

    def test_packaged_app_ignores_environment_override(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(account_client, 'RESOURCES', Path(temp)), patch.object(account_client.sys, 'frozen', True, create=True), patch.dict('os.environ', {'CUN_ZOOM_ACCOUNTS_URL': 'http://localhost:1234'}):
            (Path(temp)/'accounts-config.json').write_text('{"url":"https://accounts.example.com"}')
            self.assertEqual(account_client.configuration(), 'https://accounts.example.com')


class CommercialHTTPTests(unittest.TestCase):
    def setUp(self):
        self.account = unittest.mock.Mock(enabled=True)
        self.account.authorized.return_value = False
        self.account.require.side_effect = account_client.AccountError('Kích hoạt bản quyền trước.')
        self.account.action.return_value = {'enabled': True, 'active': False}
        self.account.status.return_value = {'enabled': True, 'active': False, 'signed_in': False}
        self.account.message = ''
        p = patch('server.account_client.Client', return_value=self.account); p.start(); self.addCleanup(p.stop)
        self.service = Service(port=0)
        threading.Thread(target=self.service.http.serve_forever, daemon=True).start()
        self.addCleanup(self.service.http.server_close)
        self.addCleanup(self.service.http.shutdown)

    def request(self, path, data=None):
        headers = {'X-App-Token': self.service.token, 'Content-Type': 'application/json'}
        return urllib.request.urlopen(urllib.request.Request(self.service.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers), timeout=5)

    def test_without_licence_lessons_stay_readable_and_only_paid_work_is_refused(self):
        with self.request('/') as response: self.assertIn('calendar-form', response.read().decode())
        with self.request('/account') as response:
            page = response.read().decode()
            self.assertIn('identity-form', page); self.assertIn('content="desktop"', page)
        with self.request('/status', {}) as response:
            status = json.load(response)
            self.assertFalse(status['account']['active']); self.assertIn('library', status)
        for path in ('/study/overview', '/ai/settings'):
            with self.request(path, {}) as response: self.assertEqual(response.status, 200)
        for path, data in (('/start-bot', {}), ('/sdk-test', {}), ('/study/run', {}), ('/study/upload', {}), ('/calendar/toggle', {'enabled': True})):
            with self.assertRaises(urllib.error.HTTPError) as caught: self.request(path, data)
            self.assertEqual(caught.exception.code, 402, path)
        with self.request('/account/status', {}) as response: self.assertFalse(json.load(response)['active'])
        with patch('server.runner.stop') as stop:
            self.service.action('/stop-bot', {}); stop.assert_called_once()

    def test_lapsed_licence_never_stops_a_running_recording(self):
        with patch('server.runner.shutdown') as shutdown, patch('server.runner.stop') as stop, \
                patch('server.runner.state', return_value={'running': True}), patch.object(self.service.calendar, 'start'), patch.object(self.service.study, 'start'), \
                patch.object(self.service.http, 'serve_forever'):
            self.service.start()
            threading.Event().wait(0.2)
            shutdown.assert_not_called(); stop.assert_not_called()

    def test_valid_license_unlocks_original_ui_and_actions(self):
        self.account.authorized.return_value = True
        self.account.require.side_effect = None
        with self.request('/') as response: self.assertIn('calendar-form', response.read().decode())
        with self.request('/parse-room', {'meeting_link': 'https://zoom.us/j/12345678901'}) as response:
            self.assertEqual(response.status, 200)

    def test_account_routes_still_require_local_csrf_token(self):
        req = urllib.request.Request(self.service.base+'/account/otp/verify', data=b'{}')
        with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(req, timeout=5)
        self.assertEqual(caught.exception.code, 403)
