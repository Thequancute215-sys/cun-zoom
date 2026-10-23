"""Commercial account sessions stay in the local encrypted vault, never browser storage."""
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from paths import DATA, RESOURCES
import vault


class AccountError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configuration():
    path = RESOURCES / 'accounts-config.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    # A distributed commercial executable uses its bundled origin, not a user environment override.
    if not getattr(sys, 'frozen', False) and os.environ.get('CUN_ZOOM_ACCOUNTS_URL'):
        config = {'url': os.environ['CUN_ZOOM_ACCOUNTS_URL']}
    url = config.get('url', '')
    if not url and not path.exists():
        return ''
    parsed = urllib.parse.urlsplit(url)
    local = not getattr(sys, 'frozen', False) and parsed.hostname in ('localhost', '127.0.0.1')
    if not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or (parsed.scheme != 'https' and not (local and parsed.scheme == 'http')):
        raise AccountError('Địa chỉ dịch vụ tài khoản trong bản phát hành không hợp lệ.')
    return url


class Client:
    def __init__(self):
        self.url = configuration()
        self.path = DATA / 'account.vault'
        self.lock = threading.RLock()
        self.checked_until = 0
        self.message = ''
        self.credentials = vault.load(self.path) if self.url else {}
        if self.credentials.get('origin') != self.url:
            self.credentials = {}

    @property
    def enabled(self):
        return bool(self.url)

    def save(self):
        self.credentials['origin'] = self.url
        vault.save(self.path, self.credentials)

    def request(self, route, data):
        headers = {'Content-Type': 'application/json'}
        if self.credentials.get('token'):
            headers['Authorization'] = 'Bearer ' + self.credentials['token']
        req = urllib.request.Request(self.url + '/api/' + route, json.dumps(data).encode(), headers)
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=10) as response:
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise AccountError('Phản hồi dịch vụ tài khoản quá lớn.')
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise AccountError('Phản hồi dịch vụ tài khoản không hợp lệ.')
                return result
        except urllib.error.HTTPError as error:
            if error.code == 401:
                self.credentials.pop('token', None)
                self.checked_until = 0
                self.save()
            try:
                value = json.loads(error.read(8192)).get('error')
            except (ValueError, AttributeError):
                value = None
            raise AccountError(value if isinstance(value, str) and len(value) < 300 else 'Dịch vụ tài khoản từ chối yêu cầu.') from None
        except (OSError, ValueError) as error:
            if isinstance(error, AccountError):
                raise
            raise AccountError('Không kết nối được dịch vụ bản quyền. Kiểm tra mạng rồi thử lại.') from None

    def authorized(self):
        if not self.enabled:
            return True
        with self.lock:
            if time.monotonic() < self.checked_until:
                return True
            if not all(self.credentials.get(k) for k in ('token', 'device_id', 'license_id')):
                return False
            try:
                result = self.request('licenses/check', {k: self.credentials[k] for k in ('device_id', 'license_id')})
                if result.get('active') is not True or result.get('license_id') != self.credentials['license_id']:
                    raise AccountError('Bản quyền chưa được xác nhận.')
                remaining = float(result['expires']) - time.time()
                if remaining <= 0:
                    raise AccountError('Bản quyền đã hết hạn.')
                self.checked_until = time.monotonic() + min(60, remaining)
                self.message = ''
                return True
            except (AccountError, KeyError, TypeError, ValueError):
                self.checked_until = 0
                self.message = 'Cần đăng nhập/kích hoạt lại hoặc kiểm tra kết nối bản quyền.'
                return False

    def require(self):
        if not self.authorized():
            raise AccountError(self.message or 'Đăng nhập và kích hoạt bản quyền trước khi sử dụng.')

    def status(self):
        return {'enabled': self.enabled, 'active': self.authorized(),
                'signed_in': bool(self.credentials.get('token')), 'identity': self.credentials.get('identity', ''),
                'message': self.message, 'device_id': self.credentials.get('device_id', '')}

    def action(self, route, data):
        with self.lock:
            if not self.enabled:
                raise AccountError('Bản này chưa cấu hình dịch vụ tài khoản.')
            if route == 'status':
                return self.status()
            if route == 'otp/request':
                return self.request(route, {'identity': data.get('identity')})
            if route == 'otp/verify':
                result = self.request(route, {'challenge': data.get('challenge'), 'code': data.get('code'), 'client': 'desktop'})
                token = result.get('token')
                if not isinstance(token, str) or len(token) != 64:
                    raise AccountError('Dịch vụ chưa cấp phiên đăng nhập hợp lệ.')
                previous = self.credentials
                self.credentials = {'token': token, 'identity': result['identity'],
                                    'device_id': previous.get('device_id') or uuid.uuid4().hex}
                if previous.get('identity') == result['identity'] and previous.get('license_id'):
                    self.credentials['license_id'] = previous['license_id']
                self.checked_until = 0
                self.save()
                return {'identity': result['identity']}
            if route == 'logout':
                try:
                    if self.credentials.get('token'):
                        self.request(route, {})
                finally:
                    self.credentials = {'device_id': self.credentials.get('device_id') or uuid.uuid4().hex}
                    self.checked_until = 0
                    self.save()
                return {'ok': True}
            if route == 'devices/activate':
                result = self.request(route, {'license_id': data.get('license_id'),
                                             'device_id': self.credentials.get('device_id'),
                                             'name': str(data.get('name') or socket.gethostname())[:80]})
                self.credentials['license_id'] = result['license_id']
                self.checked_until = 0
                self.save()
                self.require()
                return {'ok': True}
            if route in ('me', 'licenses/key', 'licenses/redeem', 'devices/remove'):
                result = self.request(route, data)
                if route == 'devices/remove':
                    self.checked_until = 0
                return result
            raise AccountError('Không tìm thấy thao tác tài khoản.')
