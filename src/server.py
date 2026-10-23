"""Authenticated loopback API for the desktop window; no remote control listener."""
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import calendar_watch
import account_client
import library
import runner
import vault
import access_control
import ai_backend
import platform_actions
import sdk_setup
import study
from paths import DATA, RESOURCES, WEB, VERSION, REPOSITORY, SDK, MANAGED_SDK, NATIVE, PREFERENCES, preferences, CONTAINER, sdk_present
from room_link import parse_room_link


UPLOAD_LIMIT = 2 * 1024 ** 3


def pkce(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')


def jwt_for_sdk(client_id, secret):
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip('=')
    now = int(time.time()) - 30
    head = encode(b'{"alg":"HS256","typ":"JWT"}')
    body = encode(json.dumps({'appKey': client_id, 'iat': now, 'exp': now+3600, 'tokenExp': now+3600}, separators=(',', ':')).encode())
    value = head + '.' + body
    return value + '.' + encode(hmac.new(secret.encode(), value.encode(), hashlib.sha256).digest())


def token_request(config, parameters):
    client = config.get('public_client_id', '')
    if not client:
        raise ValueError('Thêm Public client ID trong cấu hình Zoom trước khi kết nối.')
    request = urllib.request.Request('https://zoom.us/oauth/token', data=urllib.parse.urlencode({**parameters, 'client_id': client}).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise ValueError('Zoom chưa cấp quyền (HTTP '+str(error.code)+'). Kiểm tra cấu hình hoặc kết nối lại.') from None
    except Exception:
        raise ValueError('Không kết nối được Zoom. Kiểm tra mạng rồi thử lại.') from None


class Service:
    def __init__(self, port=18766, host='127.0.0.1'):
        self.lock = threading.RLock()
        self.account = account_client.Client()
        self.license_stop = threading.Event()
        self.token = secrets.token_urlsafe(32)
        self.vault = DATA / 'zoom.vault'
        self.calendar = calendar_watch.Watcher()
        self.study = study.Engine()
        self.calendar.authorized = self.account.authorized
        self.study.authorized = self.account.authorized
        self.pending = {}
        self.show_window = lambda: None
        self.choose_folder = lambda: None
        self.choose_sdk_archive = lambda: None
        self.quit_app = lambda: None
        self.message = ''
        self.model_state = 'idle'
        self.http = ThreadingHTTPServer((host, port), self.handler())
        self.port = self.http.server_port
        self.base = os.environ.get('PUBLIC_ORIGIN', f'http://127.0.0.1:{self.port}').rstrip('/')
        origin = urllib.parse.urlsplit(self.base)
        if origin.scheme not in ('http', 'https') or not origin.netloc or origin.path or origin.query or origin.fragment or origin.username:
            self.http.server_close()
            raise ValueError('PUBLIC_ORIGIN phải là origin HTTP(S), không có đường dẫn hoặc thông tin đăng nhập.')
        self.allowed_hosts = {origin.netloc, f'127.0.0.1:{self.port}'}
        if CONTAINER:
            access_control.access_password()

    def status(self):
        config = vault.load(self.vault)
        recordings = library.listing()
        return {'version': VERSION, 'account': self.account.status(), 'calendar': self.calendar.status(), 'native': runner.state(),
                'zoom': {'configured': bool(config.get('client_secret')), 'authorized': bool(config.get('oauth', {}).get('refresh_token')),
                         'client_id': config.get('client_id', ''), 'public_client_id': config.get('public_client_id', ''),
                         'default_passcode': config.get('default_meeting_passcode', ''),
                         'sdk_available': NATIVE.is_file() and sdk_present(), 'sdk_installed': sdk_present(),
                         'sdk_installable': not CONTAINER and SDK == MANAGED_SDK.resolve(), 'sdk_version': sdk_setup.TESTED_VERSION,
                         'external_review_verified': False},
                'library': recordings, 'preferences': preferences(), 'message': self.message,
                'model': {'state': self.model_state, 'available': self.model_available()},
                'data_directory': str(DATA), 'container': CONTAINER,
                'browser_events': platform_actions.events(),
                'oauth_redirect': self.base + '/oauth/callback' if CONTAINER else 'Cổng loopback ngẫu nhiên trên Windows'}

    def model_available(self):
        from transcribe import model_root
        return any(model_root().glob('models--Systran--faster-whisper-base/snapshots/*/model.bin'))

    def download_model(self):
        if self.model_state == 'downloading':
            return
        self.model_state = 'downloading'
        def job():
            try:
                from huggingface_hub import snapshot_download
                from transcribe import model_root
                snapshot_download('Systran/faster-whisper-base', cache_dir=str(model_root()), allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*'])
                self.model_state = 'ready'
            except Exception:
                self.model_state = 'failed'
        threading.Thread(target=job, daemon=True).start()

    def begin_oauth(self):
        config = vault.load(self.vault)
        if not config.get('client_secret') or not config.get('public_client_id'):
            raise ValueError('Lưu Client ID, Client Secret và Public client ID của ứng dụng Zoom trước.')
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        listener = None if CONTAINER else ThreadingHTTPServer(('127.0.0.1', 0), self.handler())
        if listener:
            listener.oauth_listener = True
        redirect = self.base + '/oauth/callback' if CONTAINER else f'http://127.0.0.1:{listener.server_port}/oauth/callback'
        with self.lock:
            for entry in self.pending.values():
                if entry['listener']:
                    threading.Thread(target=entry['listener'].shutdown, daemon=True).start()
            self.pending = {state: {'verifier': verifier, 'redirect': redirect, 'expires': time.time()+600, 'listener': listener}}
        def listen():
            try:
                listener.serve_forever()
            finally:
                listener.server_close()
        if listener:
            threading.Thread(target=listen, daemon=True).start()
            timer = threading.Timer(600, listener.shutdown)
            timer.daemon = True
            timer.start()
        return 'https://zoom.us/oauth/authorize?' + urllib.parse.urlencode({'response_type': 'code', 'client_id': config['public_client_id'], 'redirect_uri': redirect, 'state': state, 'code_challenge': pkce(verifier), 'code_challenge_method': 'S256'})

    def oauth_callback(self, query):
        state = query.get('state', [''])[0]
        with self.lock:
            entry = self.pending.pop(state, None)
            if not entry or entry['expires'] < time.time():
                raise ValueError('Phiên kết nối đã hết hạn; bắt đầu lại từ ứng dụng.')
            if query.get('error') or not query.get('code'):
                raise ValueError('Zoom chưa được cấp quyền. Có thể kết nối lại khi sẵn sàng.')
            config = vault.load(self.vault)
            tokens = token_request(config, {'grant_type': 'authorization_code', 'code': query['code'][0], 'redirect_uri': entry['redirect'], 'code_verifier': entry['verifier']})
            if not tokens.get('access_token') or not tokens.get('refresh_token'):
                raise ValueError('Zoom chưa trả đủ thông tin cấp quyền.')
            tokens['expires_at'] = time.time() + tokens.get('expires_in', 3600)
            config['oauth'] = tokens
            vault.save(self.vault, config)
            self.message = 'Đã kết nối quyền Zoom trên máy này.'

    def action(self, route, data):
        if route.startswith('/account/'):
            return self.account.action(route[len('/account/'):], data)
        if route not in ('/stop-bot', '/app/quit', '/app/show'):
            self.account.require()
        if route == '/status':
            return self.status()
        if route == '/parse-room':
            return parse_room_link(data.get('meeting_link', ''))
        if route == '/calendar/configure':
            self.calendar.configure(data)
            self.calendar.sync()
            return self.calendar.status()
        if route == '/calendar/sync':
            self.calendar.sync()
            return self.calendar.status()
        if route == '/calendar/toggle':
            with self.calendar.lock:
                if not self.calendar.config.get('feed_url'):
                    raise ValueError('Kết nối lịch học trước khi bật theo dõi.')
                self.calendar.config['enabled'] = data.get('enabled') is True
                vault.save(self.calendar.path, self.calendar.config)
            return self.calendar.status()
        if route == '/calendar/open':
            event = self.calendar.event(data.get('key', ''))
            if not CONTAINER:
                self.calendar.open_event(data.get('key', ''))
            return {'ok': True, 'url': event['link'] if CONTAINER else None}
        if route == '/settings/zoom':
            with self.lock:
                config = vault.load(self.vault)
                cid = str(data.get('client_id', '')).strip()
                public = str(data.get('public_client_id', '')).strip()
                secret = str(data.get('client_secret', '')).strip() or config.get('client_secret', '')
                if not cid or not public or not secret or max(len(cid), len(public), len(secret)) > 500:
                    raise ValueError('Cần đủ Client ID, Client Secret và Public client ID hợp lệ.')
                changed = config.get('client_id') != cid or config.get('client_secret') != secret
                if config.get('client_id') and config['client_id'] != cid:
                    config.pop('oauth', None)
                config.update(client_id=cid, public_client_id=public, client_secret=secret, default_meeting_passcode=str(data.get('default_passcode', ''))[:256])
                vault.save(self.vault, config)
                if changed:
                    with runner.MUTEX:
                        runner.CURRENT['auth_test_passed'] = False
                        runner.persist()
            return {'ok': True}
        if route in ('/sdk-test', '/start-bot', '/zoom/connect', '/zoom/disconnect'):
            config = vault.load(self.vault)
            if route == '/zoom/connect':
                url = self.begin_oauth()
                if not CONTAINER:
                    platform_actions.open_url(url)
                return {'ok': True, 'url': url if CONTAINER else None}
            if route == '/zoom/disconnect':
                config.pop('oauth', None)
                vault.save(self.vault, config)
                return {'ok': True}
            if not config.get('client_id') or not config.get('client_secret'):
                raise ValueError('Kết nối ứng dụng Zoom trong Cài đặt trước.')
            if route == '/sdk-test':
                runner.launch(config, jwt_for_sdk(config['client_id'], config['client_secret']))
                return {'ok': True}
            if data.get('consent') is not True:
                raise ValueError('Xác nhận đã vào đúng lớp và được phép ghi trước khi bắt đầu.')
            if not runner.state().get('auth_test_passed'):
                raise ValueError('Bấm Kiểm tra Zoom trong Cài đặt trước khi vào lớp.')
            room = str(data.get('meeting_id', '')).replace(' ', '').replace('-', '')
            if data.get('meeting_link'):
                linked = parse_room_link(data['meeting_link'])['meeting_id']
                if room and room != linked:
                    raise ValueError('ID khác với link phòng; bấm Đọc link để cập nhật.')
                room = linked
            runner.access(config, token_request, self.vault)
            runner.launch(config, jwt_for_sdk(config['client_id'], config['client_secret']), mode='join', meeting=room,
                          password=str(data.get('password', '')), subject=data.get('subject', ''), title=data.get('title', ''), consent=True)
            return {'ok': True}
        if route == '/stop-bot':
            runner.stop()
            return {'ok': True}
        if route == '/library/open':
            if CONTAINER:
                library.find(data.get('id', ''))
                return {'ok': True, 'download': '/library/download?id='+urllib.parse.quote(data['id'])}
            library.open_folder(data.get('id', ''))
            return {'ok': True}
        if route == '/library/read':
            return {'text': library.read(data.get('id', ''), data.get('kind', ''))}
        if route == '/model/download':
            self.download_model()
            return {'ok': True}
        if route == '/app/show':
            self.show_window()
            return {'ok': True}
        if route == '/app/releases':
            url = f'https://github.com/{REPOSITORY}/releases'
            if not CONTAINER:
                platform_actions.open_url(url)
            return {'ok': True, 'url': url if CONTAINER else None}
        if route == '/app/folder':
            if CONTAINER:
                raise ValueError('Docker lưu bài trong volume /data/lessons. Dùng nút Tải buổi học hoặc xem hướng dẫn sao lưu.')
            selected = self.choose_folder()
            if selected:
                folder = Path(selected).resolve()
                folder.mkdir(parents=True, exist_ok=True)
                config = preferences()
                config['recordings_root'] = str(folder)
                PREFERENCES.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
            return {'ok': True}
        if route == '/sdk/install':
            if CONTAINER:
                raise ValueError('Docker dùng SDK Linux đặt trong vendor/zoom-linux; xem docs/INSTALL.md.')
            if SDK != MANAGED_SDK.resolve():
                raise ValueError('SDK đang được chỉ định tại ' + str(SDK) + '; ứng dụng không cài đè thư mục này.')
            if runner.state().get('running'):
                raise ValueError('Dừng bot trước khi cài lại Zoom SDK.')
            selected = self.choose_sdk_archive()
            if not selected:
                return {'ok': False}
            sdk_setup.install(selected, SDK)
            self.message = 'Đã cài Zoom SDK. Bấm Kiểm tra Zoom để thử.'
            return {'ok': True}
        if route == '/ai/settings':
            return ai_backend.public_settings()
        if route == '/ai/save':
            settings = ai_backend.save(data)
            self.study.kick()
            return settings
        if route == '/ai/test':
            ai_backend.test()
            return {'ok': True}
        if route == '/study/overview':
            return study.overview(self.study)
        if route == '/study/subject':
            return study.subject_detail(data.get('name', ''))
        if route == '/study/exam':
            return study.exam(study.subject_dir(data.get('subject', '')), data.get('id', ''))
        if route == '/study/run':
            kind = data.get('kind')
            if kind == 'sync':
                self.study.request('subject', data.get('subject', ''))
            elif kind == 'outline':
                self.study.request('outline', data.get('subject', ''))
            elif kind == 'exam':
                mix = data.get('mix', 'can_bang')
                if mix not in study.MIX:
                    raise ValueError('Mức độ đề không hợp lệ.')
                self.study.request('exam', data.get('subject', ''), multiple_choice=int(data.get('multiple_choice', 20)), essays=int(data.get('essays', 3)), mix=mix)
            else:
                raise ValueError('Thao tác không được hỗ trợ.')
            return {'ok': True}
        if route == '/study/open':
            folder = study.subject_paths(study.subject_dir(data.get('subject', '')))['folder']
            folder.mkdir(parents=True, exist_ok=True)
            if CONTAINER:
                return {'ok': True, 'download': '/study/download?subject=' + urllib.parse.quote(folder.parent.name)}
            platform_actions.open_folder(folder)
            return {'ok': True}
        if route == '/app/quit':
            threading.Thread(target=self.quit_app, daemon=True).start()
            return {'ok': True}
        raise ValueError('Thao tác không được hỗ trợ.')

    def handler(self):
        service = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def valid_host(self):
                hosts = service.allowed_hosts | {f'127.0.0.1:{self.server.server_port}'}
                return self.headers.get('Host') in hosts

            def authenticated(self):
                if access_control.allowed(self.headers.get('Authorization', '')):
                    return True
                self.send_response(401)
                self.headers_common()
                self.send_header('WWW-Authenticate', 'Basic realm="Cun Zoom", charset="UTF-8"')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return False

            def headers_common(self):
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")

            def reply(self, value, status=200):
                raw = json.dumps(value, ensure_ascii=False).encode()
                self.send_response(status)
                self.headers_common()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if not self.valid_host():
                    return self.reply({'error': 'Host không hợp lệ.'}, 403)
                route = urllib.parse.urlsplit(self.path).path
                if route == '/health':
                    return self.reply({'product': 'CunZoom', 'version': VERSION})
                if not self.authenticated():
                    return
                if route in ('/library/download', '/study/download', '/oauth/callback') and not service.account.authorized():
                    return self.reply({'error': 'Vui lòng kích hoạt bản quyền.'}, 402)
                if route == '/library/download' and CONTAINER:
                    try:
                        identifier = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('id', [''])[0]
                        with library.archive(identifier) as packed:
                            self.send_response(200)
                            self.headers_common()
                            self.send_header('Content-Type', 'application/zip')
                            self.send_header('Content-Disposition', 'attachment; filename="cun-zoom-lesson.zip"')
                            self.send_header('Content-Length', str(packed.seek(0, 2)))
                            self.end_headers()
                            packed.seek(0)
                            import shutil
                            shutil.copyfileobj(packed, self.wfile)
                    except ValueError as error:
                        return self.reply({'error': str(error)}, 400)
                    return
                if route == '/study/download' and CONTAINER:
                    try:
                        subject = study.subject_dir(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('subject', [''])[0])
                        with library.archive_folder(study.subject_paths(subject)['folder']) as packed:
                            self.send_response(200)
                            self.headers_common()
                            self.send_header('Content-Type', 'application/zip')
                            self.send_header('Content-Disposition', 'attachment; filename="cun-zoom-on-tap.zip"')
                            self.send_header('Content-Length', str(packed.seek(0, 2)))
                            self.end_headers()
                            packed.seek(0)
                            import shutil
                            shutil.copyfileobj(packed, self.wfile)
                    except ValueError as error:
                        return self.reply({'error': str(error)}, 400)
                    return
                if route == '/oauth/callback':
                    try:
                        service.oauth_callback(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query))
                    except ValueError as error:
                        service.message = str(error)
                    except Exception:
                        service.message = 'Kết nối Zoom chưa hoàn tất. Thử lại trong Cài đặt.'
                    raw = '<!doctype html><meta charset="utf-8"><title>Cún Zoom</title><p>Đã xử lý kết nối. Quay lại cửa sổ Cún Zoom để xem kết quả.</p>'.encode()
                    self.send_response(200)
                    self.headers_common()
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(raw)
                    if getattr(self.server, 'oauth_listener', False):
                        threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                known = {'/': 'index.html', '/app.js': 'app.js', '/study.js': 'study.js', '/style.css': 'style.css', '/logo.svg': 'logo.svg',
                         '/tokens.css': 'tokens.css', '/fonts.css': 'fonts.css'}
                known.update({'/account': 'account.html', '/account.js': 'account.js', '/account.css': 'account.css'})
                if route == '/' and service.account.enabled and not service.account.authorized():
                    known['/'] = 'account.html'
                for font in ('inter-400.ttf', 'inter-500.ttf', 'inter-600.ttf', 'inter-700.ttf',
                             'space-grotesk-500.ttf', 'space-grotesk-700.ttf', 'jetbrains-mono-400.ttf'):
                    known['/fonts/'+font] = 'fonts/'+font
                if route not in known:
                    return self.reply({'error': 'Không tìm thấy.'}, 404)
                target = WEB / known[route]
                raw = target.read_bytes()
                if route in ('/', '/account'):
                    raw = raw.replace(b'__TOKEN__', service.token.encode()).replace(b'__MODE__', b'desktop')
                self.send_response(200)
                self.headers_common()
                self.send_header('Content-Type', (mimetypes.guess_type(target.name)[0] or 'text/plain')+'; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                if not self.authenticated():
                    return
                if not self.valid_host() or self.headers.get('X-App-Token') != service.token:
                    return self.reply({'error': 'Phiên ứng dụng không hợp lệ.'}, 403)
                if self.headers.get('Origin') not in (None, service.base):
                    return self.reply({'error': 'Nguồn yêu cầu không hợp lệ.'}, 403)
                if urllib.parse.urlsplit(self.path).path == '/study/upload':
                    if not service.account.authorized():
                        return self.reply({'error': 'Vui lòng kích hoạt bản quyền.'}, 402)
                    return self.upload()
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size < 65536:
                        raise ValueError('Yêu cầu không hợp lệ.')
                    data = json.loads(self.rfile.read(size))
                    if not isinstance(data, dict):
                        raise ValueError('Nội dung yêu cầu không hợp lệ.')
                    return self.reply(service.action(urllib.parse.urlsplit(self.path).path, data))
                except account_client.AccountError as error:
                    self.reply({'error': str(error)}, 402)
                except ValueError as error:
                    self.reply({'error': str(error)}, 400)
                except Exception:
                    self.reply({'error': 'Chưa thực hiện được. Kiểm tra kết nối và cấu hình; khóa bí mật không được ghi vào nhật ký.'}, 500)
            def upload(self):
                """Stream one study file to disk; the body is never held in memory or interpreted here."""
                target = None
                try:
                    query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    value = lambda key: query.get(key, [''])[0]
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= UPLOAD_LIMIT:
                        raise ValueError('File rỗng hoặc lớn hơn 2 GB.')
                    if value('lesson'):
                        folder = library.find(value('lesson'))['_folder']
                    else:
                        folder = study.new_upload_lesson(value('subject'), value('title'))
                    target = study.upload_target(folder, value('name'))
                    temp = target.with_name(target.name + '.part')
                    with temp.open('wb') as stream:
                        left = size
                        while left:
                            chunk = self.rfile.read(min(left, 1024 * 1024))
                            if not chunk:
                                raise ValueError('Tải lên bị ngắt giữa chừng; thử lại.')
                            stream.write(chunk)
                            left -= len(chunk)
                    temp.replace(target)
                    service.study.kick()
                    return self.reply({'ok': True, 'lesson': study.lesson_id(folder), 'file': target.name})
                except ValueError as error:
                    if target is not None:
                        target.with_name(target.name + '.part').unlink(missing_ok=True)
                    return self.reply({'error': str(error)}, 400)
                except OSError:
                    if target is not None:
                        target.with_name(target.name + '.part').unlink(missing_ok=True)
                    return self.reply({'error': 'Không lưu được file. Kiểm tra dung lượng ổ đĩa.'}, 500)

        return Handler

    def start(self):
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.calendar.start()
        self.study.start()
        if self.account.enabled:
            def watch_license():
                while not self.license_stop.wait(15):
                    if not self.account.authorized() and runner.state().get('running'):
                        runner.shutdown()
            threading.Thread(target=watch_license, daemon=True).start()

    def stop(self):
        self.license_stop.set()
        self.calendar.stop_event.set()
        self.study.stop()
        runner.shutdown()
        self.http.shutdown()
        self.http.server_close()
