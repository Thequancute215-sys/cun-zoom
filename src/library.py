"""Read local lesson outputs. Browser requests never supply arbitrary file paths."""
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from paths import preferences


def items():
    root = Path(preferences()['recordings_root']).resolve()
    found = []
    if not root.is_dir():
        return found
    for subject in root.iterdir():
        if not subject.is_dir() or subject.is_symlink() or not subject.resolve().is_relative_to(root) or subject.name in {'Bot_rieng', 'Cong_cu', 'Du_lieu_ung_dung', 'App'}:
            continue
        for folder in subject.iterdir():
            if not folder.is_dir() or folder.is_symlink() or not folder.resolve().is_relative_to(root):
                continue
            metadata = folder / 'buoi_hoc.json'
            if not metadata.is_file() or not metadata.resolve().is_relative_to(folder.resolve()):
                continue
            try:
                meta = json.loads(metadata.read_text(encoding='utf-8-sig'))
                audio = folder / '01_Tai_lieu_goc/am_thanh.wav'
                if not audio.exists():
                    audio = folder / '01_Tai_lieu_goc/am_thanh.webm'
                summary = folder / '02_Tom_tat/tom_tat_nhap.md'
                transcript = folder / '02_Tom_tat/ban_chep_loi.txt'
                found.append({'id': hashlib.sha256(str(folder).encode()).hexdigest()[:24],
                              'subject': str(meta.get('subject', subject.name))[:200],
                              'title': str(meta.get('title', folder.name))[:200],
                              'date': meta.get('requested', meta.get('created', folder.name[:10])),
                              'audio_bytes': audio.stat().st_size if audio.is_file() else 0,
                              'slides': len(list((folder/'01_Tai_lieu_goc').glob('slide_*.jpg'))),
                              'has_summary': summary.is_file(), 'has_transcript': transcript.is_file(),
                              'state': meta.get('state', 'unknown'), '_folder': folder})
            except (OSError, ValueError, TypeError):
                continue
    return sorted(found, key=lambda item: str(item['date']), reverse=True)[:300]


def listing():
    return [{k:v for k,v in item.items() if k != '_folder'} for item in items()]


def find(identifier):
    item = next((item for item in items() if item['id'] == identifier), None)
    if not item:
        raise ValueError('Không tìm thấy buổi học trong thư viện.')
    return item


def read(identifier, kind):
    folder = find(identifier)['_folder']
    name = {'summary': 'tom_tat_nhap.md', 'transcript': 'ban_chep_loi.txt'}.get(kind)
    if not name:
        raise ValueError('Loại tài liệu không hợp lệ.')
    target = folder / '02_Tom_tat' / name
    if not target.is_file() or not target.resolve().is_relative_to(folder.resolve()):
        raise ValueError('Buổi học chưa có tài liệu này.')
    return target.read_text(encoding='utf-8', errors='replace')[:160000]


def open_folder(identifier):
    os.startfile(str(find(identifier)['_folder']))


def archive(identifier):
    folder = find(identifier)['_folder'].resolve()
    packed = tempfile.TemporaryFile()
    try:
        with zipfile.ZipFile(packed, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
            for target in folder.rglob('*'):
                if target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(folder):
                    bundle.write(target, str(target.relative_to(folder)))
        packed.seek(0)
        return packed
    except Exception:
        packed.close()
        raise

