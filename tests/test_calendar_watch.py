import bootstrap
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from calendar_watch import Watcher, TZ, events_from_ics, feed_url, fetch_feed
from unittest.mock import patch
from urllib.error import HTTPError
import vault

NOW = datetime(2026, 10, 21, 9, 30, tzinfo=TZ)
SOURCE = 'https://calendar.google.com/calendar/ical/synthetic%40example.com/private-synthetic/basic.ics'


def fixture(extra='', start='20261021T030000Z', title='PTTC1 Tin hoc', uid='lesson'):
    return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\n'
            'BEGIN:VEVENT\r\nUID:'+uid+'\r\nDTSTART:'+start+'\r\nDURATION:PT90M\r\nSUMMARY:'+title+
            '\r\nDESCRIPTION:Join https://us02web.zoom.us/j/12345678901?pwd=synthetic-secret\r\n'+extra+
            'END:VEVENT\r\nEND:VCALENDAR\r\n').encode()


class CalendarTests(unittest.TestCase):
    def test_timezone_recurrence_cancellation_and_filters(self):
        events = events_from_ics(fixture('RRULE:FREQ=DAILY;COUNT=3\r\nEXDATE:20261022T030000Z\r\n'), 'PTTC1', NOW)
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]['start'].startswith('2026-10-21T10:00:00+07:00'))
        self.assertEqual(events_from_ics(fixture('STATUS:CANCELLED\r\n'), 'PTTC1', NOW), [])
        self.assertEqual(events_from_ics(fixture(title='Work meeting'), 'PTTC1', NOW), [])
        self.assertEqual(events_from_ics(fixture(), '', NOW), [])

    def test_all_day_and_ambiguous_rooms_are_not_scheduled(self):
        all_day=fixture().replace(b'DTSTART:20261021T030000Z',b'DTSTART;VALUE=DATE:20261021')
        self.assertEqual(events_from_ics(all_day,'PTTC1',NOW),[])
        multiple=fixture().replace(b'pwd=synthetic-secret', b'pwd=synthetic-secret https://zoom.us/j/98765432101')
        self.assertEqual(events_from_ics(multiple,'PTTC1',NOW),[])

    def test_feed_destination_and_error_do_not_echo_secrets(self):
        self.assertEqual(feed_url(SOURCE),SOURCE)
        for source in ('https://evil.example/private-secret', 'https://calendar.google.com.evil.example/calendar/ical/a/private-secret/basic.ics',
                       'http://calendar.google.com/calendar/ical/a/private-secret/basic.ics'):
            with self.assertRaises(ValueError) as e:feed_url(source)
            self.assertNotIn('private-secret',str(e.exception))

    def test_remind_open_once_even_after_restart_and_pause(self):
        with tempfile.TemporaryDirectory() as d:
            notices, opened = [], []
            path=Path(d)/'calendar.dpapi'
            watcher=Watcher(path,fetcher=lambda _:fixture(),notifier=lambda *a:notices.append(a),opener=opened.append)
            watcher.configure({'feed_url':SOURCE,'keywords':'PTTC1','account_confirmed':True,'enabled':True,'auto_open':True})
            watcher.sync(NOW);watcher.tick(NOW);watcher.tick(NOW)
            self.assertEqual(len(notices),1);self.assertEqual(len(opened),0)
            watcher.tick(NOW+timedelta(minutes=28));self.assertEqual(len(opened),1)
            second=Watcher(path,fetcher=lambda _:fixture(),notifier=lambda *a:notices.append(a),opener=opened.append)
            second.sync(NOW);second.tick(NOW+timedelta(minutes=29));self.assertEqual(len(opened),1)
            self.assertNotIn(b'private-synthetic',path.read_bytes())
            self.assertNotIn('private-synthetic',str(second.status()))
            second.pause();second.events=events_from_ics(fixture(uid='new'),'PTTC1',NOW)
            second.tick(NOW);self.assertEqual(len(notices),1)

    def test_fetch_error_reports_type_and_code_without_private_url(self):
        error=HTTPError(SOURCE,403,'private-synthetic',{},None)
        with patch('calendar_watch.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=error
            with self.assertRaises(ValueError) as result:fetch_feed(SOURCE)
        self.assertIn('HTTPError:403',str(result.exception))
        self.assertNotIn('private-synthetic',str(result.exception))

    def test_failed_refresh_clears_stale_room_and_never_opens(self):
        with tempfile.TemporaryDirectory() as d:
            opened=[]
            watcher=Watcher(Path(d)/'calendar.dpapi',fetcher=lambda _:fixture(),opener=opened.append)
            watcher.configure({'feed_url':SOURCE,'keywords':'PTTC1','account_confirmed':True,'enabled':True,'auto_open':True})
            watcher.sync(NOW)
            def fail(_):raise RuntimeError('secret-source-must-not-be-logged')
            watcher.fetcher=fail;watcher.sync(NOW);watcher.tick(NOW+timedelta(minutes=28))
            self.assertEqual(opened,[]);self.assertEqual(watcher.events,[])
            self.assertNotIn('secret-source',watcher.error)


if __name__=='__main__':unittest.main()
