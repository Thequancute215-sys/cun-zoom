"""Build a Windows executable from explicit resources; user data and the Zoom SDK are never bundled."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--onedir',action='store_true')
    args=parser.parse_args()
    import shutil
    shutil.copyfile(ROOT/'tokens.css', ROOT/'web/tokens.css')
    # Some bundled Python runtimes load a distrust-policy PEM beside ssl.py.
    # Preserve that policy file; do not modify ssl.py or disable TLS checks.
    import ssl
    ssl_policy=Path(ssl.__file__).with_name('codex-rejected-cas.pem')
    native=ROOT/'vendor/CunZoomBot.exe'
    if not native.is_file():
        raise SystemExit('Missing native worker. Run prepare_sdk.py and build_native.py first.')
    from PIL import Image,ImageDraw
    image=Image.new('RGBA',(256,256),(0,0,0,0));draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((2,2,254,254),radius=56,fill='#1749b9')
    for y,width in ((72,96),(128,64),(184,96)):
        draw.line([(80,y),(80+width,y)],fill='white',width=18)
    draw.ellipse((176,116,200,140),fill='white')
    image.save(ROOT/'web/icon.png');image.save(ROOT/'web/icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    command=[sys.executable,'-m','PyInstaller','--clean','--noconfirm','--windowed','--name','CunZoom','--icon',str(ROOT/'web/icon.ico'),
             '--paths',str(ROOT/'src'),'--add-data',str(ROOT/'web')+';web',
             '--add-binary',str(native)+';vendor','--collect-all','webview','--collect-all','tzdata',
             '--collect-all','icalendar','--collect-all','recurring_ical_events','--collect-all','ctranslate2',
             '--collect-all','faster_whisper','--collect-all','tokenizers','--collect-all','av',
             '--hidden-import','pystray._win32','--hidden-import','PIL._tkinter_finder',
             '--exclude-module','torch','--exclude-module','tensorflow','--exclude-module','PyQt5',
             '--exclude-module','PyQt6','--exclude-module','PySide6','--exclude-module','pytest',
             '--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'build/pyinstaller'),
             '--specpath',str(ROOT/'build'), '--onedir' if args.onedir else '--onefile',str(ROOT/'src/main.py')]
    if ssl_policy.is_file():
        command[3:3]=['--add-data',str(ssl_policy)+';.']
    result=subprocess.run(command,cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    exe=ROOT/'dist'/('CunZoom/CunZoom.exe' if args.onedir else 'CunZoom.exe')
    digest=hashlib.sha256(exe.read_bytes()).hexdigest()
    if not args.onedir:
        (ROOT/'dist/SHA256SUMS.txt').write_text(digest+'  CunZoom.exe\n',encoding='ascii')
        version=__import__('re').search(r"VERSION = '([^']+)'",(ROOT/'src/paths.py').read_text()).group(1)
        (ROOT/'dist/build-info.json').write_text(json.dumps({'version':version,'sha256':digest,'bytes':exe.stat().st_size,'user_data_included':False,'zoom_sdk_included':False},indent=2),encoding='utf-8')
    print(json.dumps({'built':str(exe),'bytes':exe.stat().st_size,'sha256':digest}))


if __name__=='__main__':main()
