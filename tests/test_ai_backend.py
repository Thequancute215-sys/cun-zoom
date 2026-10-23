import bootstrap
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import unittest
from unittest.mock import patch

import ai_backend as ai

SCHEMA = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False}


def sse(text, stop='end_turn', model='claude-opus-5-5'):
    events = [('message_start', {'type': 'message_start', 'message': {'id': 'msg_test', 'type': 'message', 'role': 'assistant', 'model': model, 'content': [],
                                                                     'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 10, 'output_tokens': 1}}})]
    if text is not None:
        events += [('content_block_start', {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}),
                   ('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}}),
                   ('content_block_stop', {'type': 'content_block_stop', 'index': 0})]
    events += [('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': stop, 'stop_sequence': None}, 'usage': {'output_tokens': 5}}),
               ('message_stop', {'type': 'message_stop'})]
    return ''.join('event: ' + name + '\ndata: ' + json.dumps(data) + '\n\n' for name, data in events).encode()


class FakeServer:
    """Local stand-in for the Claude and Ollama HTTP APIs; records what the app sends."""

    def __init__(self, respond):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.requests.append({'path': self.path, 'headers': dict(self.headers), 'body': body})
                status, content_type, raw = respond(self.path, body)
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:' + str(self.http.server_port)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def close(self):
        self.http.shutdown()
        self.http.server_close()


def claude(model='claude-opus-5-5'):
    return {'provider': 'claude', 'claude_key': 'sk-ant-synthetic', 'claude_model': model, 'ollama_url': 'http://127.0.0.1:1', 'ollama_model': '', 'auto': True}


class SettingsTests(unittest.TestCase):
    def test_key_is_kept_encrypted_and_never_returned(self):
        ai.save({'provider': 'claude', 'claude_key': 'sk-ant-synthetic-secret', 'claude_model': 'claude-sonnet-5-5'})
        self.assertNotIn(b'sk-ant-synthetic-secret', ai.CONFIG.read_bytes())
        public = ai.public_settings()
        self.assertNotIn('sk-ant-synthetic-secret', json.dumps(public))
        self.assertTrue(public['claude_key_saved'] and public['enabled'])
        # An empty key field keeps the saved key.
        ai.save({'provider': 'claude', 'claude_key': '', 'claude_model': 'claude-opus-5-5'})
        self.assertEqual(ai.settings()['claude_key'], 'sk-ant-synthetic-secret')
        ai.save({'provider': 'off'})
        self.assertFalse(ai.enabled())

    def test_rejects_invalid_settings(self):
        for data in ({'provider': 'gpt'}, {'provider': 'claude', 'claude_key': 'not-a-key', 'claude_model': 'claude-opus-5-5'},
                     {'provider': 'ollama', 'ollama_model': 'm', 'ollama_url': 'file:///etc'}, {'provider': 'off', 'claude_model': 'gpt-4'}):
            with self.assertRaises(ai.AIError):
                ai.save(data)


class ClaudeTests(unittest.TestCase):
    def run_claude(self, respond, model='claude-opus-5-5', parts=None):
        server = FakeServer(respond)
        self.addCleanup(server.close)
        with patch.dict(os.environ, {'ANTHROPIC_BASE_URL': server.url, 'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}):
            result = ai.generate('system', parts or [{'kind': 'text', 'text': 'xin chào'}], SCHEMA, 'high', claude(model))
        return result, server.requests

    def test_structured_request_with_documents_fallback_and_cache(self):
        parts = [{'kind': 'text', 'text': 'Bài giảng'}, {'kind': 'image', 'media_type': 'image/png', 'data': b'png-bytes'},
                 {'kind': 'pdf', 'title': 'slide.pdf', 'data': b'%PDF-1.4', 'text': 'ignored for Claude'}]
        result, requests = self.run_claude(lambda path, body: (200, 'text/event-stream', sse('{"ok": true}')), parts=parts)
        self.assertEqual(result, {'ok': True})
        sent = requests[0]
        body = sent['body']
        self.assertEqual(body['model'], 'claude-opus-5-5')
        self.assertEqual(body['output_config'], {'effort': 'high', 'format': {'type': 'json_schema', 'schema': SCHEMA}})
        self.assertEqual(body['fallbacks'], 'default')
        self.assertIn('server-side-fallback-2026-07-01', sent['headers'].get('anthropic-beta', ''))
        self.assertEqual(body['cache_control'], {'type': 'ephemeral'})
        self.assertTrue(body['stream'])
        kinds = [block['type'] for block in body['messages'][0]['content']]
        self.assertEqual(kinds, ['text', 'image', 'document'])
        self.assertEqual(body['messages'][0]['content'][2]['source']['media_type'], 'application/pdf')
        self.assertNotIn('thinking', body)

    def test_haiku_has_no_fallback(self):
        _, requests = self.run_claude(lambda path, body: (200, 'text/event-stream', sse('{"ok": true}', model='claude-haiku-5-5')), model='claude-haiku-5-5')
        self.assertNotIn('fallbacks', requests[0]['body'])
        self.assertNotIn('server-side-fallback', requests[0]['headers'].get('anthropic-beta', ''))

    def test_refusal_and_truncation_and_auth_errors_are_explained(self):
        cases = [(lambda path, body: (200, 'text/event-stream', sse(None, stop='refusal')), 'không xử lý'),
                 (lambda path, body: (200, 'text/event-stream', sse('{"ok": tr', stop='max_tokens')), 'độ dài'),
                 (lambda path, body: (401, 'application/json', json.dumps({'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}}).encode()), 'Khóa API')]
        for respond, message in cases:
            with self.subTest(message=message), self.assertRaises(ai.AIError) as result:
                self.run_claude(respond)
            self.assertIn(message, str(result.exception))

    def test_oversized_payload_is_refused_before_sending(self):
        with patch.object(ai, 'CLAUDE_PAYLOAD_LIMIT', 10), self.assertRaises(ai.AIError):
            ai.generate('s', [{'kind': 'image', 'media_type': 'image/png', 'data': b'x' * 100}], SCHEMA, 'low', claude())


class OllamaTests(unittest.TestCase):
    def test_json_schema_request_and_image_retry_for_text_models(self):
        def respond(path, body):
            if body['messages'][1].get('images'):
                return 500, 'application/json', b'{"error":"model does not support images"}'
            return 200, 'application/json', json.dumps({'message': {'content': '{"ok": true}'}}).encode()
        server = FakeServer(respond)
        self.addCleanup(server.close)
        config = {'provider': 'ollama', 'claude_key': '', 'claude_model': 'claude-opus-5-5', 'ollama_url': server.url, 'ollama_model': 'qwen2.5:14b', 'auto': True}
        parts = [{'kind': 'text', 'text': 'Bài giảng'}, {'kind': 'image', 'media_type': 'image/png', 'data': b'png'}, {'kind': 'pdf', 'data': b'%PDF', 'text': 'PDF text'}]
        self.assertEqual(ai.generate('system', parts, SCHEMA, 'medium', config), {'ok': True})
        self.assertEqual(len(server.requests), 2)
        first, second = server.requests
        self.assertEqual(first['path'], '/api/chat')
        self.assertEqual(first['body']['format'], SCHEMA)
        self.assertIn('PDF text', second['body']['messages'][1]['content'])
        self.assertNotIn('images', second['body']['messages'][1])

    def test_image_only_input_fails_on_text_models_instead_of_guessing(self):
        server = FakeServer(lambda path, body: (500, 'application/json', b'{"error":"model does not support images"}'))
        self.addCleanup(server.close)
        config = {'provider': 'ollama', 'claude_key': '', 'claude_model': 'claude-opus-5-5', 'ollama_url': server.url, 'ollama_model': 'qwen2.5:3b', 'auto': True}
        with self.assertRaises(ai.AIError) as result:
            ai.generate('s', [{'kind': 'text', 'text': 'Ghi chú'}, {'kind': 'image', 'media_type': 'image/png', 'data': b'png'}], SCHEMA, 'low', config, images_required=True)
        self.assertIn('không đọc được ảnh', str(result.exception))
        self.assertEqual(len(server.requests), 1)

    def test_oversized_or_malformed_replies_are_errors(self):
        replies = iter([json.dumps({'message': {'content': 'x' * 300}}).encode(), json.dumps({'message': {'content': '[1, 2]'}}).encode(),
                        json.dumps({'message': {'content': '[' * 100000}}).encode()])
        server = FakeServer(lambda path, body: (200, 'application/json', next(replies)))
        self.addCleanup(server.close)
        config = {'provider': 'ollama', 'claude_key': '', 'claude_model': 'claude-opus-5-5', 'ollama_url': server.url, 'ollama_model': 'm', 'auto': True}
        with patch.object(ai, 'OLLAMA_REPLY_LIMIT', 200), self.assertRaises(ai.AIError) as result:
            ai.generate('s', [{'kind': 'text', 'text': 'x'}], SCHEMA, 'low', config)
        self.assertIn('quá lớn', str(result.exception))
        for _ in range(2):
            with self.assertRaises(ai.AIError):
                ai.generate('s', [{'kind': 'text', 'text': 'x'}], SCHEMA, 'low', config)

    def test_unreachable_server_is_explained(self):
        config = {'provider': 'ollama', 'claude_key': '', 'claude_model': 'claude-opus-5-5', 'ollama_url': 'http://127.0.0.1:9', 'ollama_model': 'm', 'auto': True}
        with self.assertRaises(ai.AIError) as result:
            ai.generate('s', [{'kind': 'text', 'text': 'x'}], SCHEMA, 'low', config)
        self.assertIn('Ollama', str(result.exception))


if __name__ == '__main__':
    unittest.main()
