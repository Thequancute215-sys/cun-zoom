"""Optional AI for study notes: the user's own Claude API key or a local Ollama model. Off until the user enables it."""
import base64
import json
import threading
import urllib.error
import urllib.parse
import urllib.request

import vault
from paths import DATA, CONTAINER

CONFIG = DATA / 'ai.vault'
CLAUDE_MODELS = {
    'claude-opus-5-5': 'Claude Opus 5.5 — chất lượng cao nhất (khuyên dùng)',
    'claude-sonnet-5-5': 'Claude Sonnet 5.5 — cân bằng chi phí',
    'claude-haiku-5-5': 'Claude Haiku 5.5 — rẻ và nhanh nhất',
}
DEFAULT_CLAUDE = 'claude-opus-5-5'
# Server-side refusal fallback exists for Opus/Sonnet 5.5; Haiku 5.5 has none.
FALLBACK_MODELS = {'claude-opus-5-5', 'claude-sonnet-5-5'}
DEFAULT_OLLAMA_URL = 'http://host.docker.internal:11434' if CONTAINER else 'http://127.0.0.1:11434'
# A Claude request may carry at most 32 MB; leave room for the JSON envelope.
CLAUDE_PAYLOAD_LIMIT = 24 * 1024 * 1024
# Characters of plain text one request may carry before the caller must split it.
INPUT_CHARS = {'claude': 600_000, 'ollama': 40_000}
_lock = threading.RLock()


class AIError(ValueError):
    pass


def settings():
    with _lock:
        try:
            config = vault.load(CONFIG)
        except (OSError, ValueError):
            config = {}
    model = config.get('claude_model') if config.get('claude_model') in CLAUDE_MODELS else DEFAULT_CLAUDE
    return {'provider': config.get('provider') if config.get('provider') in ('claude', 'ollama') else 'off',
            'claude_key': config.get('claude_key', ''), 'claude_model': model,
            'ollama_url': config.get('ollama_url') or DEFAULT_OLLAMA_URL, 'ollama_model': config.get('ollama_model', ''),
            'auto': config.get('auto', True) is not False}


def public_settings():
    config = settings()
    return {'provider': config['provider'], 'claude_model': config['claude_model'], 'claude_key_saved': bool(config['claude_key']),
            'ollama_url': config['ollama_url'], 'ollama_model': config['ollama_model'], 'auto': config['auto'],
            'enabled': enabled(config), 'models': CLAUDE_MODELS}


def enabled(config=None):
    config = config or settings()
    if config['provider'] == 'claude':
        return bool(config['claude_key'])
    return config['provider'] == 'ollama' and bool(config['ollama_model'])


def save(data):
    provider = data.get('provider', 'off')
    if provider not in ('off', 'claude', 'ollama'):
        raise AIError('Chọn Tắt, Claude hoặc Ollama.')
    current = settings()
    model = data.get('claude_model', current['claude_model'])
    if model not in CLAUDE_MODELS:
        raise AIError('Mô hình Claude không hợp lệ.')
    key = str(data.get('claude_key', '')).strip() or current['claude_key']
    if provider == 'claude' and not key.startswith('sk-ant-'):
        raise AIError('Dán khóa API Claude (bắt đầu bằng sk-ant-) từ console.anthropic.com.')
    url = str(data.get('ollama_url', '') or current['ollama_url']).strip().rstrip('/')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
        raise AIError('Địa chỉ Ollama phải có dạng http://máy:11434.')
    ollama_model = str(data.get('ollama_model', current['ollama_model'])).strip()[:120]
    if provider == 'ollama' and not ollama_model:
        raise AIError('Nhập tên mô hình Ollama, ví dụ qwen2.5:14b.')
    config = {'provider': provider, 'claude_key': key, 'claude_model': model, 'ollama_url': url,
              'ollama_model': ollama_model, 'auto': data.get('auto', current['auto']) is not False}
    with _lock:
        vault.save(CONFIG, config)
    return public_settings()


def input_chars(config=None):
    return INPUT_CHARS.get((config or settings())['provider'], INPUT_CHARS['ollama'])


def generate(system, parts, schema, effort='medium', config=None):
    """Return JSON matching schema. parts: {'kind': 'text'|'image'|'pdf', ...}; PDFs also carry extracted 'text'."""
    config = config or settings()
    if not enabled(config):
        raise AIError('Chưa bật AI. Vào Cài đặt → AI để chọn Claude hoặc Ollama.')
    if config['provider'] == 'claude':
        return _claude(config, system, parts, schema, effort)
    return _ollama(config, system, parts, schema)


def test(config=None):
    schema = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False}
    result = generate('Trả lời đúng định dạng JSON được yêu cầu.', [{'kind': 'text', 'text': 'Trả về {"ok": true}.'}], schema, 'low', config)
    if result.get('ok') is not True:
        raise AIError('AI trả lời nhưng không đúng định dạng. Thử mô hình khác.')
    return True


