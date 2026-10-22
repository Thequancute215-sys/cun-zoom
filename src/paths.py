"""Portable resources and explicit per-installation storage; Windows upgrades keep the 1.x locations."""
import json
import os
from pathlib import Path
import shutil
import sys

VERSION = '2.2.1'
REPOSITORY = 'Thequancute215-sys/cun-zoom'
RESOURCES = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
CONTAINER = os.environ.get('CUN_ZOOM_CONTAINER') == '1'
DESKTOP = os.name == 'nt' and not CONTAINER
# Windows 1.x (repo AI-Zoom) defaulted to these folders. Keep reading them so an upgrade finds the same settings and lessons.
V1_ROOT = Path('D:/HocTap_Zoom')
V1_DATA = V1_ROOT/'Du_lieu_ung_dung'
DEFAULT_DATA = V1_DATA if DESKTOP and V1_DATA.is_dir() else Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'CunZoom'
DATA = Path(os.environ.get('CUN_ZOOM_DATA_DIR', DEFAULT_DATA)).resolve()
DATA.mkdir(parents=True, exist_ok=True)
# The Windows exe ships without Zoom's SDK: each user installs their own copy into MANAGED_SDK from the app.
MANAGED_SDK = DATA/'zoom-sdk'
BUNDLED_SDK = RESOURCES/'vendor/zoom/bin'
SDK = Path(os.environ.get('CUN_ZOOM_SDK_DIR') or (MANAGED_SDK if DESKTOP and not (BUNDLED_SDK/'sdk.dll').is_file() else BUNDLED_SDK)).resolve()
NATIVE = Path(os.environ.get('CUN_ZOOM_WORKER', RESOURCES/'vendor'/('CunZoomBot.exe' if os.name=='nt' else 'CunZoomBot'))).resolve()
WEB = RESOURCES/'web'
PREFERENCES = DATA/'preferences.json'

def sdk_present():
    return any((SDK/name).is_file() for name in ('sdk.dll','libmeetingsdk.so'))

def default_recordings():
    if os.environ.get('CUN_ZOOM_RECORDINGS_DIR'):return Path(os.environ['CUN_ZOOM_RECORDINGS_DIR'])
    if DESKTOP and DATA==V1_DATA.resolve():return V1_ROOT
    if DESKTOP and (Path.home()/'Documents/CunZoom').is_dir():return Path.home()/'Documents/CunZoom'
    return DATA/'lessons'

def preferences():
    default={'recordings_root':str(default_recordings().resolve()),'theme':'light'}
    try:default.update(json.loads(PREFERENCES.read_text(encoding='utf-8')))
    except (OSError,ValueError):pass
    # A container never follows a user-supplied host path outside its mounted lesson root.
    if CONTAINER:default['recordings_root']=str(Path(os.environ.get('CUN_ZOOM_RECORDINGS_DIR','/data/lessons')).resolve())
    return default

def migrate_legacy():
    """Adopt this machine's own Windows 1.x vaults by copying them; sources stay. Nothing is imported from elsewhere."""
    if not DESKTOP:return
    for old,new in (('quyen_zoom.dpapi','zoom.vault'),('calendar.dpapi','calendar.vault')):
        source,target=DATA/old,DATA/new
        if source.is_file() and not target.exists():shutil.copy2(source,target)
