"""Host actions are explicit events in a container, never arbitrary shell commands."""
import os
import threading
from collections import deque
from pathlib import Path

_events=deque(maxlen=100)
_lock=threading.RLock()
_sequence=0

def emit(kind,**fields):
    global _sequence
    with _lock:
        _sequence+=1
        _events.append({'sequence':_sequence,'kind':kind,**fields})

def events():
    with _lock:return list(_events)

def open_url(url):
    if os.name=='nt':os.startfile(url)
    else:emit('open_url',url=url)

def open_folder(path):
    if os.name=='nt':os.startfile(str(Path(path)))
    else:raise ValueError('Thư mục nằm trong volume Docker. Dùng nút Tải buổi học để tải dữ liệu về máy.')

def notify(title,text):emit('notice',title=title,text=text)