def _claude(config, system, parts, schema, effort):
    import anthropic
    content, size = [], 0
    for part in parts:
        if part['kind'] == 'text':
            content.append({'type': 'text', 'text': part['text']})
            continue
        size += len(part['data']) * 4 // 3
        if size > CLAUDE_PAYLOAD_LIMIT:
            raise AIError('Tài liệu gửi cho Claude vượt 24 MB trong một lần; chia nhỏ file hoặc bớt ảnh.')
        data = base64.standard_b64encode(part['data']).decode('ascii')
        if part['kind'] == 'image':
            content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': part['media_type'], 'data': data}})
        else:
            content.append({'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': data},
                            'title': part.get('title', 'Tài liệu')[:200]})
    model = config['claude_model']
    request = {'model': model, 'max_tokens': 64000, 'system': system, 'messages': [{'role': 'user', 'content': content}],
               'output_config': {'effort': effort, 'format': {'type': 'json_schema', 'schema': schema}},
               'cache_control': {'type': 'ephemeral'}}
    client = anthropic.Anthropic(api_key=config['claude_key'], max_retries=3, timeout=900.0)
    try:
        if model in FALLBACK_MODELS:
            with client.beta.messages.stream(**request, betas=['server-side-fallback-2026-07-01'], fallbacks='default') as stream:
                message = stream.get_final_message()
        else:
            with client.messages.stream(**request) as stream:
                message = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise AIError('Khóa API Claude không hợp lệ hoặc đã bị thu hồi. Nhập lại trong Cài đặt → AI.') from None
    except anthropic.PermissionDeniedError:
        raise AIError('Khóa API Claude không có quyền dùng mô hình này.') from None
    except anthropic.NotFoundError:
        raise AIError('Tài khoản Claude chưa dùng được mô hình ' + model + '. Chọn mô hình khác.') from None
    except anthropic.RateLimitError:
        raise AIError('Claude đang giới hạn tốc độ hoặc đã hết hạn mức. Thử lại sau ít phút.') from None
    except anthropic.BadRequestError as error:
        raise AIError('Claude từ chối yêu cầu: ' + str(getattr(error, 'message', ''))[:300]) from None
    except anthropic.APIStatusError as error:
        raise AIError('Máy chủ Claude lỗi (HTTP ' + str(error.status_code) + '). Thử lại sau.') from None
    except anthropic.APIConnectionError:
        raise AIError('Không kết nối được Claude. Kiểm tra mạng rồi thử lại.') from None
    if message.stop_reason == 'refusal':
        category = getattr(getattr(message, 'stop_details', None), 'category', None)
        raise AIError('Claude không xử lý nội dung này' + (' (' + category + ')' if category else '') + '. Thử bớt tài liệu hoặc đổi mô hình.')
    if message.stop_reason == 'max_tokens':
        raise AIError('Kết quả vượt độ dài tối đa. Tạo lại với ít nội dung hơn.')
    text = next((block.text for block in message.content if block.type == 'text'), '')
    try:
        return json.loads(text)
    except ValueError:
        raise AIError('Claude trả về dữ liệu không đọc được. Thử lại.') from None


def _ollama(config, system, parts, schema):
    texts, images = [], []
    for part in parts:
        if part['kind'] == 'image':
            images.append(base64.standard_b64encode(part['data']).decode('ascii'))
        elif part.get('text'):
            texts.append(part['text'])
    message = {'role': 'user', 'content': '\n\n'.join(texts)}
    try:
        return _ollama_call(config, system, {**message, 'images': images} if images else message, schema)
    except AIError:
        if not images:
            raise
        # Text-only models reject images; keep the text so the notes still get made.
        return _ollama_call(config, system, message, schema)


def _ollama_call(config, system, message, schema):
    body = {'model': config['ollama_model'], 'stream': False, 'format': schema,
            'messages': [{'role': 'system', 'content': system}, message], 'options': {'num_ctx': 32768}}
    request = urllib.request.Request(config['ollama_url'] + '/api/chat', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            reply = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(400).decode('utf-8', 'replace')
        if error.code == 404:
            raise AIError('Ollama chưa có mô hình ' + config['ollama_model'] + '. Chạy: ollama pull ' + config['ollama_model']) from None
        raise AIError('Ollama báo lỗi (HTTP ' + str(error.code) + '): ' + detail[:200]) from None
    except (urllib.error.URLError, OSError):
        raise AIError('Không kết nối được Ollama tại ' + config['ollama_url'] + '. Mở Ollama rồi thử lại.') from None
    try:
        return json.loads(reply['message']['content'])
    except (KeyError, TypeError, ValueError):
        raise AIError('Ollama trả về dữ liệu không đọc được. Thử mô hình lớn hơn.') from None
