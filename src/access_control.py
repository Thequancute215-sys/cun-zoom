"""Container access is authenticated before serving HTML, secrets or lesson contents."""
import base64
import hmac
import os
from pathlib import Path
import secrets
import threading
from paths import DATA,CONTAINER

_lock=threading.RLock()

def access_password():
    path=Path(os.environ.get('CUN_ZOOM_ACCESS_KEY_FILE',DATA/'access-password.txt'))
    with _lock:
        if not path.exists():
            if os.environ.get('CUN_ZOOM_ACCESS_KEY_FILE'):raise ValueError('Mounted access secret is missing.')
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='ascii') as stream:stream.write(secrets.token_urlsafe(32))
        value=path.read_text(encoding='utf-8').strip()
        if len(value)<24:raise ValueError('Access password must contain at least 24 characters.')
        return value

def allowed(header):
    if not CONTAINER:return True
    if not header.startswith('Basic '):return False
    try:
        raw=base64.b64decode(header[6:],validate=True).decode('utf-8')
        username,password=raw.split(':',1)
    except (ValueError,UnicodeError):return False
    return hmac.compare_digest(username.encode(),b'cunzoom') and hmac.compare_digest(password.encode(),access_password().encode())
