import bootstrap
import unittest
from room_link import parse_room_link


class RoomLinkTests(unittest.TestCase):
    def test_supported_meeting_links(self):
        for url in ('https://us02web.zoom.us/j/12345678901?pwd=example',
                    'https://ptit.zoom.us/j/12345678901',
                    'https://zoom.com/wc/join/12345678901',
                    'https://zoom.us/wc/12345678901/join'):
            self.assertEqual(parse_room_link(url)['meeting_id'], '12345678901')

    def test_does_not_return_link_passcode(self):
        result = parse_room_link('https://zoom.us/j/123456789?pwd=private-example')
        self.assertEqual(result, {'meeting_id': '123456789', 'has_embedded_passcode': True})
        self.assertNotIn('private-example', str(result))

    def test_rejects_spoofed_and_unsupported_links(self):
        for url in ('https://zoom.us.evil.example/j/123456789',
                    'https://evilzoom.us/j/123456789',
                    'https://zoom.us@evil.example/j/123456789',
                    'http://zoom.us/j/123456789',
                    'https://zoom.us:8443/j/123456789',
                    'https://zoom.us/my/teacher',
                    'https://zoom.us/j/123',
                    'https://zoom.us/j/123456789\n',
                    'https://zoom.us/j/123456789\x00', None):
            # Outer whitespace is intentionally accepted when copying a link.
            if isinstance(url, str) and url.endswith('\n'):
                continue
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_room_link(url)


if __name__ == '__main__':
    unittest.main()
