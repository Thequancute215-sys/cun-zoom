"""Study notes kept in sync with lesson files: per-lesson notes, a per-subject knowledge map, outline and mock exams.

Folder layout under the lesson root (all generated files can be rebuilt from the lesson files):
  00_Tong_hop/Muc_luc.md                      index of every subject
  <Môn>/00_Tong_hop_mon/                     subject knowledge map, outline, mock exams
  <Môn>/<Buổi>/02_Tom_tat/he_thong_buoi.*    notes for one lesson
"""
from collections import deque
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import urllib.parse
import uuid

import ai_backend as ai
import documents
import runner
import transcribe
from paths import preferences

PROMPT_VERSION = '1'
ROOT_INDEX = '00_Tong_hop'
SUBJECT_DIR = '00_Tong_hop_mon'
MATERIALS = '01_Tai_lieu_goc/tai_lieu'
SESSION_NOTES = '02_Tom_tat/he_thong_buoi'
SKIP = {'Bot_rieng', 'Cong_cu', 'Du_lieu_ung_dung', 'App', ROOT_INDEX}
RELEVANCE = {'cot_loi': 'Cốt lõi', 'quan_trong': 'Quan trọng', 'bo_tro': 'Bổ trợ', 'tham_khao': 'Tham khảo'}
DIFFICULTY = {'co_ban': 'Cơ bản', 'trung_binh': 'Trung bình', 'nang_cao': 'Nâng cao'}
TYPES = {'khai_niem': 'Khái niệm', 'cong_thuc_dinh_ly': 'Công thức / định lý', 'quy_trinh': 'Quy trình / phương pháp',
         'vi_du': 'Ví dụ', 'so_sanh': 'So sánh', 'ung_dung': 'Ứng dụng', 'luu_y': 'Lưu ý'}
SLIDE_IMAGES = 20
TRANSCRIBE_STALE = 6 * 3600

SYSTEM = ('Bạn là trợ lý học tập cho sinh viên Việt Nam. Chỉ dùng thông tin có trong tài liệu được cung cấp '
          '(bản chép lời bài giảng, ảnh slide, tài liệu tải lên). Bản chép lời tự động có thể nghe nhầm: sửa lỗi hiển nhiên '
          'theo ngữ cảnh, ghi chỗ không chắc vào mục cần kiểm tra, không bịa thêm kiến thức. Viết tiếng Việt rõ ràng, súc tích.\n'
          'Độ liên quan với môn học: cot_loi = kiến thức trung tâm, gần như chắc chắn được kiểm tra; quan_trong = cần nắm để hiểu '
          'và làm bài; bo_tro = giúp hiểu sâu hơn; tham_khao = mở rộng, ví dụ phụ.\n'
          'Độ khó: co_ban = nhớ và hiểu; trung_binh = vận dụng; nang_cao = phân tích, tổng hợp, bài khó.')


def _string(): return {'type': 'string'}
def _strings(): return {'type': 'array', 'items': {'type': 'string'}}
def _enum(values): return {'type': 'string', 'enum': list(values)}
def _object(properties): return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


ITEM = _object({'ten': _string(), 'noi_dung': _string(), 'loai': _enum(TYPES), 'do_lien_quan': _enum(RELEVANCE),
                'do_kho': _enum(DIFFICULTY), 'nguon': _string()})
SESSION_SCHEMA = _object({
    'tieu_de': _string(), 'tom_tat': _string(),
    'nhom': {'type': 'array', 'items': _object({'ten': _string(), 'mo_ta': _string(), 'muc': {'type': 'array', 'items': ITEM}})},
    'thuat_ngu': {'type': 'array', 'items': _object({'thuat_ngu': _string(), 'giai_thich': _string()})},
    'bai_tap': _strings(), 'cau_hoi_on_tap': _strings(), 'can_kiem_tra': _strings()})
SUBJECT_ITEM = _object({'ten': _string(), 'noi_dung': _string(), 'loai': _enum(TYPES), 'do_lien_quan': _enum(RELEVANCE),
                        'do_kho': _enum(DIFFICULTY), 'buoi': _strings()})
SUBJECT_SCHEMA = _object({
    'tong_quan': _string(),
    'nhom': {'type': 'array', 'items': _object({'ten': _string(), 'mo_ta': _string(), 'do_lien_quan': _enum(RELEVANCE),
                                                 'muc': {'type': 'array', 'items': SUBJECT_ITEM}})},
    'lien_ket': {'type': 'array', 'items': _object({'tu': _string(), 'den': _string(), 'quan_he': _string()})}})
OUTLINE_SCHEMA = _object({
    'muc_tieu': _strings(),
    'chuong': {'type': 'array', 'items': _object({'ten': _string(), 'tom_tat': _string(),
                                                   'y_chinh': {'type': 'array', 'items': _object({'noi_dung': _string(), 'do_kho': _enum(DIFFICULTY), 'trong_tam': {'type': 'boolean'}})},
                                                   'cau_hoi_goi_y': _strings()})},
    'trong_tam_thi': _strings(),
    'ke_hoach_on': {'type': 'array', 'items': _object({'buoc': _string(), 'noi_dung': _string()})}})
EXAM_SCHEMA = _object({
    'tieu_de': _string(), 'thoi_gian_phut': {'type': 'integer'},
    # 'noi_dung_cau_hoi', not 'cau': local models read 'cau' as the question number and leave the question out.
    'trac_nghiem': {'type': 'array', 'items': _object({'noi_dung_cau_hoi': _string(), 'lua_chon': _strings(), 'dap_an': _enum('ABCD'),
                                                        'giai_thich': _string(), 'do_kho': _enum(DIFFICULTY), 'chu_de': _string()})},
    'tu_luan': {'type': 'array', 'items': _object({'noi_dung_cau_hoi': _string(), 'diem': {'type': 'number'}, 'do_kho': _enum(DIFFICULTY),
                                                    'chu_de': _string(), 'goi_y_cham': _strings()})}})
