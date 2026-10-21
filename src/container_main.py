"""Foreground Linux/container service. No tray, hidden browser or host credential import."""
import os
os.environ['CUN_ZOOM_CONTAINER']='1'
os.umask(0o077)
import signal
import threading
from pathlib import Path
from server import Service
import calendar_watch
import platform_actions
from access_control import access_password

def main():
    access_password()
    calendar_watch.NOTIFIER=platform_actions.notify
    service=Service(port=int(os.environ.get('PORT','18766')),host=os.environ.get('BIND_HOST','0.0.0.0'))
    stop=threading.Event()
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *_:stop.set())
    service.quit_app=lambda:stop.set()
    service.start()
    print('Cun Zoom ready. Open the address configured in PUBLIC_ORIGIN. Login user: cunzoom. Password file: /data/access-password.txt (or your mounted access secret).',flush=True)
    stop.wait()
    service.stop()

if __name__=='__main__':main()
