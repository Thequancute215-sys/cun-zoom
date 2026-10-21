"""Build only our worker against a separately mounted official Zoom Linux SDK."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def class_body(text,name):
    match=re.search(r'\bclass\s+'+name+r'\s*\{',text)
    if not match:raise ValueError('SDK interface not found: '+name)
    start=match.end();depth=1;index=start
    while depth and index<len(text):
        depth+=(text[index]=='{')-(text[index]=='}');index+=1
    if depth:raise ValueError('Incomplete SDK interface: '+name)
    return text[start:index-1]


def build(sdk,out,syntax_only=False):
    sdk=sdk.resolve();out=out.resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if not (sdk/'h/zoom_sdk.h').is_file() or (not syntax_only and not (sdk/'libmeetingsdk.so').is_file()):
        raise ValueError('SDK cần có h/zoom_sdk.h và libmeetingsdk.so ngay trong thư mục được mount.')
    compiler=['g++','-std=c++17','-I'+str(sdk/'h')]
    includes=['zoom_sdk.h','auth_service_interface.h','meeting_service_interface.h','meeting_service_components/meeting_recording_interface.h']
    # Preprocess first so callbacks for other platforms cannot leak into adapters.
    unit='\n'.join('#include <'+header+'>' for header in includes)
    text=subprocess.check_output(compiler+['-E','-P','-x','c++','-'],input=unit,text=True)
    adapters=['#pragma once','using namespace ZOOM_SDK_NAMESPACE;']
    for name in ['IAuthServiceEvent','IMeetingServiceEvent','IMeetingRecordingCtrlEvent']:
        adapters.append('class '+name+'Adapter : public '+name+' { public:')
        for method,args in re.findall(r'virtual\s+void\s+(\w+)\s*\((.*?)\)\s*=\s*0\s*;',class_body(text,name),re.S):
            adapters.append('void '+method+'('+re.sub(r'\s+',' ',args).strip()+') override {}')
        adapters.append('};')
    (out.parent/'linux_adapters.h').write_text('\n'.join(adapters),encoding='utf-8')
    flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','glib-2.0','gio-2.0'],text=True))
    temporary=out.with_suffix('.new')
    if syntax_only:
        subprocess.run(compiler+['-pthread','-I'+str(out.parent),str(ROOT/'native/linux_bot.cpp'),'-fsyntax-only',*flags],check=True)
        print('Linux SDK interface syntax check passed.',flush=True)
        return
    subprocess.run(compiler+['-O2','-pthread','-I'+str(out.parent),str(ROOT/'native/linux_bot.cpp'),'-L'+str(sdk),'-lmeetingsdk','-ljpeg',*flags,'-Wl,-rpath,'+str(sdk),'-o',str(temporary)],check=True)
    temporary.chmod(0o700);temporary.replace(out)
    print('Linux worker compiled; SDK remains outside the image.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('sdk',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--syntax-only',action='store_true')
    args=parser.parse_args();build(args.sdk,args.output,args.syntax_only)