MIX = {'can_bang': 'khoảng 40% cơ bản, 40% trung bình, 20% nâng cao',
       'co_ban': 'khoảng 60% cơ bản, 30% trung bình, 10% nâng cao',
       'nang_cao': 'khoảng 20% cơ bản, 40% trung bình, 40% nâng cao'}


def root():
    return Path(preferences()['recordings_root']).resolve()


def _inside(path, base):
    return not path.is_symlink() and path.resolve().is_relative_to(base.resolve())


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(text, encoding='utf-8')
    temp.replace(path)


def _write_json(path, value):
    _write(path, json.dumps(value, ensure_ascii=False, indent=2))


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def subject_dirs():
    base = root()
    if not base.is_dir():
        return []
    return sorted((d for d in base.iterdir() if d.is_dir() and d.name not in SKIP and _inside(d, base) and sessions(d)), key=lambda d: d.name.lower())


def subject_dir(name):
    base = root()
    folder = base / str(name)
    if not name or '/' in str(name) or '\\' in str(name) or folder.name in SKIP or not folder.is_dir() or not _inside(folder, base):
        raise ValueError('Không tìm thấy môn học.')
    return folder


def sessions(subject):
    found = []
    for folder in subject.iterdir():
        if folder.is_dir() and _inside(folder, subject) and (folder / 'buoi_hoc.json').is_file():
            meta = _read_json(folder / 'buoi_hoc.json') or {}
            found.append({'folder': folder, 'meta': meta, 'date': str(meta.get('requested') or meta.get('created') or folder.name[:10])})
    found.sort(key=lambda item: item['date'])
    for number, item in enumerate(found, 1):
        item['label'] = 'Buổi ' + str(number) + ' · ' + item['date'][:10] + ' · ' + str(item['meta'].get('title') or item['folder'].name)[:80]
    return found


def lesson_id(folder):
    # Same identifier the lesson library uses, so the UI can link both views.
    return hashlib.sha256(str(folder).encode()).hexdigest()[:24]


def _materials(folder):
    target = folder / MATERIALS
    if not target.is_dir():
        return []
    return sorted(p for p in target.iterdir() if p.is_file() and _inside(p, folder) and documents.kind(p))


def _slides(folder):
    return sorted((folder / '01_Tai_lieu_goc').glob('slide_*.jpg'))


def _transcript(folder):
    path = folder / '02_Tom_tat/ban_chep_loi.txt'
    return path if path.is_file() and path.stat().st_size > 0 else None


def _uploaded_media(folder):
    return any(p.parent.name == 'tai_lieu' for p in transcribe.media_files(folder))


def transcription_state(folder):
    """'none', 'needed', 'running', 'failed' or 'done' for the lesson's audio and video."""
    media = transcribe.media_files(folder)
    if not media:
        return 'none'
    status = _read_json(folder / '02_Tom_tat/trang_thai.json') or {}
    transcript = _transcript(folder)
    newest = max(p.stat().st_mtime for p in media)
    if transcript and transcript.stat().st_mtime >= newest:
        return 'done'
    if status.get('state') == 'completed' and (folder / '02_Tom_tat/trang_thai.json').stat().st_mtime >= newest:
        # Silent media leaves an empty transcript; running it again would hear nothing again.
        return 'done'
    if status.get('state') == 'processing':
        try:
            started = datetime.fromisoformat(status['time']).timestamp()
        except (KeyError, ValueError):
            started = 0
        if time.time() - started < TRANSCRIBE_STALE:
            return 'running'
    if status.get('state') == 'failed' and (folder / '02_Tom_tat/trang_thai.json').stat().st_mtime >= newest:
        return 'failed'
    return 'needed'


def fingerprint(folder):
    digest = hashlib.sha256(PROMPT_VERSION.encode())
    inputs = [p for p in [_transcript(folder)] if p] + _materials(folder) + _slides(folder)[:500]
    for path in inputs:
        stat = path.stat()
        digest.update(f'{path.relative_to(folder).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}\n'.encode())
    return digest.hexdigest()[:32], bool(inputs)


# SHA-256 of a file's bytes by (path, size, mtime): read once per version, again after restart or a manual resync.
_DIGESTS = {}


def _file_digest(path):
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in _DIGESTS:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                digest.update(block)
        _DIGESTS[key] = digest.hexdigest()
    return _DIGESTS[key]


def forget_digests(folder):
    prefix = str(folder)
    for key in [k for k in _DIGESTS if k[0].startswith(prefix)]:
        _DIGESTS.pop(key, None)


def content_fingerprint(folder):
    """Like fingerprint, but by content for what the owner writes (transcript, documents): same bytes, same notes.
    Slides the bot captures and media (read through the transcript) keep size and mtime."""
    digest, slides = hashlib.sha256(PROMPT_VERSION.encode()), _slides(folder)[:500]
    captured = set(slides)
    for path in [p for p in [_transcript(folder)] if p] + _materials(folder) + slides:
        stat = path.stat()
        by_bytes = path not in captured and documents.kind(path) != 'media'
        digest.update(f'{path.relative_to(folder).as_posix()}|{_file_digest(path) if by_bytes else str(stat.st_size) + "|" + str(stat.st_mtime_ns)}\n'.encode())
    return digest.hexdigest()[:32]


def notes_current(folder, notes, current=None):
    meta = notes.get('_meta', {})
    # Notes written before content digests compare as they always did, so an upgrade reruns nothing.
    if 'content' in meta:
        return meta['content'] == content_fingerprint(folder)
    return meta.get('fingerprint') == (current or fingerprint(folder)[0])


def session_notes(folder):
    return _read_json(folder / (SESSION_NOTES + '.json'))


