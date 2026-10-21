"""Compile against the SDK on this machine, without modifying the SDK itself."""
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HEADERS=ROOT/'build/sdk/zoom_sdk_c_sharp_wrap/h'


def body(text,name):
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S);text=re.sub(r'//[^\n]*','',text)
    match=re.search(r'\bclass\s+'+name+r'\s*\{',text)
    if not match:raise ValueError(name)
    start=match.end();depth=1;index=start
    while depth:depth+=(text[index]=='{')-(text[index]=='}');index+=1
    return text[start:index-1]


def main():
    out=['#pragma once','using namespace ZOOM_SDK_NAMESPACE;']
    for name,file in [('IAuthServiceEvent','auth_service_interface.h'),('IMeetingServiceEvent','meeting_service_interface.h'),('IMeetingRecordingCtrlEvent','meeting_service_components/meeting_recording_interface.h')]:
        block=body((HEADERS/file).read_text(encoding='utf-8-sig'),name)
        out.append('class '+name+'Adapter : public '+name+' { public:')
        for method,args in re.findall(r'virtual\s+void\s+(\w+)\s*\((.*?)\)\s*=\s*0\s*;',block,re.S):
            if method=='onTranscodingStatusChanged':continue # Linux-only callback in official header.
            out.append('void '+method+'('+re.sub(r'\s+',' ',args).strip()+') override {}')
        out.append('};')
    (ROOT/'native/adapters.h').write_text('\n'.join(out),encoding='utf-8')
    candidates=[]
    vswhere=Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    if vswhere.exists():
        installation=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
        if installation:candidates.append(Path(installation)/'VC/Auxiliary/Build/vcvars64.bat')
    compiler=next((p for p in candidates if p.is_file()),None)
    if not compiler:raise SystemExit('Microsoft C++ Build Tools are required for the native worker.')
    (ROOT/'build/obj').mkdir(parents=True,exist_ok=True)
    command='@echo off\ncall "'+str(compiler)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /O1 /MD /DWIN32 /DUNICODE /D_UNICODE /I"'+str(HEADERS)+'" /Fo"'+str(ROOT/'build/obj/bot.obj')+'" /Fe"'+str(ROOT/'vendor/CunZoomBot.exe')+'" "'+str(ROOT/'native/bot.cpp')+'" /link crypt32.lib gdiplus.lib user32.lib ole32.lib\nexit /b %errorlevel%\n'
    batch=ROOT/'build/compile.cmd';batch.write_text(command,encoding='utf-8')
    result=subprocess.run(['cmd.exe','/d','/c',str(batch)],cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
