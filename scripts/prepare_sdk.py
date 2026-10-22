"""Extract the official, manually supplied SDK without path traversal or code execution."""
import argparse
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import sdk_setup


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive');args=parser.parse_args()
    archive=Path(args.archive).resolve()
    target=ROOT/'build/sdk'
    try:sdk_setup.extract(archive,target)
    except ValueError as error:raise SystemExit(str(error))
    # build_native.py compiles against the C# wrapper package's C++ headers.
    if not (target/'zoom_sdk_c_sharp_wrap/h/zoom_sdk.h').is_file():raise SystemExit('SDK archive has no expected Windows x64 headers.')
    # Only for local builds and the CI self-test; build.py never packages this folder.
    shutil.copytree(target/'bin',ROOT/'vendor/zoom/bin',dirs_exist_ok=True)
    print('Official x64 SDK prepared. Source archive preserved.')


if __name__=='__main__':main()