def _waiting(folder):
    state = transcription_state(folder)
    # Without the speech model the audio cannot be read yet; notes use the other files and update once it is.
    return state == 'running' or (state == 'needed' and transcribe.model_ready())


def session_status(folder):
    if _waiting(folder):
        return 'waiting_transcript'
    current, has_inputs = fingerprint(folder)
    if not has_inputs:
        return 'empty'
    notes = session_notes(folder)
    return 'ready' if notes and notes_current(folder, notes, current) else 'stale'


def _sorted_items(items):
    rank = {key: index for index, key in enumerate(RELEVANCE)}
    hard = {key: index for index, key in enumerate(DIFFICULTY)}
    return sorted(items, key=lambda item: (rank.get(item.get('do_lien_quan'), 9), hard.get(item.get('do_kho'), 9)))


def _organize(data):
    """Order groups by their most relevant item, then items by relevance and difficulty."""
    rank = {key: index for index, key in enumerate(RELEVANCE)}
    for group in data.get('nhom', []):
        group['muc'] = _sorted_items(group.get('muc', []))
    data['nhom'] = sorted(data.get('nhom', []), key=lambda g: min([rank.get(g.get('do_lien_quan'), 9)] + [rank.get(i.get('do_lien_quan'), 9) for i in g['muc']]))
    return data


