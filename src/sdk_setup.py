"""Install the user's own official Zoom Windows Meeting SDK from its ZIP. Nothing in the archive is executed."""
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

RUNTIME = 'sdk.dll'
# The native worker is compiled against these headers; other SDK versions may not match its interfaces.
TESTED_VERSION = '7.2.1.49056'


def extract(archive, target, subfolder=''):
    """Copy `<package>/x64/<subfolder>` from an official Windows SDK ZIP into target, rejecting unsafe paths."""
    target = Path(target).resolve()
    try:
        source = zipfile.ZipFile(archive)
    except (OSError, zipfile.BadZipFile):
        raise ValueError('Không mở được file ZIP. Tải lại gói Meeting SDK Windows từ Zoom Marketplace.') from None
    with source:
        marker = 'x64/bin/' + RUNTIME
        hit = next((name for name in source.namelist() if name == marker or name.endswith('/' + marker)), None)
        if not hit:
            raise ValueError('File ZIP không phải Zoom Meeting SDK Windows x64 (thiếu x64/bin/sdk.dll). Tải đúng gói Windows từ Zoom Marketplace.')
        prefix = hit[:-len('bin/' + RUNTIME)] + (subfolder.strip('/') + '/' if subfolder else '')
        copied = 0
        for member in source.infolist():
            if not member.filename.startswith(prefix):
                continue
            relative = PurePosixPath(member.filename[len(prefix):])
            if not relative.parts:
                continue
            if relative.is_absolute() or '..' in relative.parts or '\\' in member.filename:
                raise ValueError('Đường dẫn trong file ZIP không an toàn; không cài gói này.')
            path = (target / str(relative)).resolve()
            if not path.is_relative_to(target):
                raise ValueError('Đường dẫn trong file ZIP không an toàn; không cài gói này.')
            if member.is_dir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as src, path.open('wb') as dst:
                shutil.copyfileobj(src, dst)
            copied += 1
    return copied


def install(archive, target):
    """Replace the app-managed SDK folder with the archive's x64 runtime; the old copy stays until the new one is complete."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.zoom-sdk-', dir=target.parent))
    previous = target.with_name(target.name + '.old')
    try:
        extract(archive, staging, 'bin')
        if not (staging / RUNTIME).is_file():
            raise ValueError('Gói SDK thiếu sdk.dll.')
        shutil.rmtree(previous, ignore_errors=True)
        if target.exists():
            target.rename(previous)
        try:
            staging.rename(target)
        except OSError:
            if previous.exists() and not target.exists():
                previous.rename(target)
            raise
        shutil.rmtree(previous, ignore_errors=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target
