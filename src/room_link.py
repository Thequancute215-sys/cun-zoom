"""Parse numeric Zoom meeting links locally; never fetch or persist the URL."""
import re
from urllib.parse import urlsplit, parse_qs


def parse_room_link(value):
    if not isinstance(value, str):
        raise ValueError('Hãy dán link phòng Zoom hợp lệ.')
    value = value.strip()
    # Browsers read a backslash as '/', so 'https://evil.example\.zoom.us/j/1' would open evil.example.
    if not value or len(value) > 4096 or re.search(r'[\x00-\x20\x7f\\]', value):
        raise ValueError('Link Zoom trống hoặc chứa ký tự không hợp lệ.')
    try:
        url = urlsplit(value)
        host = (url.hostname or '').lower()
        port = url.port
    except ValueError:
        raise ValueError('Không đọc được link Zoom.') from None
    allowed = any(host == root or host.endswith('.' + root) for root in ('zoom.us', 'zoom.com'))
    if url.scheme != 'https' or not allowed or url.username or url.password or port not in (None, 443):
        raise ValueError('Chỉ nhận link HTTPS của zoom.us hoặc zoom.com; không mở link chuyển hướng.')
    match = re.fullmatch(r'/(?:j|wc/join)/(\d{9,11})/?', url.path)
    if not match:
        match = re.fullmatch(r'/wc/(\d{9,11})/join/?', url.path)
    if not match:
        raise ValueError('Link chưa có ID phòng dạng số được hỗ trợ. Dùng link /j/… hoặc nhập ID; link /my/ và đăng ký chưa được hỗ trợ.')
    query = parse_qs(url.query, keep_blank_values=True)
    return {'meeting_id': match.group(1), 'has_embedded_passcode': bool(query.get('pwd', [''])[0])}
