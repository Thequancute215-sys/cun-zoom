"""Cún Zoom Windows desktop entry point and packaged transcription worker."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=18766)
    parser.add_argument('--data-dir')
    parser.add_argument('--no-migrate', action='store_true')
    parser.add_argument('--self-test', metavar='REPORT')
    parser.add_argument('--transcribe', metavar='FOLDER')
    args = parser.parse_args()
    if args.self_test:
        Path(args.self_test).write_text(json.dumps({'stage':'starting'}),encoding='utf-8')
    if args.data_dir:
        os.environ['CUN_ZOOM_DATA_DIR'] = args.data_dir
    from paths import DATA, RESOURCES, VERSION, NATIVE, SDK, migrate_legacy
    if args.transcribe:
        import transcribe
        sys.argv = [sys.argv[0], args.transcribe]
        transcribe.main()
        return
    if args.self_test:
        import tempfile
        import vault
        import ssl
        context = ssl.create_default_context()
        https_context = context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        Path(args.self_test).write_text(json.dumps({'stage':'loading_service'}),encoding='utf-8')
        from server import Service
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'roundtrip.dpapi'
            vault.save(path,{'test':'synthetic'})
            encrypted=vault.load(path)=={'test':'synthetic'} and b'synthetic' not in path.read_bytes()
        Path(args.self_test).write_text(json.dumps({'stage':'encryption_passed','encryption_roundtrip':encrypted}),encoding='utf-8')
        service=Service(port=0)
        resources=all((RESOURCES/'web'/name).is_file() for name in ['index.html','style.css','app.js','logo.svg'])
        try:
            import subprocess
            probe=subprocess.run([str(NATIVE),str(SDK),'check'],capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            sdk_loadable=probe.returncode==0 and 'sdk_loaded' in probe.stdout
        except (OSError, subprocess.TimeoutExpired):
            sdk_loadable=False
        import runner
        native_state=runner.state()
        report={'version':VERSION,'sdk_bundled':(RESOURCES/'vendor/zoom').exists(),'https_context':https_context,'encryption_roundtrip':encrypted,'web_resources':resources,
                'native_worker':NATIVE.is_file(),'sdk_loadable':sdk_loadable,'server_port':service.port,
                'native_status_consistent':native_state['built'] and native_state['state']!='not_built',
                'calendar_configured':service.calendar.status()['configured']}
        service.http.server_close()
        Path(args.self_test).write_text(json.dumps(report,indent=2),encoding='utf-8')
        if not all(report[k] for k in ['https_context','encryption_roundtrip','web_resources','native_worker','sdk_loadable','native_status_consistent']):
            raise SystemExit(2)
        return
    if not args.no_migrate:
        migrate_legacy()
    from server import Service
    if args.serve:
        service=Service(args.port)
        service.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            service.stop()
        return

    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
    kernel.CreateMutexW.restype=ctypes.c_void_p
    mutex=kernel.CreateMutexW(None,False,'Local\\CunZoom.Desktop.v1')
    if ctypes.get_last_error()==183:
        try:
            session=json.loads((DATA/'session.json').read_text(encoding='utf-8'))
            request=urllib.request.Request(session['base']+'/app/show',data=b'{}',headers={'X-App-Token':session['token'],'Content-Type':'application/json'})
            urllib.request.urlopen(request,timeout=3).close()
        except Exception:
            ctypes.windll.user32.MessageBoxW(None,'Cún Zoom đang chạy. Mở ứng dụng từ biểu tượng ở khay hệ thống.','Cún Zoom',0x40)
        return

    import calendar_watch
    import pystray
    import webview
    from PIL import Image
    try:
        service=Service(args.port)
    except OSError:
        ctypes.windll.user32.MessageBoxW(None,'Cổng ứng dụng đang được sử dụng. Đóng bản Cún Zoom cũ rồi mở lại.','Cún Zoom',0x40)
        return
    exiting=threading.Event()
    window=webview.create_window('Cún Zoom · Không gian học tập',service.base,width=1380,height=940,
                                min_size=(960,680),background_color='#f7f8f5',text_select=True)
    def show(*_):
        window.show()
        window.restore()
    service.show_window=show
    def choose():
        result=window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None
    service.choose_folder=choose
    def choose_sdk():
        result=window.create_file_dialog(webview.OPEN_DIALOG,file_types=('Zoom Meeting SDK (*.zip)',))
        return result[0] if result else None
    service.choose_sdk_archive=choose_sdk
    icon=pystray.Icon('CunZoom',Image.open(RESOURCES/'web/icon.png'),'Cún Zoom',menu=pystray.Menu(
        pystray.MenuItem('Mở Cún Zoom',show,default=True),
        pystray.MenuItem('Thoát Cún Zoom',lambda *_:threading.Thread(target=quit_app,daemon=True).start())))
    def quit_app():
        if exiting.is_set():
            return
        exiting.set()
        service.stop()
        import runner
        for _ in range(30):
            if not runner.state().get('running'):
                break
            time.sleep(.2)
        icon.stop()
        window.destroy()
    service.quit_app=quit_app
    def on_closing():
        if exiting.is_set():
            return True
        window.hide()
        return False
    window.events.closing+=on_closing
    calendar_watch.NOTIFIER=lambda title,text:icon.notify(text,title)
    icon.run_detached()
    service.start()
    (DATA/'session.json').write_text(json.dumps({'base':service.base,'token':service.token,'pid':os.getpid()}),encoding='utf-8')
    try:
        webview.start(gui='edgechromium',private_mode=False,storage_path=str(DATA/'webview'),debug=False,icon=str(RESOURCES/'web/icon.ico'))
    finally:
        if not exiting.is_set():
            service.stop()
            icon.stop()
        (DATA/'session.json').unlink(missing_ok=True)
        kernel.CloseHandle(ctypes.c_void_p(mutex))


if __name__=='__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        # Do not dump request objects, URLs, or credentials into desktop error logs.
        message='Cún Zoom chưa khởi động được ('+type(error).__name__+'). Xem hướng dẫn cài đặt hoặc nhờ Cún kiểm tra.'
        if getattr(sys,'frozen',False):
            ctypes.windll.user32.MessageBoxW(None,message,'Cún Zoom',0x10)
        else:
            raise
