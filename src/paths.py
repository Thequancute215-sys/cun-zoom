"""Portable resources and explicit per-installation storage; Windows upgrades keep the 1.x locations."""
import json
import os
from pathlib import Path
import shutil
import stat
import sys

VERSION = '2.2.1'
REPOSITORY = 'Thequancute215-sys/cun-zoom'
RESOURCES = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
CONTAINER = os.environ.get('CUN_ZOOM_CONTAINER') == '1'
DESKTOP = os.name == 'nt' and not CONTAINER
# Grants to these still leave an item private: SYSTEM, Administrators, TrustedInstaller, and CREATOR OWNER / OWNER RIGHTS,
# which only reach the item's owner, itself checked to be this user, SYSTEM or Administrators.
SERVICE_SIDS = {'S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464','S-1-3-0','S-1-3-4'}
# Read data, write, append, extended attributes, delete child, attributes, delete, change permissions/owner, generic read/write/all.
SHARED_RIGHTS = 0xD00D0157

def private_path(path):
    """True on Windows when `path` is not a link, belongs to this user (or SYSTEM/Administrators) and no other account can read or change it."""
    if os.name != 'nt':return False
    try:
        if os.lstat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:return False
    except OSError:return False
    import ctypes
    from ctypes import wintypes as W
    P=ctypes.c_void_p
    advapi=ctypes.WinDLL('advapi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    advapi.GetNamedSecurityInfoW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD]+[ctypes.POINTER(P)]*5;advapi.GetNamedSecurityInfoW.restype=W.DWORD
    advapi.ConvertSidToStringSidW.argtypes=[P,ctypes.POINTER(P)];advapi.ConvertSidToStringSidW.restype=W.BOOL
    advapi.GetAce.argtypes=[P,W.DWORD,ctypes.POINTER(P)];advapi.GetAce.restype=W.BOOL
    advapi.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,ctypes.POINTER(W.HANDLE)];advapi.OpenProcessToken.restype=W.BOOL
    advapi.GetTokenInformation.argtypes=[W.HANDLE,ctypes.c_int,P,W.DWORD,ctypes.POINTER(W.DWORD)];advapi.GetTokenInformation.restype=W.BOOL
    kernel.GetCurrentProcess.restype=W.HANDLE;kernel.CloseHandle.argtypes=[W.HANDLE];kernel.LocalFree.argtypes=[P];kernel.LocalFree.restype=P
    def text(sid):
        out=P()
        if not advapi.ConvertSidToStringSidW(sid,ctypes.byref(out)):raise OSError(ctypes.get_last_error())
        try:return ctypes.wstring_at(out.value)
        finally:kernel.LocalFree(out)
    token=W.HANDLE();size=W.DWORD()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):return False
    try:
        advapi.GetTokenInformation(token,1,None,0,ctypes.byref(size))
        user=ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token,1,user,size,ctypes.byref(size)):return False
        me=text(ctypes.cast(user,ctypes.POINTER(P))[0])
    except OSError:return False
    finally:kernel.CloseHandle(token)
    owner,dacl,descriptor=P(),P(),P()
    # Owner and DACL of the item itself; a link was refused above, so this is the real folder or file.
    if advapi.GetNamedSecurityInfoW(str(path),1,0x5,ctypes.byref(owner),None,ctypes.byref(dacl),None,ctypes.byref(descriptor)):return False
    try:
        if not dacl.value or text(owner) not in SERVICE_SIDS|{me}:return False
        for index in range(ctypes.cast(dacl,ctypes.POINTER(W.WORD))[2]):
            ace=P()
            if not advapi.GetAce(dacl,index,ctypes.byref(ace)):return False
            kind=ctypes.cast(ace,ctypes.POINTER(ctypes.c_ubyte))[0]
            if kind==1:continue
            # Only plain allow and deny entries are understood; anything else (conditional, callback) counts as shared.
            if kind!=0:return False
            if ctypes.cast(ace,ctypes.POINTER(W.DWORD))[1]&SHARED_RIGHTS and text(ace.value+8) not in SERVICE_SIDS|{me}:return False
        return True
    except OSError:return False
    finally:kernel.LocalFree(descriptor)

# Windows 1.x (repo AI-Zoom) defaulted to these folders. Keep reading them so an upgrade finds the same settings and lessons.
V1_ROOT = Path('D:/HocTap_Zoom')
V1_DATA = V1_ROOT/'Du_lieu_ung_dung'
# D: is often writable by every account. Adopt the 1.x folder only when it is this user's alone: it holds the app token
# and the sdk.dll the bot loads. Otherwise use a new folder and say why (V1_REFUSED) instead of loading another user's files.
def v1_private():
    return DESKTOP and V1_DATA.is_dir() and private_path(V1_ROOT) and private_path(V1_DATA)
V1_ADOPTED = v1_private()
DEFAULT_DATA = V1_DATA if V1_ADOPTED else Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'CunZoom'
DATA = Path(os.environ.get('CUN_ZOOM_DATA_DIR', DEFAULT_DATA)).resolve()
V1_REFUSED = DESKTOP and V1_DATA.is_dir() and not V1_ADOPTED and 'CUN_ZOOM_DATA_DIR' not in os.environ
# The one command that makes the 1.x folder this user's alone; shown with V1_REFUSED.
V1_LOCK = f'icacls "{V1_ROOT}" /inheritance:r /grant:r "{os.environ.get("USERNAME","%USERNAME%")}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F"'
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
