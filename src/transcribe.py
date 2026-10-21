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
    from paths import DATA
    return DATA/'models'

def main():
    folder=Path(sys.argv[1]); out=folder/'02_Tom_tat'; status=out/'trang_thai.json'
    def state(value,**kw): status.write_text(json.dumps({'state':value,'time':datetime.now().isoformat(),**kw},ensure_ascii=False,indent=2),encoding='utf-8')
    state('processing')
    try:
        from faster_whisper import WhisperModel
        model=WhisperModel('base',device='cpu',compute_type='int8',download_root=str(model_root()),local_files_only=True,cpu_threads=2,num_workers=1)
        audio=folder/'01_Tai_lieu_goc'/'am_thanh.wav'
        if not audio.exists():audio=folder/'01_Tai_lieu_goc'/'am_thanh.webm'
        segments,info=model.transcribe(str(audio),language='vi',vad_filter=True,beam_size=3)
        lines=[]
        with (out/'ban_chep_loi.txt').open('w',encoding='utf-8') as f:
            for s in segments:
                line=f'[{int(s.start//60):02d}:{int(s.start%60):02d}] {s.text.strip()}'
                f.write(line+'\n'); f.flush(); lines.append(s.text.strip())
        (out/'tom_tat_nhap.md').write_text(draft('\n'.join(lines)),encoding='utf-8')
        (out/'GUI_CHO_CUN.txt').write_text('Hãy đọc ban_chep_loi.txt và các ảnh slide trong thư mục buổi học này, tổng hợp theo môn: kiến thức chính, giải thích ví dụ, phần cần ôn, bài tập và hạn nộp. Không suy đoán chỗ thiếu.\n'+str(folder),encoding='utf-8')
        state('completed',segments=len(lines))
    except Exception as e:
        state('failed',error=str(e)); traceback.print_exc(); raise

if __name__=='__main__': main()
