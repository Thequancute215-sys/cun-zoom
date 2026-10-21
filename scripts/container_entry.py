"""Non-root container supervisor. No host audio/video devices or Docker socket."""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

os.umask(0o077)
data=Path(os.environ.get('CUN_ZOOM_DATA_DIR','/data'))
data.mkdir(parents=True,exist_ok=True)
home=Path(os.environ.get('HOME','/data/home'));home.mkdir(parents=True,exist_ok=True)
runtime=data/'runtime';runtime.mkdir(exist_ok=True);runtime.chmod(0o700)
os.environ['XDG_RUNTIME_DIR']=str(runtime)
os.environ.setdefault('DISPLAY',':99')
os.environ['PULSE_SERVER']='unix:'+str(runtime/'pulse/native')
os.environ['CUN_ZOOM_CONTAINER']='1'
sdk=Path(os.environ.get('CUN_ZOOM_SDK_DIR','/opt/zoom-sdk'))
worker=Path(os.environ.get('CUN_ZOOM_WORKER','/data/native/CunZoomBot'))
worker.parent.mkdir(parents=True,exist_ok=True)
paths=[worker.parent/'runtime',sdk,sdk/'qt_libs',sdk/'qt_libs/Qt/lib']
paths[0].mkdir(exist_ok=True)
os.environ['LD_LIBRARY_PATH']=':'.join(map(str,paths))
children=[]
main=None


def terminate(*_):
    if main and main.poll() is None:main.terminate()


signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
try:
    children.append(subprocess.Popen(['Xvfb',os.environ['DISPLAY'],'-screen','0','1280x720x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    pulse=runtime/'pulse';pulse.mkdir(exist_ok=True)
    children.append(subprocess.Popen(['pulseaudio','--daemonize=no','--exit-idle-time=-1','--disallow-exit','--use-pid-file=no','--log-target=stderr','-n',
        '--load=module-native-protocol-unix socket='+str(pulse/'native')+' auth-anonymous=0',
        '--load=module-null-sink sink_name=cunzoom sink_properties=device.description=CunZoom',
        '--load=module-remap-source source_name=cunzoom_mic master=cunzoom.monitor'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    for _ in range(50):
        if (pulse/'native').exists():break
        time.sleep(0.1)
    config=home/'.config';config.mkdir(exist_ok=True)
    (config/'zoomus.conf').write_text('[General]\nsystem.audio.type=default\n',encoding='utf-8')
    if (sdk/'libmeetingsdk.so').is_file() and (sdk/'h/zoom_sdk.h').is_file():
        for lib in sdk.glob('lib*.so*'):
            link=paths[0]/lib.name
            if not link.exists():link.symlink_to(lib)
        soname=paths[0]/'libmeetingsdk.so.1'
        if not soname.exists():soname.symlink_to(sdk/'libmeetingsdk.so')
        digest=hashlib.sha256()
        for source in [sdk/'libmeetingsdk.so',*sorted((sdk/'h').rglob('*.h')),Path('/app/native/linux_bot.cpp'),Path('/app/scripts/build_linux.py')]:
            with source.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        stamp=worker.parent/'build.sha256'
        if not worker.exists() or not stamp.exists() or stamp.read_text()!=digest.hexdigest():
            try:
                subprocess.run([sys.executable,'/app/scripts/build_linux.py',str(sdk),str(worker)],check=True)
                stamp.write_text(digest.hexdigest())
            except subprocess.CalledProcessError:
                worker.unlink(missing_ok=True)
                print('SDK compile failed. UI remains available; inspect compiler diagnostics above.',flush=True)
    else:
        worker.unlink(missing_ok=True)
        print('SDK not mounted. See docs/INSTALL.md; recording is disabled.',flush=True)
    main=subprocess.Popen([sys.executable,'/app/src/container_main.py'])
    sys.exit(main.wait())
finally:
    for child in reversed(children):
        if child.poll() is None:child.terminate()
    for child in children:
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill()
