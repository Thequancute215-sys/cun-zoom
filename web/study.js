'use strict';
// Study pane and AI settings. Shares $, el, api, busy, toast, go and settingsTab with app.js; all text is set via textContent.
let studyOverview=null,studySubject='',studyDetail=null,studyTab='map',studyExam=null,studyBusy=false,studyFilter={difficulty:'',relevance:'',query:''};
const studyLabels=()=>studyOverview?.labels||{relevance:{},difficulty:{},types:{}};
const lessonState={ready:['Đã hệ thống hoá','success'],stale:['Chờ cập nhật','neutral'],waiting_transcript:['Đang chờ chép lời','neutral'],empty:['Chưa có dữ liệu','neutral']};

function pill(text,kind){return el('span','pill '+(kind||'neutral'),text);}
function levelPill(kind,value){const label=studyLabels()[kind]?.[value];return label?pill(label,'level-'+value):null;}
function section(title,children){const box=el('section','study-section');box.append(el('h3','',title),...children.filter(Boolean));return box;}
function bullets(values){if(!values?.length)return null;const list=el('ul');for(const v of values)list.append(el('li','',v));return list;}
function emptyNote(title,text){const box=el('div','empty-state');box.append(el('strong','',title),el('p','',text));return box;}

async function loadStudy(){if(studyBusy)return;studyBusy=true;try{studyOverview=await api('/study/overview');paintStudy();if(studySubject)await loadSubject(studySubject,false);}catch(e){$('study-status').textContent=e.message;}finally{studyBusy=false;}}

function paintStudy(){const o=studyOverview,engine=o.engine;
  $('study-count').textContent=o.subjects.length+' môn';$('study-nav-count').textContent=o.subjects.length;
  $('study-ai-off').hidden=o.ai.enabled;
  $('study-status').textContent=engine.running?'Đang xử lý: '+engine.current+(engine.queued?' · còn '+engine.queued+' việc':''):engine.message||(o.ai.enabled?'Đã đồng bộ. Tự cập nhật khi có bài giảng hoặc tài liệu mới.':'AI đang tắt.');
  const list=$('study-subjects');list.replaceChildren();
  if(!o.subjects.length)list.append(emptyNote('Chưa có môn học','Ghi một buổi học hoặc tải tài liệu lên để bắt đầu.'));
  for(const s of o.subjects){const b=el('button','lesson-button');b.type='button';b.setAttribute('aria-pressed',String(s.name===studySubject));
    const detail=s.ready+'/'+s.sessions+' buổi đã hệ thống hoá'+(s.waiting?' · '+s.waiting+' chờ chép lời':'')+(s.exams?' · '+s.exams+' đề':'');
    b.append(el('strong','',s.name),el('small','',detail));if(s.error)b.append(el('small','inline-error',s.error));
    b.onclick=()=>loadSubject(s.name,true);list.append(b);}
  const options=$('upload-subjects');options.replaceChildren(...o.subjects.map(s=>{const opt=document.createElement('option');opt.value=s.name;return opt;}));
}

async function loadSubject(name,reset){if(reset){studySubject=name;studyExam=null;}
  studyDetail=await api('/study/subject',{name});if(name!==studySubject)return;
  $('study-placeholder').hidden=true;$('study-view').hidden=false;$('study-subject').textContent=studyDetail.name;
  const s=studyOverview?.subjects.find(x=>x.name===name);
  $('study-meta').textContent=s?s.sessions+' buổi · '+(s.has_map?(s.map_current?'hệ thống kiến thức mới nhất':'hệ thống kiến thức đang chờ cập nhật'):'chưa có hệ thống kiến thức')+(s.error?' · Lỗi: '+s.error:''):'';
  document.querySelectorAll('#study-subjects .lesson-button').forEach(b=>b.setAttribute('aria-pressed',String(b.querySelector('strong').textContent===name)));
  if(reset||studyTab!=='exam'||!studyExam)paintStudyTab();
}

