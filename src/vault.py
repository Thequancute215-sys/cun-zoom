"""Windows DPAPI or authenticated portable encryption. Never fall back to plaintext."""
import ctypes
import json
import os
from pathlib import Path
import threading

_lock=threading.RLock()
WINDOWS=os.name=='nt'

def transform(data,decrypt=False):
    if WINDOWS:
        from ctypes import wintypes as W
        class Blob(ctypes.Structure):
            _fields_=[('size',W.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
        buf=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte)));result=Blob()
        lib=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.LocalFree.argtypes=[W.HLOCAL];kernel.LocalFree.restype=W.HLOCAL
        fn=lib.CryptUnprotectData if decrypt else lib.CryptProtectData
        fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,W.DWORD,ctypes.POINTER(Blob)];fn.restype=W.BOOL
        if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(result)):raise ValueError('Không mở được kho khóa bằng tài khoản Windows này.')
        try:return ctypes.string_at(result.data,result.size)
        finally:kernel.LocalFree(ctypes.cast(result.data,W.HLOCAL))
    from cryptography.fernet import Fernet,InvalidToken
    from paths import DATA
    keyfile=Path(os.environ.get('CUN_ZOOM_KEY_FILE',DATA/'vault.key'))
    with _lock:
        if not keyfile.exists():
            if decrypt:raise ValueError('Thiếu khóa giải mã. Khôi phục vault.key từ bản sao lưu của chính bạn.')
            if os.environ.get('CUN_ZOOM_KEY_FILE'):raise ValueError('Mounted encryption secret is missing.')
            keyfile.parent.mkdir(parents=True,exist_ok=True)
            try:
                fd=os.open(keyfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as stream:stream.write(Fernet.generate_key())
            except FileExistsError:pass
        try:
            cipher=Fernet(keyfile.read_bytes().strip())
            return cipher.decrypt(data) if decrypt else cipher.encrypt(data)
        except (InvalidToken,ValueError):raise ValueError('Không giải mã được kho khóa. Kiểm tra đúng tệp vault.key; không tạo khóa mới đè lên khóa cũ.') from None

def load(path):
    path=Path(path)
    if not path.exists():return {}
    with _lock:return json.loads(transform(path.read_bytes(),True))

def save(path,data):
    path=Path(path)
    with _lock:
        temp=path.with_suffix('.tmp')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(transform(json.dumps(data,ensure_ascii=False).encode()))
        os.replace(temp,path)
