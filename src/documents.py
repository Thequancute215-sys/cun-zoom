"""Turn uploaded study files into AI input. Reads files only; never executes or renders their content."""
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree

TEXT = {'.txt', '.md'}
OFFICE = {'.docx', '.pptx'}
IMAGES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif'}
MEDIA = {'.mp3', '.m4a', '.wav', '.aac', '.flac', '.ogg', '.opus', '.wma', '.mp4', '.mkv', '.mov', '.webm', '.avi'}
ACCEPTED = TEXT | OFFICE | MEDIA | set(IMAGES) | {'.pdf'}
# Claude accepts images up to 5 MB and PDFs up to 600 pages within a 32 MB request.
IMAGE_LIMIT = 5 * 1024 * 1024
PDF_LIMIT = 20 * 1024 * 1024
XML_LIMIT = 50 * 1024 * 1024


def kind(path):
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        return 'pdf'
    if suffix in IMAGES:
        return 'image'
    if suffix in MEDIA:
        return 'media'
    if suffix in OFFICE or suffix in TEXT:
        return 'text'
    return None


def safe_name(name):
    name = Path(str(name).replace('\\', '/')).name
    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', stem).strip(' .')[:120] or 'tai_lieu'
    if suffix not in ACCEPTED:
        raise ValueError('Chưa hỗ trợ loại file ' + (suffix or 'không đuôi') + '. Dùng PDF, Word, PowerPoint, ảnh, TXT/MD hoặc âm thanh/video.')
    return stem + suffix


def text_of(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT:
        raw = path.read_bytes()[:4_000_000]
        for encoding in ('utf-8-sig', 'utf-16'):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode('cp1258', errors='replace')
    if suffix == '.docx':
        return _docx(path)
    if suffix == '.pptx':
        return _pptx(path)
    if suffix == '.pdf':
        return _pdf(path)
    return ''


def parts_for(path, provider):
    """AI input parts for one file plus a warning when part of it cannot be used."""
    path = Path(path)
    file_kind = kind(path)
    label = 'Tài liệu "' + path.name + '"'
    if file_kind == 'image':
        if path.stat().st_size > IMAGE_LIMIT:
            return [], path.name + ': ảnh lớn hơn 5 MB, bỏ qua. Giảm kích thước ảnh rồi tải lại.'
        return [{'kind': 'text', 'text': label + ' (ảnh):'}, {'kind': 'image', 'media_type': IMAGES[path.suffix.lower()], 'data': path.read_bytes()}], None
    if file_kind == 'pdf':
        text = ''
        try:
            text = _pdf(path)
        except Exception:
            pass
        if provider == 'claude' and path.stat().st_size <= PDF_LIMIT:
            # Claude reads the PDF pages themselves, including slide images and formulas.
            return [{'kind': 'pdf', 'title': path.name, 'data': path.read_bytes(), 'text': text}], None
        if not text.strip():
            return [], path.name + ': PDF không có chữ đọc được (có thể là bản scan). Dùng Claude hoặc tải ảnh từng trang.'
        return [{'kind': 'text', 'text': label + ':\n' + text}], None
    if file_kind == 'text':
        try:
            text = text_of(path)
        except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
            return [], path.name + ': không đọc được nội dung file.'
        if not text.strip():
            return [], path.name + ': file không có chữ.'
        return [{'kind': 'text', 'text': label + ':\n' + text}], None
    return [], None


def _xml(archive, name):
    info = archive.getinfo(name)
    if info.file_size > XML_LIMIT:
        raise ValueError('Office part too large.')
    return ElementTree.fromstring(archive.read(name))


def _docx(path):
    word = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    with zipfile.ZipFile(path) as archive:
        root = _xml(archive, 'word/document.xml')
    lines = []
    for paragraph in root.iter(word + 'p'):
        text = ''.join(node.text or '' for node in paragraph.iter(word + 't'))
        if text.strip():
            lines.append(text)
    return '\n'.join(lines)


def _pptx(path):
    drawing = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    with zipfile.ZipFile(path) as archive:
        number = lambda name: int(re.search(r'(\d+)\.xml$', name).group(1))
        slides = sorted((n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)), key=number)
        notes = {number(n): n for n in archive.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)}
        lines = []
        for index, name in enumerate(slides, 1):
            paragraphs = [''.join(t.text or '' for t in p.iter(drawing + 't')) for p in _xml(archive, name).iter(drawing + 'p')]
            lines.append('Slide ' + str(index) + ': ' + ' | '.join(p for p in paragraphs if p.strip()))
            if number(name) in notes:
                spoken = [''.join(t.text or '' for t in p.iter(drawing + 't')) for p in _xml(archive, notes[number(name)]).iter(drawing + 'p')]
                spoken = ' '.join(p for p in spoken if p.strip() and not p.strip().isdigit())
                if spoken:
                    lines.append('  Ghi chú: ' + spoken)
    return '\n'.join(lines)


def _pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages[:600], 1):
        text = (page.extract_text() or '').strip()
        if text:
            pages.append('[Trang ' + str(index) + ']\n' + text)
    return '\n\n'.join(pages)
