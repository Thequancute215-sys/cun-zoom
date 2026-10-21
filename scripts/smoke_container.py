"""Exercise a real running container, without printing generated passwords/tokens."""
import base64
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

name=sys.argv[1] if len(sys.argv)>1 else 'cun-zoom-test'
base='http://127.0.0.1:18767'


def run(*args):return subprocess.check_output(['docker',*args],text=True).strip()


def request(path,body=None,auth=None,token=None,origin=None,expected=200):
    headers={}
    if auth:headers['Authorization']=auth
    if token:headers['X-App-Token']=token
    if origin:headers['Origin']=origin
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=10) as response:
            raw=response.read();code=response.status
    except urllib.error.HTTPError as error:code=error.code;raw=error.read()
    assert code==expected,(path,code,expected)
    return raw


for attempt in range(90):
    try:request('/health');break
    except (OSError,AssertionError):time.sleep(2)
else:raise SystemExit('Container did not become healthy.')
assert run('exec',name,'id','-u')=='10001'
password=run('exec',name,'cat','/data/access-password.txt')
assert len(password)>=24
auth='Basic '+base64.b64encode(('cunzoom:'+password).encode()).decode()
request('/',expected=401)
request('/status',{},expected=401)
page=request('/',auth=auth).decode()
token=re.search(r'name="app-token" content="([^"]+)"',page).group(1)
request('/status',{},auth=auth,expected=403)
request('/status',{},auth=auth,token=token,origin='https://attacker.example',expected=403)
state=json.loads(request('/status',{},auth=auth,token=token,origin=base))
assert state['container'] and not state['zoom']['sdk_available']
request('/settings/zoom',{'client_id':'synthetic-ci-client','public_client_id':'synthetic-ci-public','client_secret':'synthetic-ci-private'},auth=auth,token=token)
encrypted=run('exec',name,'python','-c',"from pathlib import Path;p=Path('/data/zoom.vault');assert b'synthetic-ci-private' not in p.read_bytes();print('encrypted')")
assert encrypted=='encrypted'
request('/vault.key',auth=auth,expected=404)
run('restart',name)
for attempt in range(45):
    try:
        page=request('/',auth=auth).decode();break
    except OSError:time.sleep(2)
else:raise SystemExit('Container did not return after restart.')
assert run('exec',name,'cat','/data/access-password.txt')==password
token=re.search(r'name="app-token" content="([^"]+)"',page).group(1)
state=json.loads(request('/status',{},auth=auth,token=token,origin=base))
assert state['zoom']['configured'] and state['zoom']['client_id']=='synthetic-ci-client'
print('Docker smoke passed: non-root, authenticated UI/API, CSRF, encrypted configuration and restart persistence.')
