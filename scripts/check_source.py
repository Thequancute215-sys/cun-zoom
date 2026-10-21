"""Allow source only. Run before publishing or packaging from a checkout."""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','.venv','build','dist','vendor','__pycache__','.local'}


def main():
    errors=[]
    if (ROOT/'.git').exists():
        tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
        for name in tracked:
            p=Path(name)
            if (name.startswith('vendor/') and name!='vendor/README.md') or p.suffix.lower() in {'.vault','.dpapi','.key','.ics','.exe','.dll','.so','.wav','.webm','.xz'} or p.name in {'access-password.txt','session.json','native_state.json'}:
                errors.append(name)
    for path in ROOT.rglob('*'):
        relative=path.relative_to(ROOT)
        if any(part in SKIP for part in relative.parts) or not path.is_file():continue
        if path.parent==ROOT and path.name.startswith('build-') and path.suffix=='.log':continue
        if path.suffix.lower() in {'.vault','.dpapi','.key','.ics','.log','.tmp','.dll','.exe','.so','.wav','.webm','.xz'}:
            errors.append(str(relative));continue
        if path.suffix.lower() not in {'.py','.html','.css','.js','.md','.json','.yml','.yaml','.txt'}:continue
        text=path.read_text(encoding='utf-8-sig')
        # Match real private feed addresses, not the synthetic test fixture.
        feeds=re.findall(r'https://calendar\.google\.com/calendar/ical/[^\s\'\"<>]+/private-[A-Za-z0-9]+/basic\.ics',text)
        if any('private-synthetic' not in item for item in feeds):errors.append(str(relative))
        if re.search(r'gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}',text):errors.append(str(relative))
    if errors:raise SystemExit('Do not publish these files: '+', '.join(sorted(set(errors))))
    print('Source check passed: no runtime credentials or private calendar feed found.')


if __name__=='__main__':main()
