"""Portable resources and explicit per-installation storage, with no personal defaults."""
import json
import os
from pathlib import Path
import sys

VERSION = '2.0.0'
REPOSITORY = 'Thequancute215-sys/cun-zoom'
RESOURCES = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
CONTAINER = os.environ.get('CUN_ZOOM_CONTAINER') == '1'
DEFAULT_DATA = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'CunZoom'
DATA = Path(os.environ.get('CUN_ZOOM_DATA_DIR', DEFAULT_DATA)).resolve()
DATA.mkdir(parents=True, exist_ok=True)
SDK = Path(os.environ.get('CUN_ZOOM_SDK_DIR', RESOURCES/'vendor/zoom/bin')).resolve()
NATIVE = Path(os.environ.get('CUN_ZOOM_WORKER', RESOURCES/'vendor'/('CunZoomBot.exe' if os.name=='nt' else 'CunZoomBot'))).resolve()
WEB = RESOURCES/'web'
PREFERENCES = DATA/'preferences.json'

def preferences():
    default={'recordings_root':str(Path(os.environ.get('CUN_ZOOM_RECORDINGS_DIR', DATA/'lessons')).resolve()),'theme':'light'}
    try:default.update(json.loads(PREFERENCES.read_text(encoding='utf-8')))
    except (OSError,ValueError):pass
    # A container never follows a user-supplied host path outside its mounted lesson root.
    if CONTAINER:default['recordings_root']=str(Path(os.environ.get('CUN_ZOOM_RECORDINGS_DIR','/data/lessons')).resolve())
    return default

def migrate_legacy():
    """Public installs start empty. No implicit copy from another person's installation."""
    return
