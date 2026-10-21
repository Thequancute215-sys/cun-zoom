"""Extract the official, manually supplied SDK without path traversal or code execution."""
import argparse
from pathlib import Path, PurePosixPath
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive');args=parser.parse_args()
    archive=Path(args.archive).resolve()
    with zipfile.ZipFile(archive) as source:
        names=source.namelist()
        marker='/x64/zoom_sdk_c_sharp_wrap/h/zoom_sdk.h'
        header=next((name for name in names if name.endswith(marker)),None)
        if not header:raise SystemExit('SDK archive has no expected Windows x64 headers.')
        prefix=header[:header.index('/x64/')]+ '/x64/'
        target=(ROOT/'build/sdk').resolve()
        for member in source.infolist():
            if not member.filename.startswith(prefix):continue
            relative=PurePosixPath(member.filename[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):raise SystemExit('Unsafe SDK archive path.')
            path=(target/str(relative)).resolve()
            if not path.is_relative_to(target):raise SystemExit('SDK archive escaped output folder.')
            if member.is_dir():path.mkdir(parents=True,exist_ok=True);continue
            path.parent.mkdir(parents=True,exist_ok=True)
            with source.open(member) as src,path.open('wb') as dst:shutil.copyfileobj(src,dst)
        runtime=ROOT/'vendor/zoom/bin'
        shutil.copytree(target/'bin',runtime,dirs_exist_ok=True)
    print('Official x64 SDK prepared. Source archive preserved.')


if __name__=='__main__':main()