function studySelectTab(name){studyTab=name;document.querySelectorAll('[data-study]').forEach(b=>{const active=b.dataset.study===name;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
  $('study-content').setAttribute('aria-labelledby','study-tab-'+name);paintStudyTab();}

function paintStudyTab(){const box=$('study-content');box.replaceChildren();if(!studyDetail)return;
  ({map:paintMap,lessons:paintLessons,outline:paintOutline,exam:paintExams})[studyTab](box);}

function itemCard(item,extra){const card=el('article','study-item');const head=el('div','study-item-head');head.append(el('strong','',item.ten),levelPill('relevance',item.do_lien_quan),levelPill('difficulty',item.do_kho),pill(studyLabels().types[item.loai]||item.loai));
  card.append(head,el('p','',item.noi_dung));if(extra)card.append(el('small','field-help',extra));return card;}

function paintMap(box){const data=studyDetail.map;
  if(!data){box.append(emptyNote('Chưa có hệ thống kiến thức',studyOverview?.ai.enabled?'Đang chờ hệ thống hoá các buổi học. Bấm Đồng bộ lại nếu cần.':'Bật AI trong Cài đặt để hệ thống hoá.'));return;}
  const bar=el('div','study-filters');const select=(key,labels,first)=>{const s=document.createElement('select');s.setAttribute('aria-label',first);s.append(new Option(first,''),...Object.entries(labels).map(([k,v])=>new Option(v,k)));s.value=studyFilter[key];s.onchange=()=>{studyFilter[key]=s.value;paintStudyTab();};return s;};
  const search=el('input');search.type='search';search.placeholder='Tìm kiến thức…';search.value=studyFilter.query;search.oninput=()=>{studyFilter.query=search.value;const pos=search.selectionStart;paintStudyTab();const again=$('study-content').querySelector('input[type=search]');again.focus();again.setSelectionRange(pos,pos);};
  bar.append(search,select('relevance',studyLabels().relevance,'Mọi mức liên quan'),select('difficulty',studyLabels().difficulty,'Mọi độ khó'));box.append(bar);
  if(data.tong_quan)box.append(el('p','study-lead',data.tong_quan));
  const query=norm(studyFilter.query);let shown=0;
  for(const group of data.nhom||[]){const items=(group.muc||[]).filter(i=>(!studyFilter.difficulty||i.do_kho===studyFilter.difficulty)&&(!studyFilter.relevance||i.do_lien_quan===studyFilter.relevance)&&(!query||norm(i.ten+' '+i.noi_dung).includes(query)));
    if(!items.length)continue;shown+=items.length;const g=el('section','study-group');const head=el('div','study-item-head');head.append(el('h3','',group.ten),levelPill('relevance',group.do_lien_quan),pill(items.length+' mục'));
    g.append(head);if(group.mo_ta)g.append(el('p','field-help',group.mo_ta));for(const i of items)g.append(itemCard(i,i.buoi?.length?'Học ở: '+i.buoi.join('; '):''));box.append(g);}
  if(!shown)box.append(el('p','field-help','Không có mục phù hợp bộ lọc.'));
  if(data.lien_ket?.length)box.append(section('Liên kết giữa các khái niệm',[bullets(data.lien_ket.map(l=>l.tu+' → '+l.den+': '+l.quan_he))]));
  box.append(el('p','field-help','Tạo bởi '+data._meta.ai+' · '+data._meta.created+'. Bản AI tổng hợp; đối chiếu giáo trình trước khi học thuộc.'));
}

function paintLessons(box){if(!studyDetail.lessons.length){box.append(emptyNote('Chưa có buổi học',''));return;}
  for(const lesson of studyDetail.lessons){const card=el('details','study-lesson');const summary=el('summary');const [label,kind]=lessonState[lesson.status]||[lesson.status,'neutral'];
    summary.append(el('strong','',lesson.label),pill(label,kind));card.append(summary);
    const add=el('button','text-button','Thêm tài liệu vào buổi này');add.type='button';add.onclick=()=>openUpload(studyDetail.name,lesson.id);
    if(lesson.materials.length)card.append(el('p','field-help','Tài liệu: '+lesson.materials.join(', ')));
    if(lesson.transcription==='needed')card.append(el('p','field-help','Chờ chép lời. Nếu chưa tải bộ chép lời, vào Cài đặt → Lưu trữ.'));
    if(lesson.transcription==='failed')card.append(el('p','inline-error','Chép lời thất bại; ghi chú dùng slide và tài liệu.'));
    const n=lesson.notes;
    if(n){card.append(el('p','study-lead',n.tom_tat));for(const g of n.nhom||[]){const s=el('section','study-group');s.append(el('h4','',g.ten));for(const i of g.muc||[])s.append(itemCard(i,i.nguon?'Nguồn: '+i.nguon:''));card.append(s);}
      card.append(section('Thuật ngữ',[bullets((n.thuat_ngu||[]).map(t=>t.thuat_ngu+': '+t.giai_thich))]),section('Bài tập và hạn nộp',[bullets(n.bai_tap)]),section('Câu hỏi ôn tập',[bullets(n.cau_hoi_on_tap)]),section('Cần kiểm tra lại',[bullets([...(n.can_kiem_tra||[]),...(n._meta.warnings||[])])]));
      card.querySelectorAll('.study-section').forEach(s=>{if(s.children.length<2)s.remove();});}
    card.append(add);box.append(card);}
}

function paintOutline(box){const data=studyDetail.outline;
  if(!data){box.append(emptyNote('Chưa có đề cương','Đề cương được tạo sau khi có hệ thống kiến thức của môn.'));return;}
  const map=studyDetail.map;if(map&&data._meta.base!==map._meta.fingerprint)box.append(el('div','notice','Đề cương này tạo từ hệ thống kiến thức cũ. Bấm "Tạo lại đề cương" để cập nhật.'));
  box.append(section('Mục tiêu',[bullets(data.muc_tieu)]));
  (data.chuong||[]).forEach((c,index)=>{const s=el('section','study-group');s.append(el('h3','',(index+1)+'. '+c.ten));if(c.tom_tat)s.append(el('p','',c.tom_tat));
    const list=el('ul');for(const p of c.y_chinh||[]){const li=el('li',p.trong_tam?'study-key':'',(p.trong_tam?'★ ':'')+p.noi_dung+' ');const level=levelPill('difficulty',p.do_kho);if(level)li.append(level);list.append(li);}s.append(list);
    if(c.cau_hoi_goi_y?.length)s.append(el('p','field-help','Tự kiểm tra:'),bullets(c.cau_hoi_goi_y));box.append(s);});
  box.append(section('Trọng tâm thi',[bullets(data.trong_tam_thi)]),section('Kế hoạch ôn',[bullets((data.ke_hoach_on||[]).map(s=>s.buoc+': '+s.noi_dung))]));
  box.append(el('p','field-help','Tạo bởi '+data._meta.ai+' · '+data._meta.created+'. Ý có ★ là trọng tâm.'));
}

function paintExams(box){if(studyExam)return paintExam(box);
  const form=el('form','study-exam-form');const field=(label,input)=>{const l=el('label','',label);l.append(input);return l;};
  const mc=el('input');mc.type='number';mc.min='0';mc.max='60';mc.value='20';const essays=el('input');essays.type='number';essays.min='0';essays.max='10';essays.value='3';
  const mix=document.createElement('select');mix.append(new Option('Cân bằng','can_bang'),new Option('Thiên về cơ bản','co_ban'),new Option('Thiên về nâng cao','nang_cao'));
  const make=el('button','button primary','Tạo đề thi thử');make.type='submit';
  form.append(field('Số câu trắc nghiệm',mc),field('Số câu tự luận',essays),field('Độ khó',mix),make);
  form.onsubmit=busy(make,async()=>{await api('/study/run',{kind:'exam',subject:studyDetail.name,multiple_choice:Number(mc.value),essays:Number(essays.value),mix:mix.value});toast('Đang soạn đề. Đề mới sẽ hiện trong danh sách khi xong.');loadStudy();});
  box.append(form);if(!studyDetail.map)box.append(el('p','field-help','Cần có hệ thống kiến thức của môn trước khi tạo đề.'));
  if(!studyDetail.exams.length){box.append(el('p','field-help','Chưa có đề thi thử.'));return;}
  for(const e of studyDetail.exams){const b=el('button','lesson-button');b.type='button';b.append(el('strong','',e.title||'Đề thi thử'),el('small','',e.created.replace('T',' ')+' · '+e.multiple_choice+' trắc nghiệm · '+e.essays+' tự luận'));
    b.onclick=busy(b,async()=>{studyExam={id:e.id,data:await api('/study/exam',{subject:studyDetail.name,id:e.id}),answers:{},submitted:false};paintStudyTab();});box.append(b);}
}

function paintExam(box){const {data}=studyExam;const back=el('button','text-button','← Danh sách đề');back.type='button';back.onclick=()=>{studyExam=null;paintStudyTab();};
  box.append(back,el('h3','',data.tieu_de||'Đề thi thử'),el('p','field-help','Thời gian gợi ý: '+data.thoi_gian_phut+' phút'));
  const questions=data.trac_nghiem||[];let correct=0;
  questions.forEach((q,index)=>{const set=el('fieldset','exam-question');const legend=el('legend','','Câu '+(index+1)+'. '+q.cau+' ');const level=levelPill('difficulty',q.do_kho);if(level)legend.append(level);set.append(legend);
    q.lua_chon.forEach((option,i)=>{const letter='ABCD'[i];const label=el('label','exam-option');const radio=el('input');radio.type='radio';radio.name='q'+index;radio.value=letter;radio.checked=studyExam.answers[index]===letter;radio.disabled=studyExam.submitted;radio.onchange=()=>{studyExam.answers[index]=letter;};
      label.append(radio,el('span','',letter+'. '+option));if(studyExam.submitted){if(letter===q.dap_an)label.classList.add('correct');else if(studyExam.answers[index]===letter)label.classList.add('wrong');}set.append(label);});
    if(studyExam.submitted){if(studyExam.answers[index]===q.dap_an)correct++;set.append(el('p','field-help','Đáp án '+q.dap_an+'. '+q.giai_thich));}box.append(set);});
  if(questions.length){if(studyExam.submitted)box.append(el('p','study-score','Kết quả trắc nghiệm: '+correct+'/'+questions.length+' câu đúng'));
    else{const submit=el('button','button primary','Nộp bài trắc nghiệm');submit.type='button';submit.onclick=()=>{studyExam.submitted=true;paintStudyTab();$('study-content').querySelector('.study-score')?.scrollIntoView({block:'nearest'});};box.append(submit);}}
  (data.tu_luan||[]).forEach((q,index)=>{const card=el('section','exam-question');const title=el('h4','','Tự luận '+(index+1)+' ('+q.diem+' điểm). '+q.cau+' ');const level=levelPill('difficulty',q.do_kho);if(level)title.append(level);
    const hint=el('details');hint.append(el('summary','','Xem gợi ý chấm'),bullets(q.goi_y_cham));card.append(title,el('textarea','exam-answer'),hint);box.append(card);});
}

function openUpload(subject,lesson){const form=$('study-upload');form.hidden=false;$('upload-error').hidden=true;$('upload-progress').textContent='';
  $('upload-subject').value=subject||studySubject||'';fillUploadLessons(lesson||'');$('upload-subject').focus();}

async function fillUploadLessons(selected){const select=$('upload-lesson'),name=$('upload-subject').value.trim();select.replaceChildren(new Option('Buổi mới (chỉ có tài liệu)',''));
  if(name&&studyOverview?.subjects.some(s=>s.name===name)){try{const detail=name===studyDetail?.name?studyDetail:await api('/study/subject',{name});for(const l of detail.lessons)select.append(new Option(l.label,l.id));}catch{}}
  select.value=selected;$('upload-title-row').hidden=!!select.value;}

async function uploadFiles(){const subject=$('upload-subject').value.trim(),files=[...$('upload-files').files];let lesson=$('upload-lesson').value;
  if(!subject)throw Error('Nhập tên môn học.');if(!files.length)throw Error('Chọn ít nhất một file.');
  for(const [index,file] of files.entries()){$('upload-progress').textContent='Đang tải '+(index+1)+'/'+files.length+': '+file.name+' ('+size(file.size)+')';
    const query=new URLSearchParams({subject,name:file.name,title:$('upload-title').value.trim()||file.name.replace(/\.[^.]+$/,'')});if(lesson)query.set('lesson',lesson);
    const r=await fetch('/study/upload?'+query,{method:'POST',headers:{'X-App-Token':token},body:file});const v=await r.json().catch(()=>({}));
    if(!r.ok)throw Error(file.name+': '+(v.error||'Không tải lên được.'));lesson=v.lesson;}
  $('upload-progress').textContent='Đã tải '+files.length+' file. Âm thanh/video sẽ được chép lời, sau đó tự hệ thống hoá nếu AI đang bật.';
  $('upload-files').value='';studySubject=subject;toast('Đã lưu tài liệu vào '+subject+'.');await loadStudy();}

function paintAI(s){$('ai-provider').value=s.provider;$('ai-model').replaceChildren(...Object.entries(s.models).map(([k,v])=>new Option(v,k)));$('ai-model').value=s.claude_model;
  $('ai-ollama-url').value=s.ollama_url;$('ai-ollama-model').value=s.ollama_model;$('ai-auto').checked=s.auto;$('ai-key').value='';
  $('ai-key').placeholder=s.claude_key_saved?'Đã lưu khóa · để trống để giữ':'sk-ant-…';paintAIProvider();
  $('ai-health').textContent=!s.enabled?'Đang tắt':s.provider==='claude'?'Đang dùng Claude · '+(s.models[s.claude_model]||s.claude_model):'Đang dùng Ollama · '+s.ollama_model;}
function paintAIProvider(){const p=$('ai-provider').value;$('ai-claude').hidden=p!=='claude';$('ai-ollama').hidden=p!=='ollama';}
async function loadAI(){try{paintAI(await api('/ai/settings'));}catch(e){$('ai-health').textContent=e.message;}}

$('ai-provider').onchange=paintAIProvider;
$('ai-form').onsubmit=busy($('ai-form').querySelector('[type=submit]'),async()=>{paintAI(await api('/ai/save',{provider:$('ai-provider').value,claude_key:$('ai-key').value.trim(),claude_model:$('ai-model').value,ollama_url:$('ai-ollama-url').value.trim(),ollama_model:$('ai-ollama-model').value.trim(),auto:$('ai-auto').checked}));toast('Đã lưu cấu hình AI.');loadStudy();},'ai-form-error');
$('ai-test').onclick=busy($('ai-test'),async()=>{toast('Đang kiểm tra AI…');await api('/ai/test');toast('AI hoạt động bình thường.');},'ai-form-error');
$('study-ai-enable').onclick=()=>{go('settings');settingsTab('ai');};
$('study-upload-open').onclick=()=>openUpload();
$('upload-cancel').onclick=()=>{$('study-upload').hidden=true;};
$('upload-subject').onchange=()=>fillUploadLessons('');
$('upload-lesson').onchange=()=>{$('upload-title-row').hidden=!!$('upload-lesson').value;};
$('study-upload').onsubmit=busy($('upload-start'),uploadFiles,'upload-error');
$('study-sync').onclick=busy($('study-sync'),async()=>{await api('/study/run',{kind:'sync',subject:studySubject});toast('Đang đồng bộ môn '+studySubject+'.');loadStudy();});
$('study-outline').onclick=busy($('study-outline'),async()=>{await api('/study/run',{kind:'outline',subject:studySubject});toast('Đang tạo lại đề cương.');loadStudy();});
$('study-open').onclick=busy($('study-open'),async()=>openResult(await api('/study/open',{subject:studySubject})));
document.querySelectorAll('[data-study]').forEach(b=>b.onclick=()=>studySelectTab(b.dataset.study));
document.querySelectorAll('[data-settings="ai"]').forEach(b=>b.addEventListener('click',loadAI));
window.addEventListener('hashchange',()=>{if(location.hash==='#study')loadStudy();});
setInterval(()=>{if(view==='study'&&!document.hidden)loadStudy();},8000);
loadAI();loadStudy();
