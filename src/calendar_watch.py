"""Read-only Google iCal feed, local reminders and user-confirmed Zoom handoff."""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.parse import urlsplit
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from paths import DATA
ROOT = DATA
from icalendar import Calendar
import recurring_ical_events
import vault
import platform_actions
from room_link import parse_room_link

TZ = ZoneInfo('Asia/Bangkok')


def feed_url(value):
    value = str(value).strip()
    try:
        u = urlsplit(value)
        valid = (u.scheme == 'https' and u.hostname == 'calendar.google.com'
                 and not u.username and not u.password and u.port in (None, 443)
                 and not u.query and not u.fragment
                 and re.fullmatch(r'/calendar/ical/[^/]+/(?:private-[A-Za-z0-9]+|public)/basic\.ics', u.path))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Dùng địa chỉ iCal của Google Calendar, kết thúc bằng /basic.ics. Không dán link trang lịch thông thường.')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Nguồn lịch chuyển hướng; hãy kiểm tra lại địa chỉ iCal trong Google Calendar.')


def fetch_feed(url):
    request = urllib.request.Request(feed_url(url), headers={'User-Agent': 'CunLocalCalendar/1.0'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=25) as response:
            raw = response.read(10 * 1024 * 1024 + 1)
        if len(raw) > 10 * 1024 * 1024:
            raise ValueError('Lịch quá lớn; hãy dùng một lịch riêng cho các môn học.')
        return raw
    except ValueError:
        raise
    except Exception as error:
        # Exceptions from urllib can contain the secret feed URL.
        # Report only exception types and numeric codes, never str(error) / URL.
        reason = getattr(error, 'reason', None)
        code = getattr(error, 'code', None) or getattr(reason, 'winerror', None) or getattr(reason, 'errno', None)
        detail = type(error).__name__ + ('/' + type(reason).__name__ if isinstance(reason, BaseException) else '')
        if isinstance(code, int):
            detail += ':' + str(code)
        raise ValueError('Không tải được lịch Google ('+detail+'). Kiểm tra mạng và địa chỉ iCal riêng tư; nếu địa chỉ đã đổi, hãy kết nối lại.') from None


def clean_text(value):
    return html.unescape(re.sub(r'<[^>]*>', ' ', str(value or '')))


def events_from_ics(raw, keywords, now):
    calendar = Calendar.from_ical(raw)
    result = []
    terms = [word.strip().casefold() for word in keywords.split(';') if word.strip()]
    if not terms:
        return []
    # Recurrence expansion can coerce DATE entries into midnight datetimes.
    all_day_uids = {str(e.get('UID', '')) for e in calendar.walk('VEVENT')
                    if not isinstance(e.decoded('DTSTART', None), datetime)}
    expanded = recurring_ical_events.of(calendar).between(now - timedelta(days=1), now + timedelta(days=14))
    for event in expanded[:5000]:
        if str(event.get('UID', '')) in all_day_uids:
            continue
        if str(event.get('STATUS', '')).upper() == 'CANCELLED':
            continue
        title = clean_text(event.get('SUMMARY'))[:240]
        if not any(term in title.casefold() for term in terms):
            continue
        start = event.decoded('DTSTART', None)
        if not isinstance(start, datetime):
            continue  # No inferred time for all-day events.
        start = start.replace(tzinfo=TZ) if start.tzinfo is None else start.astimezone(TZ)
        end = event.decoded('DTEND', None)
        if isinstance(end, datetime):
            end = end.replace(tzinfo=TZ) if end.tzinfo is None else end.astimezone(TZ)
        else:
            end = None
        if (end and end <= now) or (not end and start < now - timedelta(minutes=10)):
            continue
        text = '\n'.join(clean_text(event.get(key)) for key in ('URL', 'DESCRIPTION', 'LOCATION'))
        links = {}
        for candidate in re.findall(r'https://[^\s<>"\']+', text):
            candidate = candidate.rstrip('.,);]')
            try:
                parsed = parse_room_link(candidate)
                links[parsed['meeting_id']] = candidate
            except ValueError:
                continue
        if len(links) != 1:
            continue  # Do not guess when several distinct Zoom rooms are present.
        meeting, link = next(iter(links.items()))
        key = hashlib.sha256((str(event.get('UID', '')) + '|' + title + '|' + start.isoformat()).encode()).hexdigest()[:32]
        result.append({'key': key, 'title': title, 'start': start.isoformat(),
                       'end': end.isoformat() if end else None, 'meeting_id': meeting, 'link': link})
    return sorted({e['key']: e for e in result}.values(), key=lambda e: e['start'])


NOTIFIER = None


def windows_notice(title, text):
    if NOTIFIER:
        NOTIFIER(title, text)


class Watcher:
    def __init__(self, path=None, fetcher=fetch_feed, notifier=windows_notice, opener=None):
        self.path = path or ROOT / 'calendar.vault'
        self.fetcher, self.notifier = fetcher, notifier
        self.opener = opener or platform_actions.open_url
        self.lock = threading.RLock()
        self.config = vault.load(self.path)
        self.events = []
        self.messages = []
        self.error = ''
        self.last_sync = None
        self.last_fetch = 0
        self.stop_event = threading.Event()

    def configure(self, data):
        with self.lock:
            url = data.get('feed_url', '').strip() or self.config.get('feed_url', '')
            url = feed_url(url)
            keywords = str(data.get('keywords', '')).strip()[:500]
            if not any(x.strip() for x in keywords.split(';')):
                raise ValueError('Nhập ít nhất một tên môn hoặc từ khóa trong tiêu đề lịch. Chỉ các môn khớp từ khóa mới được theo dõi.')
            enabled = data.get('enabled') is True
            auto_open = data.get('auto_open') is True
            if not data.get('account_confirmed'):
                raise ValueError('Hãy xác nhận đã chọn đúng nguồn lịch học của bạn.')
            self.config.update(feed_url=url, keywords=keywords, enabled=enabled, auto_open=auto_open,
                               account=str(data.get('account') or self.config.get('account') or 'Lịch học của bạn')[:200])
            vault.save(self.path, self.config)
            self.events = []
            self.last_fetch = 0
            self.error = ''

    def pause(self):
        with self.lock:
            self.config['enabled'] = False
            vault.save(self.path, self.config)

    def status(self):
        with self.lock:
            return {'configured': bool(self.config.get('feed_url')), 'enabled': self.config.get('enabled', False),
                    'auto_open': self.config.get('auto_open', False), 'keywords': self.config.get('keywords', ''),
                    'account': self.config.get('account', 'Lịch học của bạn'),
                    'last_sync': self.last_sync, 'error': self.error, 'events': self.events[:100],
                    'messages': self.messages[-10:], 'timezone': 'Asia/Bangkok'}

    def sync(self, now=None):
        now = now or datetime.now(TZ)
        with self.lock:
            url, keywords = self.config.get('feed_url'), self.config.get('keywords', '')
        if not url:
            raise ValueError('Chưa kết nối nguồn lịch Google.')
        try:
            result = events_from_ics(self.fetcher(url), keywords, now)
        except Exception as error:
            with self.lock:
                self.error = str(error) if isinstance(error, ValueError) and str(error).startswith(('Không tải', 'Lịch quá', 'Nguồn lịch')) else 'Không đọc được nội dung iCal; hãy kiểm tra nguồn lịch Google.'
                self.events = []  # Never open stale/cancelled rooms after a failed refresh.
                self.last_fetch = time.monotonic()
            return
        with self.lock:
            if url != self.config.get('feed_url') or keywords != self.config.get('keywords', ''):
                return
            self.events, self.error = result, ''
            self.last_sync, self.last_fetch = now.isoformat(), time.monotonic()

    def event(self, key):
        with self.lock:
            event = next((e for e in self.events if e['key'] == key), None)
            if not event:
                raise ValueError('Buổi học đã thay đổi hoặc không còn trong danh sách. Đồng bộ lại lịch.')
            return dict(event)

    def open_event(self, key):
        event = self.event(key)
        parse_room_link(event['link'])
        self.opener(event['link'])

    def tick(self, now=None):
        now = now or datetime.now(TZ)
        with self.lock:
            if not self.config.get('enabled') or self.error:
                return
            done = self.config.setdefault('done', {})
            for event in self.events:
                start = datetime.fromisoformat(event['start'])
                delta = (start - now).total_seconds()
                if event['end'] and datetime.fromisoformat(event['end']) <= now:
                    continue
                actions = []
                if 0 <= delta <= 1800:
                    actions.append('remind')
                if self.config.get('auto_open') and -600 <= delta <= 120:
                    actions.append('open')
                for action in actions:
                    key = event['key'] + ':' + action
                    if key in done:
                        continue
                    # Record before the side effect, so restart cannot repeatedly launch a room.
                    done[key] = now.isoformat()
                    self.config['done'] = {k:v for k,v in done.items() if v >= (now-timedelta(days=15)).isoformat()}
                    vault.save(self.path, self.config)
                    when = start.strftime('%d/%m %H:%M')
                    if action == 'remind':
                        self.notifier('Sắp đến giờ học Zoom', event['title'] + ' — ' + when)
                        self.messages.append('Đã gửi nhắc: ' + event['title'] + ' — ' + when)
                    else:
                        try:
                            self.open_event(event['key'])
                            self.messages.append('Đã gửi link lớp tới giao diện: ' + event['title'] + '. Vào Zoom trước rồi xác nhận bắt đầu bot.')
                        except Exception:
                            self.messages.append('Không mở được link lớp: ' + event['title'] + '. Dùng nút Mở lớp trong danh sách.')

    def run(self):
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    enabled = self.config.get('enabled') and bool(self.config.get('feed_url'))
                if enabled:
                    if not self.last_sync or time.monotonic() - self.last_fetch >= 300:
                        self.sync()
                    self.tick()
            except Exception:
                with self.lock:
                    self.error = 'Theo dõi lịch tạm dừng do lỗi. Kiểm tra kết nối và bấm Đồng bộ ngay.'
            self.stop_event.wait(15)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
