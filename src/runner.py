"""Owns the native bot process; tokens travel only over its private stdin pipe."""
import base64,json,re,subprocess,threading,time,urllib.error,urllib.parse,urllib.request,uuid
from datetime import datetime
from pathlib import Path
import vault

from paths import DATA, NATIVE, SDK, preferences, sdk_present
ROOT=DATA
EXE=NATIVE
STATE_FILE=DATA/'native_state.json'
MUTEX=threading.RLock()
PROCESS=None
CURRENT={'state':'not_built','auth_test_passed':False,'audio_bytes':0,'slides':0,'running':False}
try:
    previous=json.loads(STATE_FILE.read_text(encoding='utf-8'))
    if previous.get('running'):previous.update(state='interrupted',running=False)
    CURRENT.update(previous)
except (OSError,ValueError):pass

def persist():
    CURRENT['updated']=datetime.now().isoformat()
    temp=STATE_FILE.with_suffix('.tmp');temp.write_text(json.dumps(CURRENT,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(STATE_FILE)

def state():
    with MUTEX:
        value={**CURRENT,'built':EXE.exists() and sdk_present()}
        if value['state']=='not_built' and value['built']:value['state']='not_tested'
        return value

def start_transcription(directory):
    import sys
    directory=Path(directory);(directory/'02_Tom_tat').mkdir(parents=True,exist_ok=True)
    # Mark the lesson busy before the worker starts so a sync pass cannot launch it twice.
    (directory/'02_Tom_tat/trang_thai.json').write_text(json.dumps({'state':'processing','time':datetime.now().isoformat()}),encoding='utf-8')
    command=[sys.executable,'--transcribe',str(directory)] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).parent/'transcribe.py'),str(directory)]
    with (directory/'02_Tom_tat/xu_ly.log').open('a',encoding='utf-8') as log:
        subprocess.Popen(command,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def name(value):
    value=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value)).strip(' .')[:100]
    if not value or value.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:raise ValueError('Tên môn/buổi học không hợp lệ.')
    return value

def access(config,token_request,store):
    oauth=config.get('oauth',{})
    if not oauth.get('refresh_token'):raise ValueError('Cần kết nối quyền Zoom trước.')
    if oauth.get('expires_at',0)>time.time()+120:return oauth['access_token']
    result=token_request(config,{'grant_type':'refresh_token','refresh_token':oauth['refresh_token']})
    if not result.get('refresh_token') or not result.get('access_token'):raise ValueError('Cần kết nối lại quyền Zoom.')
    result['expires_at']=time.time()+result.get('expires_in',3600);config['oauth']=result;vault.save(store,config)
    return result['access_token']

def obf_token(access_token,meeting):
    url='https://api.zoom.us/v2/users/me/token?'+urllib.parse.urlencode({'type':'onbehalf','meeting_id':meeting})
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+access_token})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:result=json.load(response)
    except urllib.error.HTTPError as e:raise ValueError('Zoom từ chối cấp OBF (HTTP '+str(e.code)+'). Kiểm tra quyền ứng dụng và việc bạn đã ở trong phòng.') from None
    if not result.get('token'):raise ValueError('Zoom chưa trả token OBF.')
    return result['token']

def stop():
    with MUTEX:
        if PROCESS is None or PROCESS.poll() is not None:return
        try:PROCESS.stdin.write('STOP\n');PROCESS.stdin.flush()
        except (OSError,ValueError):pass
        CURRENT['state']='stopping';persist()