def _chunks(text, size):
    """Pieces of at most size characters, in order, that together keep every character of every line."""
    current, length = [], 0
    for line in text.splitlines():
        while len(line) > size:
            # Split an over-long line at a space in its second half when there is one, else exactly at size.
            cut = line.rfind(' ', size // 2, size) + 1 or size
            if current:
                yield '\n'.join(current)
                current, length = [], 0
            yield line[:cut]
            line = line[cut:]
        if length + len(line) > size and current:
            yield '\n'.join(current)
            current, length = [], 0
        current.append(line)
        length += len(line) + 1
    if current:
        yield '\n'.join(current)


def analyze_session(subject, folder, config=None):
    config = config or ai.settings()
    current, has_inputs = fingerprint(folder)
    if not has_inputs:
        raise ai.AIError('Buổi học chưa có bản chép lời, slide hay tài liệu để hệ thống hoá.')
    content = content_fingerprint(folder)
    meta = _read_json(folder / 'buoi_hoc.json') or {}
    header = 'Môn: ' + subject.name + '\nBuổi: ' + str(meta.get('title') or folder.name) + '\nNgày: ' + str(meta.get('requested', ''))[:10]
    warnings, files, extra, documents_read = [], [], [], False
    transcription = transcription_state(folder)
    if transcription == 'failed':
        warnings.append('Chưa chép lời được âm thanh của buổi này; ghi chú chỉ dựa trên slide và tài liệu.')
    elif transcription == 'needed':
        warnings.append('Chưa có bộ chép lời nên chưa dùng âm thanh của buổi này. Tải bộ chép lời trong Cài đặt → Lưu trữ; ghi chú sẽ tự cập nhật.')
    for path in _materials(folder):
        parts, warning = documents.parts_for(path, config['provider'])
        if warning:
            warnings.append(warning)
        if parts:
            files.append(path.name)
            extra.extend(parts)
            documents_read = documents_read or documents.kind(path) != 'image'
    slides = _slides(folder)
    if slides and config['provider'] == 'claude':
        step = max(1, len(slides) // SLIDE_IMAGES)
        chosen = slides[::step][:SLIDE_IMAGES]
        extra.append({'kind': 'text', 'text': 'Ảnh slide chụp từ màn hình chia sẻ (' + str(len(chosen)) + '/' + str(len(slides)) + ' ảnh):'})
        extra.extend({'kind': 'image', 'media_type': 'image/jpeg', 'data': p.read_bytes()} for p in chosen)
    elif slides:
        warnings.append(str(len(slides)) + ' ảnh slide chưa được đọc vì mô hình Ollama dùng chữ; dùng Claude để đọc slide.')
    transcript = _transcript(folder)
    text = transcript.read_text(encoding='utf-8', errors='replace') if transcript else ''
    # Never let the AI write notes from the lesson title alone: it would invent the whole lesson.
    if not text.strip() and not extra:
        raise ai.AIError('Không có nội dung đọc được để hệ thống hoá buổi này. ' + ' '.join(warnings))
    images_only = not text.strip() and not documents_read
    task = ('Hệ thống hoá buổi học: tóm tắt, chia kiến thức thành các nhóm theo chủ đề, mỗi mục ghi loại, độ liên quan, '
            'độ khó và nguồn (chép lời, slide hoặc tên tài liệu). Liệt kê thuật ngữ, bài tập/hạn nộp được nhắc, câu hỏi ôn tập '
            'và chỗ cần kiểm tra lại.')
    limit = ai.input_chars(config)
    if len(text) + sum(len(p.get('text', '')) for p in extra if p['kind'] == 'text') <= limit:
        parts = [{'kind': 'text', 'text': header + '\n\n' + task}] + extra
        if text:
            parts.append({'kind': 'text', 'text': 'Bản chép lời bài giảng:\n' + text})
        result = ai.generate(SYSTEM, parts, SESSION_SCHEMA, 'medium', config, images_required=images_only)
    else:
        # Too long for one request (mostly local models): note each part, then merge the notes.
        pieces, attachments = list(_chunks(text, limit // 2)), []
        for item in extra:
            label, _, body = item.get('text', '').partition('\n')
            if item['kind'] != 'text' or not body:
                # Images, PDFs and their one-line labels.
                attachments.append(item)
            else:
                # A long document is split like the transcript; each piece keeps the document's name for citing.
                pieces += [label + '\n' + piece for piece in _chunks(body, limit // 2)]
        partial = []
        for index, piece in enumerate(pieces, 1):
            parts = [{'kind': 'text', 'text': header + '\nPhần ' + str(index) + '/' + str(len(pieces)) + '\n\n' + task + '\n\n' + piece}]
            # Slides and PDFs ride with the first part so no input is dropped.
            partial.append(ai.generate(SYSTEM, parts + (attachments if index == 1 else []), SESSION_SCHEMA, 'medium', config))
        def merge(notes):
            return ai.generate(SYSTEM, [{'kind': 'text', 'text': header + '\n\nGộp các ghi chú từng phần của cùng buổi học thành một bản hệ thống hoá, bỏ trùng lặp:\n'
                                         + json.dumps(notes, ensure_ascii=False)}], SESSION_SCHEMA, 'medium', config)
        # Merge in rounds that each fit one request until a single request can hold every part.
        while len(json.dumps(partial, ensure_ascii=False)) > limit:
            rounds, batch = [], []
            for note in partial:
                if batch and len(json.dumps(batch + [note], ensure_ascii=False)) > limit:
                    rounds.append(batch)
                    batch = []
                batch.append(note)
            rounds.append(batch)
            if len(rounds) == len(partial):
                break  # every note alone is over the budget; another round cannot shrink them
            partial = [merge(batch) if len(batch) > 1 else batch[0] for batch in rounds]
        result = merge(partial)
    result = _organize(result)
    result['_meta'] = {'fingerprint': current, 'content': content, 'version': PROMPT_VERSION, 'created': datetime.now().isoformat(timespec='seconds'),
                       'ai': _ai_label(config), 'files': files, 'warnings': warnings, 'transcript': bool(text)}
    _write_json(folder / (SESSION_NOTES + '.json'), result)
    _write(folder / (SESSION_NOTES + '.md'), session_markdown(subject.name, result))
    return result


def subject_fingerprint(subject):
    digest = hashlib.sha256(PROMPT_VERSION.encode())
    for item in sessions(subject):
        notes = session_notes(item['folder'])
        if notes:
            meta = notes.get('_meta', {})
            # Notes redone for new content under the same size and mtime still refresh the subject map.
            digest.update((item['folder'].name + '|' + (meta.get('content') or meta.get('fingerprint', '')) + '\n').encode())
    return digest.hexdigest()[:32]


def subject_paths(subject):
    folder = subject / SUBJECT_DIR
    return {'map': folder / 'he_thong_kien_thuc.json', 'outline': folder / 'de_cuong.json', 'exams': folder / 'de_thi_thu', 'folder': folder}


def knowledge_map(subject):
    return _read_json(subject_paths(subject)['map'])


def aggregate_subject(subject, config=None):
    config = config or ai.settings()
    noted = [(item, session_notes(item['folder'])) for item in sessions(subject)]
    noted = [(item, notes) for item, notes in noted if notes]
    if not noted:
        raise ai.AIError('Chưa có buổi nào được hệ thống hoá trong môn này.')
    compact = [{'buoi': item['label'], 'tom_tat': notes.get('tom_tat', ''),
                'nhom': [{'ten': g['ten'], 'muc': [{k: m[k] for k in ('ten', 'noi_dung', 'loai', 'do_lien_quan', 'do_kho')} for m in g.get('muc', [])]} for g in notes.get('nhom', [])]}
               for item, notes in noted]
    task = ('Tổng hợp kiến thức cả môn "' + subject.name + '" từ ghi chú các buổi dưới đây. Gộp mục trùng nhau, nhóm theo chủ đề lớn của '
            'môn, đánh giá lại độ liên quan và độ khó trên phạm vi cả môn, ghi các buổi có nội dung đó (dùng đúng nhãn buổi). '
            'Nêu các liên kết quan trọng giữa các khái niệm.')
    limit = ai.input_chars(config)
    batches, current = [], []
    for entry in compact:
        if current and len(json.dumps(current + [entry], ensure_ascii=False)) > limit:
            batches.append(current)
            current = []
        current.append(entry)
    batches.append(current)
    if len(batches) == 1:
        result = ai.generate(SYSTEM, [{'kind': 'text', 'text': task + '\n\n' + json.dumps(compact, ensure_ascii=False)}], SUBJECT_SCHEMA, 'high', config)
    else:
        partial = [ai.generate(SYSTEM, [{'kind': 'text', 'text': task + '\n\n' + json.dumps(batch, ensure_ascii=False)}], SUBJECT_SCHEMA, 'high', config) for batch in batches]
        result = ai.generate(SYSTEM, [{'kind': 'text', 'text': 'Gộp các bản tổng hợp từng phần của môn "' + subject.name + '" thành một, bỏ trùng lặp:\n' + json.dumps(partial, ensure_ascii=False)}],
                             SUBJECT_SCHEMA, 'high', config)
    result = _organize(result)
    result['_meta'] = {'fingerprint': subject_fingerprint(subject), 'version': PROMPT_VERSION, 'created': datetime.now().isoformat(timespec='seconds'),
                       'ai': _ai_label(config), 'sessions': [item['label'] for item, _ in noted]}
    paths = subject_paths(subject)
    _write_json(paths['map'], result)
    _write(paths['folder'] / 'he_thong_kien_thuc.md', subject_markdown(subject, result))
    write_root_index()
    return result


def _knowledge_text(subject):
    data = knowledge_map(subject)
    if not data:
        raise ai.AIError('Chưa có hệ thống kiến thức của môn. Hệ thống hoá các buổi học trước.')
    return data, json.dumps({k: v for k, v in data.items() if k != '_meta'}, ensure_ascii=False)


def make_outline(subject, config=None):
    config = config or ai.settings()
    data, knowledge = _knowledge_text(subject)
    task = ('Lập đề cương ôn tập môn "' + subject.name + '" chỉ từ hệ thống kiến thức sau. Chia chương theo trình tự hợp lý để học, '
            'đánh dấu ý trọng tâm (ưu tiên mục cốt lõi), gợi ý câu hỏi tự kiểm tra, nêu trọng tâm thi và kế hoạch ôn từng bước.')
    result = ai.generate(SYSTEM, [{'kind': 'text', 'text': knowledge}, {'kind': 'text', 'text': task}], OUTLINE_SCHEMA, 'high', config)
    result['_meta'] = {'base': data.get('_meta', {}).get('fingerprint'), 'created': datetime.now().isoformat(timespec='seconds'), 'ai': _ai_label(config)}
    paths = subject_paths(subject)
    _write_json(paths['outline'], result)
    _write(paths['folder'] / 'de_cuong.md', outline_markdown(subject.name, result))
    write_root_index()
    return result


def _exam_questions(result):
    """Questions with real text; a multiple-choice stem that only names a topic becomes 'which statement is true about it'."""
    for question in result.get('trac_nghiem', []) + result.get('tu_luan', []):
        question['cau'] = str(question.pop('noi_dung_cau_hoi', '')).strip()
    asked = lambda q: len(q['cau']) > 3 and not q['cau'].rstrip('.').isdigit()
    choice = []
    for question in result.get('trac_nghiem', []):
        if not asked(question) or len(question.get('lua_chon', [])) != 4:
            continue
        stem = question['cau']
        if not stem.endswith(('?', ':', '…', '...')) and len(stem.split()) <= 6:
            question['cau'] = 'Phát biểu nào sau đây đúng về ' + (stem[0].lower() if stem[1:2].islower() else stem[0]) + stem[1:] + '?'
        choice.append(question)
    return choice, [q for q in result.get('tu_luan', []) if asked(q)]


def make_exam(subject, multiple_choice=20, essays=3, mix='can_bang', config=None):
    config = config or ai.settings()
    multiple_choice = max(0, min(60, int(multiple_choice)))
    essays = max(0, min(10, int(essays)))
    if not multiple_choice and not essays:
        raise ai.AIError('Chọn ít nhất một câu trắc nghiệm hoặc tự luận.')
    data, knowledge = _knowledge_text(subject)

    def ask(choices, essays_wanted, existing):
        task = ('Soạn đề thi thử môn "' + subject.name + '" chỉ từ hệ thống kiến thức đã cho: ' + str(choices) + ' câu trắc nghiệm '
                '(đúng 4 lựa chọn, ghi nội dung lựa chọn không kèm chữ A-D, một đáp án đúng, giải thích ngắn) và ' + str(essays_wanted) + ' câu tự luận '
                '(thang điểm, gợi ý chấm theo ý). Mỗi câu ghi đề bài đầy đủ trong noi_dung_cau_hoi, là một câu hỏi hoàn chỉnh, không chỉ tên '
                'chủ đề. Độ khó ' + MIX.get(mix, MIX['can_bang']) + '. Ưu tiên mục cốt lõi và quan trọng, trải đều các '
                'nhóm, không hỏi ngoài tài liệu. Ghi chủ đề (tên nhóm) và độ khó cho từng câu, ước lượng thời gian làm bài.')
        if existing:
            task += ' Không lặp lại các câu đã có: ' + json.dumps(existing, ensure_ascii=False)
        # Knowledge first, task last: the knowledge block stays cached between the outline and repeated exams.
        return ai.generate(SYSTEM, [{'kind': 'text', 'text': knowledge}, {'kind': 'text', 'text': task}], EXAM_SCHEMA, 'high', config)

    result = ask(multiple_choice, essays, [])
    choice, written = _exam_questions(result)
    missing = (multiple_choice - len(choice), essays - len(written))
    if max(missing) > 0:
        # Local models often stop short of the requested count; ask once more for the rest.
        more_choice, more_written = _exam_questions(ask(max(missing[0], 0), max(missing[1], 0), [q['cau'] for q in choice + written]))
        seen = {q['cau'] for q in choice + written}
        choice += [q for q in more_choice if q['cau'] not in seen][:max(missing[0], 0)]
        written += [q for q in more_written if q['cau'] not in seen][:max(missing[1], 0)]
    result['trac_nghiem'], result['tu_luan'] = choice, written
    if not result['trac_nghiem'] and not result['tu_luan']:
        raise ai.AIError('AI không soạn được câu hỏi hợp lệ. Thử lại hoặc dùng mô hình lớn hơn.')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    result['_meta'] = {'id': stamp, 'base': data.get('_meta', {}).get('fingerprint'), 'created': datetime.now().isoformat(timespec='seconds'),
                       'ai': _ai_label(config), 'mix': mix}
    folder = subject_paths(subject)['exams']
    _write_json(folder / (stamp + '.json'), result)
    _write(folder / (stamp + '.md'), exam_markdown(subject.name, result))
    write_root_index()
    return result


def exams(subject):
    folder = subject_paths(subject)['exams']
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob('*.json'), reverse=True):
        data = _read_json(path)
        if data and re.fullmatch(r'\d{8}-\d{6}', path.stem):
            found.append({'id': path.stem, 'title': data.get('tieu_de', ''), 'created': data.get('_meta', {}).get('created', ''),
                          'multiple_choice': len(data.get('trac_nghiem', [])), 'essays': len(data.get('tu_luan', []))})
    return found


def exam(subject, identifier):
    if not re.fullmatch(r'\d{8}-\d{6}', str(identifier)):
        raise ValueError('Không tìm thấy đề thi.')
    data = _read_json(subject_paths(subject)['exams'] / (identifier + '.json'))
    if not data:
        raise ValueError('Không tìm thấy đề thi.')
    return data


def _ai_label(config):
    return 'Claude · ' + config['claude_model'] if config['provider'] == 'claude' else 'Ollama · ' + config['ollama_model']


def _badge(item):
    return '[' + RELEVANCE.get(item.get('do_lien_quan'), '?') + ' · ' + DIFFICULTY.get(item.get('do_kho'), '?') + ' · ' + TYPES.get(item.get('loai'), '?') + ']'


def _link(relative):
    # Folder names hold spaces and Vietnamese; encode the target so Markdown viewers keep it a working link.
    return '[' + relative + '](../' + urllib.parse.quote(relative) + ')'


def _inert(markdown):
    """Model text must not become an image or HTML that a Markdown viewer loads from the web without a click."""
    return markdown.replace('<', '\\<').replace('![', '!\\[')


def session_markdown(subject, data):
    lines = ['# ' + (data.get('tieu_de') or 'Hệ thống hoá buổi học'), '', 'Môn: ' + subject + ' · Tạo bởi ' + data['_meta']['ai'] + ' · ' + data['_meta']['created'], '',
             '## Tóm tắt', '', data.get('tom_tat', ''), '']
    for group in data.get('nhom', []):
        lines += ['## ' + group.get('ten', ''), '', group.get('mo_ta', ''), '']
        lines += ['- **' + i['ten'] + '** ' + _badge(i) + ': ' + i['noi_dung'] + (' _(Nguồn: ' + i['nguon'] + ')_' if i.get('nguon') else '') for i in group.get('muc', [])]
        lines.append('')
    for title, values in (('Thuật ngữ', ['**' + t['thuat_ngu'] + '**: ' + t['giai_thich'] for t in data.get('thuat_ngu', [])]),
                          ('Bài tập và hạn nộp', data.get('bai_tap', [])), ('Câu hỏi ôn tập', data.get('cau_hoi_on_tap', [])),
                          ('Cần kiểm tra lại', data.get('can_kiem_tra', []) + data['_meta'].get('warnings', []))):
        if values:
            lines += ['## ' + title, ''] + ['- ' + v for v in values] + ['']
    lines.append('_Bản do AI hệ thống hoá từ bài giảng; đối chiếu với slide và giáo trình trước khi học thuộc._')
    return _inert('\n'.join(lines) + '\n')


def subject_markdown(subject, data):
    lines = ['# Hệ thống kiến thức · ' + subject.name, '', 'Tạo bởi ' + data['_meta']['ai'] + ' · ' + data['_meta']['created'], '', '## Tổng quan', '', data.get('tong_quan', ''), '']
    for group in data.get('nhom', []):
        lines += ['## ' + group.get('ten', '') + ' — ' + RELEVANCE.get(group.get('do_lien_quan'), ''), '', group.get('mo_ta', ''), '']
        lines += ['- **' + i['ten'] + '** ' + _badge(i) + ': ' + i['noi_dung'] + (' _(' + '; '.join(i.get('buoi', [])) + ')_' if i.get('buoi') else '') for i in group.get('muc', [])]
        lines.append('')
    if data.get('lien_ket'):
        lines += ['## Liên kết giữa các khái niệm', ''] + ['- ' + l['tu'] + ' → ' + l['den'] + ': ' + l['quan_he'] for l in data['lien_ket']] + ['']
    lines += ['## Ghi chú từng buổi', '']
    for item in sessions(subject):
        notes = item['folder'] / (SESSION_NOTES + '.md')
        lines.append('- ' + item['label'] + (': ' + _link(notes.relative_to(subject).as_posix()) if notes.is_file() else ': chưa hệ thống hoá'))
    return _inert('\n'.join(lines) + '\n')


def outline_markdown(subject, data):
    lines = ['# Đề cương ôn tập · ' + subject, '', 'Tạo bởi ' + data['_meta']['ai'] + ' · ' + data['_meta']['created'], '', '## Mục tiêu', ''] + ['- ' + v for v in data.get('muc_tieu', [])] + ['']
    for number, chapter in enumerate(data.get('chuong', []), 1):
        lines += ['## ' + str(number) + '. ' + chapter.get('ten', ''), '', chapter.get('tom_tat', ''), '']
        lines += ['- ' + ('★ ' if p.get('trong_tam') else '') + p['noi_dung'] + ' [' + DIFFICULTY.get(p.get('do_kho'), '') + ']' for p in chapter.get('y_chinh', [])]
        if chapter.get('cau_hoi_goi_y'):
            lines += ['', '**Tự kiểm tra:**'] + ['- ' + q for q in chapter['cau_hoi_goi_y']]
        lines.append('')
    lines += ['## Trọng tâm thi', ''] + ['- ' + v for v in data.get('trong_tam_thi', [])] + ['', '## Kế hoạch ôn', '']
    lines += [str(n) + '. **' + s['buoc'] + '**: ' + s['noi_dung'] for n, s in enumerate(data.get('ke_hoach_on', []), 1)]
    return _inert('\n'.join(lines) + '\n')


def exam_markdown(subject, data):
    lines = ['# ' + (data.get('tieu_de') or 'Đề thi thử · ' + subject), '', 'Thời gian gợi ý: ' + str(data.get('thoi_gian_phut', '')) + ' phút · Tạo bởi ' + data['_meta']['ai'], '']
    if data.get('trac_nghiem'):
        lines += ['## Phần I. Trắc nghiệm', '']
        for number, q in enumerate(data['trac_nghiem'], 1):
            lines += ['**Câu ' + str(number) + '.** ' + q['cau'] + ' _(' + DIFFICULTY.get(q.get('do_kho'), '') + ')_'] + [letter + '. ' + option for letter, option in zip('ABCD', q['lua_chon'])] + ['']
    if data.get('tu_luan'):
        lines += ['## Phần II. Tự luận', '']
        lines += ['**Câu ' + str(n) + '** (' + str(q.get('diem', '')) + ' điểm). ' + q['cau'] for n, q in enumerate(data['tu_luan'], 1)] + ['']
    lines += ['---', '', '## Đáp án và gợi ý chấm', '']
    lines += ['- Câu ' + str(n) + ': **' + q['dap_an'] + '** — ' + q.get('giai_thich', '') for n, q in enumerate(data.get('trac_nghiem', []), 1)]
    for n, q in enumerate(data.get('tu_luan', []), 1):
        lines += ['', '**Tự luận câu ' + str(n) + ':**'] + ['- ' + v for v in q.get('goi_y_cham', [])]
    return _inert('\n'.join(lines) + '\n')


def write_root_index():
    base = root()
    lines = ['# Mục lục bài giảng', '', 'File này do Cún Zoom tạo lại tự động khi bài giảng thay đổi.', '']
    for subject in subject_dirs():
        items = sessions(subject)
        done = sum(1 for item in items if session_notes(item['folder']))
        lines += ['## ' + subject.name, '', '- Buổi học: ' + str(len(items)) + ' (đã hệ thống hoá ' + str(done) + ')']
        for label, name in (('Hệ thống kiến thức', 'he_thong_kien_thuc.md'), ('Đề cương', 'de_cuong.md')):
            path = subject / SUBJECT_DIR / name
            if path.is_file():
                lines.append('- ' + label + ': ' + _link(path.relative_to(base).as_posix()))
        count = len(exams(subject))
        if count:
            lines.append('- Đề thi thử: ' + str(count) + ' đề trong ' + subject.name + '/' + SUBJECT_DIR + '/de_thi_thu')
        lines.append('')
    target, text = base / ROOT_INDEX / 'Muc_luc.md', '\n'.join(lines) + '\n'
    if base.is_dir() and subject_dirs() and (not target.is_file() or target.read_text(encoding='utf-8') != text):
        _write(target, text)


def new_upload_lesson(subject_name, title):
    """A lesson folder for uploaded material, shaped like a recorded lesson so every view lists it."""
    subject = runner.name(subject_name)
    title = runner.name(title or 'Tai_lieu')
    base = root()
    folder = base / subject / (datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_' + title + '_' + uuid.uuid4().hex[:4])
    if subject in SKIP or not folder.resolve().is_relative_to(base):
        raise ValueError('Tên môn không hợp lệ.')
    for sub in ('01_Tai_lieu_goc/tai_lieu', '02_Tom_tat', '03_Bai_tap_va_on_tap'):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    _write_json(folder / 'buoi_hoc.json', {'subject': subject, 'title': title, 'requested': datetime.now().isoformat(timespec='seconds'),
                                          'source': 'upload', 'state': 'materials'})
    return folder


def upload_target(folder, name):
    target_dir = folder / MATERIALS
    target_dir.mkdir(parents=True, exist_ok=True)
    clean = documents.safe_name(name)
    target = target_dir / clean
    stem, suffix, number = target.stem, target.suffix, 2
    while target.exists():
        target = target_dir / (stem + '_' + str(number) + suffix)
        number += 1
    return target


class Engine:
    """One background worker keeps notes in sync; AI work runs one job at a time to bound cost and CPU."""

    def __init__(self):
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stop_event = threading.Event()
        self.jobs = deque()
        self.current = None
        self.errors = {}
        self.failed = {}
        self.reasons = {}
        self.message = ''
        self.thread = None
        self.authorized = lambda: True

    def start(self):
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()

    def kick(self):
        self.wake.set()

    def request(self, kind, subject, **params):
        if not ai.enabled():
            raise ai.AIError('Chưa bật AI. Vào Cài đặt → AI để chọn Claude hoặc Ollama.')
        folder = subject_dir(subject)
        job = (kind, folder, tuple(sorted(params.items())))
        with self.lock:
            # A manual sync retries the subject's failed work; making an exam does not.
            if kind != 'exam':
                self.failed = {k: v for k, v in self.failed.items() if folder not in (k[1], k[1].parent)}
                # ...and reads the subject's files again, so an edit that kept size and mtime is noticed.
                forget_digests(folder)
            if job not in self.jobs and self.current != job:
                self.jobs.appendleft(job)
        self.kick()

    def status(self):
        with self.lock:
            return {'running': self.current is not None, 'current': _job_label(self.current), 'queued': len(self.jobs),
                    'errors': dict(self.errors), 'message': self.message}

    def loop(self):
        while not self.stop_event.is_set():
            if not self.authorized():
                self.stop_event.wait(15)
                continue
            worked = False
            try:
                self.scan()
                worked = self.run_jobs()
                write_root_index()
            except Exception as error:
                with self.lock:
                    self.message = 'Đồng bộ tạm dừng: ' + type(error).__name__
            if not worked:
                self.wake.wait(30)
                self.wake.clear()

    def scan(self):
        """Queue the work that lesson files call for: transcription, lesson notes, subject map, outline."""
        config = ai.settings()
        auto = ai.enabled(config) and config['auto']
        subjects = subject_dirs()
        lessons = [item['folder'] for subject in subjects for item in sessions(subject)]
        states = {folder: transcription_state(folder) for folder in lessons}
        # Transcription is CPU heavy: one lesson at a time, never during a recording. Uploaded media is always
        # transcribed; older recordings without a transcript only when the user turned on automatic sync.
        bot = runner.state()
        if 'running' not in states.values() and transcribe.model_ready() and not bot.get('running'):
            waiting = next((folder for folder in lessons if states[folder] == 'needed' and (auto or _uploaded_media(folder))), None)
            if waiting:
                runner.start_transcription(waiting)
        recording = Path(bot['path']).resolve() if bot.get('running') and bot.get('path') else None
        for subject in subjects:
            if recording and recording.parent == subject:
                # Slides keep arriving until the recording ends; notes made now would be redone (and paid for) again.
                continue
            subject_changed = False
            for item in sessions(subject):
                folder = item['folder']
                if auto and session_status(folder) == 'stale':
                    # A lesson that failed for its current files (e.g. only a broken document) must not hold back the
                    # subject map and outline for every other lesson.
                    subject_changed = self.queue(('session', folder, ()), fingerprint(folder)[0]) or subject_changed
            if not auto or subject_changed:
                continue
            notes_ready = any(session_notes(i['folder']) for i in sessions(subject))
            data = knowledge_map(subject)
            if notes_ready and (not data or data.get('_meta', {}).get('fingerprint') != subject_fingerprint(subject)):
                self.queue(('subject', subject, ()), subject_fingerprint(subject))
            elif data:
                outline = _read_json(subject_paths(subject)['outline'])
                if not outline or outline.get('_meta', {}).get('base') != data.get('_meta', {}).get('fingerprint'):
                    self.queue(('outline', subject, ()), data.get('_meta', {}).get('fingerprint'))

    def queue(self, job, version):
        """Queue job unless it already failed for these exact inputs; True while it is waiting or running."""
        with self.lock:
            # A job that already failed for these exact inputs waits for new files or a manual retry.
            if self.failed.get(job) == version:
                return False
            if job not in self.jobs and self.current != job:
                self.jobs.append(job)
            return True

    def _stale_lessons(self, subject):
        with self.lock:
            return [item['folder'] for item in sessions(subject) if session_status(item['folder']) == 'stale'
                    and self.failed.get(('session', item['folder'], ())) != fingerprint(item['folder'])[0]]

    def _lesson_problems(self, subject):
        """Errors of lessons that still fail for their current files, so a later subject update does not hide them."""
        with self.lock:
            return [item['label'] + ': ' + self.reasons[job] for item in sessions(subject)
                    for job in [('session', item['folder'], ())]
                    if job in self.reasons and self.failed.get(job) == fingerprint(item['folder'])[0]]

    def run_jobs(self):
        worked = False
        while not self.stop_event.is_set() and self.authorized():
            with self.lock:
                if not self.jobs:
                    return worked
                self.current = self.jobs.popleft()
            worked = True
            kind, folder, params = self.current
            subject = folder.parent if kind == 'session' else folder
            try:
                config = ai.settings()
                if kind == 'session':
                    analyze_session(subject, folder, config)
                elif kind == 'subject':
                    for lesson in self._stale_lessons(subject):
                        try:
                            analyze_session(subject, lesson, config)
                        except Exception as error:
                            # This lesson waits for new files; the others still make the subject map.
                            with self.lock:
                                self.failed[('session', lesson, ())] = fingerprint(lesson)[0]
                                self.reasons[('session', lesson, ())] = _reason(error)
                    aggregate_subject(subject, config)
                elif kind == 'outline':
                    if not knowledge_map(subject) or self._stale_lessons(subject):
                        aggregate_subject(subject, config)
                    make_outline(subject, config)
                elif kind == 'exam':
                    make_exam(subject, config=config, **dict(params))
                problems = self._lesson_problems(subject)
                with self.lock:
                    if problems:
                        self.errors[subject.name] = ' · '.join(problems)
                    else:
                        self.errors.pop(subject.name, None)
                    self.message = 'Đã cập nhật ' + _job_label(self.current)
            except Exception as error:
                # Any failure, not only expected ones, waits for new files or a manual retry instead of repeating every scan.
                with self.lock:
                    version = fingerprint(folder)[0] if kind == 'session' else subject_fingerprint(subject)
                    self.failed[self.current] = version
                    self.reasons[self.current] = _reason(error)
                    # A lesson's error names the lesson, together with any other lesson still failing.
                    self.errors[subject.name] = ' · '.join(self._lesson_problems(subject)) if kind == 'session' else _reason(error)
            finally:
                with self.lock:
                    self.current = None


def _reason(error):
    return str(error) if isinstance(error, (ai.AIError, ValueError, OSError)) and str(error) else 'Lỗi xử lý (' + type(error).__name__ + ')'


def _job_label(job):
    if not job:
        return ''
    kind, folder, _ = job
    names = {'session': 'ghi chú buổi', 'subject': 'hệ thống kiến thức', 'outline': 'đề cương', 'exam': 'đề thi thử'}
    target = folder.parent.name + ' · ' + folder.name if kind == 'session' else folder.name
    return names[kind] + ' · ' + target


def overview(engine):
    status = engine.status()
    found = []
    for subject in subject_dirs():
        items = sessions(subject)
        states = [session_status(item['folder']) for item in items]
        data = knowledge_map(subject)
        outline = _read_json(subject_paths(subject)['outline'])
        found.append({'name': subject.name, 'sessions': len(items), 'ready': states.count('ready'), 'stale': states.count('stale'),
                      'waiting': states.count('waiting_transcript'), 'has_map': bool(data),
                      'map_current': bool(data) and data.get('_meta', {}).get('fingerprint') == subject_fingerprint(subject),
                      'has_outline': bool(outline), 'outline_current': bool(outline and data) and outline['_meta'].get('base') == data['_meta'].get('fingerprint'),
                      'exams': len(exams(subject)), 'error': status['errors'].get(subject.name, '')})
    return {'subjects': found, 'engine': status, 'ai': ai.public_settings(), 'labels': {'relevance': RELEVANCE, 'difficulty': DIFFICULTY, 'types': TYPES}}


def subject_detail(name):
    subject = subject_dir(name)
    lessons = []
    for item in sessions(subject):
        notes = session_notes(item['folder'])
        lessons.append({'id': lesson_id(item['folder']), 'label': item['label'], 'status': session_status(item['folder']),
                        'transcription': transcription_state(item['folder']), 'materials': [p.name for p in _materials(item['folder'])],
                        'notes': notes})
    return {'name': subject.name, 'map': knowledge_map(subject), 'outline': _read_json(subject_paths(subject)['outline']),
            'exams': exams(subject), 'lessons': lessons, 'folder': str(subject / SUBJECT_DIR)}
