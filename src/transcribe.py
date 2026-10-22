import json, re, sys, traceback
from pathlib import Path
from datetime import datetime

def draft(text):
    sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n',text) if len(s.strip())>35]
    stop={'những','được','trong','chúng','mình','chúng ta','các','này','một','là','và','thì','của','cho','với'}
    freq={}
    for word in re.findall(r'\w+',text.lower()):
        if len(word)>2 and word not in stop: freq[word]=freq.get(word,0)+1
    score=lambda s: sum(freq.get(w,0) for w in set(re.findall(r'\w+',s.lower())))/max(len(s.split()),1)**0.5
    ranked=sorted(range(len(sentences)),key=lambda i:score(sentences[i]),reverse=True)[:12]
    points=[sentences[i] for i in sorted(ranked)]
    tasks=[s for s in sentences if re.search(r'bài tập|hạn nộp|nộp bài|kiểm tra|thi cuối|về nhà',s,re.I)][:15]
    return '# Bản nháp trích ý từ lời giảng\n\nĐược chọn tự động từ bản chép lời; chưa đối chiếu slide và có thể sai nhận dạng. Chưa phải bản tóm lược đã được Cún rà soát.\n\n## Các đoạn nổi bật\n\n'+('\n'.join('- '+s for s in points) or 'Chưa nhận dạng được nội dung.')+'\n\n## Đoạn có thể liên quan bài tập / kiểm tra\n\n'+('\n'.join('- '+s for s in tasks) or 'Không tìm thấy; không có nghĩa là không có bài tập.')+'\n\n## Cần rà soát\n\n- Đối chiếu thuật ngữ, công thức, tên riêng và số liệu với slide.\n- Xác nhận hạn nộp và yêu cầu bài tập từ giảng viên.\n'

def model_root():
    from paths import DATA, DESKTOP, V1_ROOT
    # Reuse a model the Windows 1.x app already downloaded instead of fetching ~150 MB again.
    legacy=V1_ROOT/'Cong_cu/models'
    return legacy if DESKTOP and legacy.is_dir() else DATA/'models'

def model_ready():
    return any(model_root().glob('models--Systran--faster-whisper-base/snapshots/*/model.bin'))

MEDIA={'.mp3','.m4a','.wav','.aac','.flac','.ogg','.opus','.wma','.mp4','.mkv','.mov','.webm','.avi'}

def media_files(folder):
    """Recorded class audio first, then audio/video files the user uploaded to this lesson."""
    source=Path(folder)/'01_Tai_lieu_goc'
    found=[p for p in (source/'am_thanh.wav',source/'am_thanh.webm') if p.is_file() and p.stat().st_size>0][:1]
    uploads=source/'tai_lieu'
    if uploads.is_dir():found+=sorted(p for p in uploads.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.lower() in MEDIA)
    return found

def main():
    folder=Path(sys.argv[1]); out=folder/'02_Tom_tat'; status=out/'trang_thai.json'
    def state(value,**kw): status.write_text(json.dumps({'state':value,'time':datetime.now().isoformat(),**kw},ensure_ascii=False,indent=2),encoding='utf-8')
    state('processing')
    try:
        from faster_whisper import WhisperModel
        model=WhisperModel('base',device='cpu',compute_type='int8',download_root=str(model_root()),local_files_only=True,cpu_threads=2,num_workers=1)
        sources=media_files(folder)
        if not sources:raise FileNotFoundError('No audio or video to transcribe.')
        lines=[]
        temp=out/'ban_chep_loi.tmp'
        with temp.open('w',encoding='utf-8') as f:
            for audio in sources:
                if len(sources)>1:f.write(f'## {audio.name}\n')
                segments,info=model.transcribe(str(audio),language='vi',vad_filter=True,beam_size=3)
                for s in segments:
                    line=f'[{int(s.start//60):02d}:{int(s.start%60):02d}] {s.text.strip()}'
                    f.write(line+'\n'); f.flush(); lines.append(s.text.strip())
        temp.replace(out/'ban_chep_loi.txt')
        (out/'tom_tat_nhap.md').write_text(draft('\n'.join(lines)),encoding='utf-8')
        (out/'GUI_CHO_CUN.txt').write_text('Hãy đọc ban_chep_loi.txt và các ảnh slide trong thư mục buổi học này, tổng hợp theo môn: kiến thức chính, giải thích ví dụ, phần cần ôn, bài tập và hạn nộp. Không suy đoán chỗ thiếu.\n'+str(folder),encoding='utf-8')
        state('completed',segments=len(lines))
    except Exception as e:
        state('failed',error=str(e)); traceback.print_exc(); raise

if __name__=='__main__': main()