def shutdown():
    stop()
    with MUTEX:process=PROCESS
    if process is not None and process.poll() is None:
        try:process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def launch(config,jwt,mode='auth-test',meeting='',password='',subject='',title='',consent=False):
    global PROCESS
    with MUTEX:
        if not EXE.exists():raise ValueError('Chưa biên dịch xong bộ chạy bot.')
        if not sdk_present():raise ValueError('Chưa có Zoom SDK. Windows: Cài đặt → Kết nối → Cài Zoom SDK (.zip). Docker: đặt SDK vào vendor/zoom-linux.')
        if PROCESS is not None and PROCESS.poll() is None:raise ValueError('Bot đang chạy; hãy dừng trước khi thử lần khác.')
        directory=None;obf=''
        if mode!='auth-test':
            if consent is not True:raise ValueError('Cần xác nhận đã vào đúng lớp và được phép ghi.')
            meeting=re.sub(r'[ -]','',str(meeting))
            if not re.fullmatch(r'\d{9,11}',meeting):raise ValueError('ID phòng phải có 9–11 chữ số.')
            subject=name(subject);title=name(title or 'Buoi_hoc')
            if '\n' in password or '\r' in password or len(password)>256:raise ValueError('Mật khẩu phòng không hợp lệ.')
            # The access token was refreshed by the caller; never send it to the native process.
            obf=obf_token(config['oauth']['access_token'],meeting)
            directory=Path(preferences()['recordings_root'])/subject/(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'_'+title+'_'+uuid.uuid4().hex[:4])
            for sub in ['01_Tai_lieu_goc','02_Tom_tat','03_Bai_tap_va_on_tap']:(directory/sub).mkdir(parents=True,exist_ok=True)
            (directory/'buoi_hoc.json').write_text(json.dumps({'subject':subject,'title':title,'requested':datetime.now().isoformat(),'source':'Zoom Meeting SDK','state':'joining','recording_confirmed':False},ensure_ascii=False,indent=2),encoding='utf-8')
        fields=[mode,jwt,meeting,password,'Cun - Tro ly ghi bai',obf,str(directory or '')]
        p=subprocess.Popen([str(EXE),str(SDK),'ipc'],cwd=SDK,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        PROCESS=p
        CURRENT.update(state='starting',auth_code=None,running=True,audio_bytes=0,slides=0,mode=mode,path=str(directory or ''),exit_code=None,last_error=None)
        persist()
        p.stdin.write(''.join(base64.b64encode(v.encode()).decode()+'\n' for v in fields));p.stdin.flush()
        threading.Thread(target=read_events,args=(p,mode,directory),daemon=True).start()

def read_events(p,mode,directory):
    authenticated=False;initialized=False
    try:
        for line in p.stdout:
            try:
                item=json.loads(line);kind=item.get('state','')
                if not re.fullmatch(r'[a-z_]{1,64}',kind):continue
                code=int(item.get('code',0));amount=max(0,int(item.get('amount',0)))
            except (ValueError,TypeError):continue
            with MUTEX:
                CURRENT['state']=kind;CURRENT['code']=code
                if kind=='sdk_initialized':initialized=code==0
                if kind=='sdk_authenticated':
                    authenticated=code==0
                    CURRENT['auth_code']=code
                    if code:CURRENT['last_error']={'state':'sdk_authenticated','code':code}
                if kind=='receiving_audio':CURRENT['audio_bytes']=amount
                if kind=='slide_saved':CURRENT['slides']=amount
                if kind=='stopped':CURRENT['audio_bytes']=amount
                if any(word in kind for word in ['failed','error','timeout','missing','revoked','denied']):CURRENT['last_error']={'state':kind,'code':code}
                persist()
        rc=p.wait()
        with MUTEX:
            CURRENT['running']=False;CURRENT['exit_code']=rc
            if mode=='auth-test':
                CURRENT['auth_test_passed']=initialized and authenticated and rc==0
                CURRENT['state']='auth_test_passed' if CURRENT['auth_test_passed'] else 'auth_test_failed'
            else:
                CURRENT['state']='stopped_with_audio' if CURRENT['audio_bytes']>0 else 'stopped_without_audio'
                if rc!=0 and not CURRENT.get('last_error'):CURRENT['last_error']={'state':'native_process_exited','code':rc}
            persist()
            if directory:
                meta=json.loads((directory/'buoi_hoc.json').read_text(encoding='utf-8'));meta.update(ended=datetime.now().isoformat(),state=CURRENT['state'],recording_confirmed=CURRENT['audio_bytes']>0,audio_bytes=CURRENT['audio_bytes'],slides=CURRENT['slides'],last_error=CURRENT['last_error']);(directory/'buoi_hoc.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            received_bytes=CURRENT['audio_bytes']
        if directory and received_bytes>0:start_transcription(directory)

    except Exception:
        with MUTEX:CURRENT.update(state='worker_error',running=p.poll() is None,last_error={'state':'worker_error','code':-1});persist()
        try:p.stdin.write('STOP\n');p.stdin.flush()
        except Exception:pass
