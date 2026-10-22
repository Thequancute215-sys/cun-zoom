import bootstrap
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch
import zipfile

import ai_backend as ai
import documents
import paths
import study
from server import Service

CONFIG = {'provider': 'claude', 'claude_key': 'sk-ant-synthetic', 'claude_model': 'claude-opus-5-5', 'ollama_url': 'http://127.0.0.1:1', 'ollama_model': '', 'auto': True}


def item(name, relevance='cot_loi', difficulty='co_ban'):
    return {'ten': name, 'noi_dung': 'Nội dung ' + name, 'loai': 'khai_niem', 'do_lien_quan': relevance, 'do_kho': difficulty, 'nguon': 'chép lời'}


def fake_generate(calls):
    """Deterministic stand-in for the AI that answers each schema with valid synthetic data."""
    def generate(system, parts, schema, effort='medium', config=None):
        calls.append({'schema': schema, 'parts': parts, 'effort': effort})
        if schema is study.SESSION_SCHEMA:
            return {'tieu_de': 'Buổi', 'tom_tat': 'Tóm tắt', 'thuat_ngu': [{'thuat_ngu': 'Cung', 'giai_thich': 'Lượng bán'}],
                    'nhom': [{'ten': 'Cung cầu', 'mo_ta': '', 'muc': [item('Phụ', 'tham_khao', 'nang_cao'), item('Cầu', 'cot_loi', 'trung_binh'), item('Cung', 'cot_loi', 'co_ban')]}],
                    'bai_tap': ['Bài 1 hạn thứ Sáu'], 'cau_hoi_on_tap': ['Cung là gì?'], 'can_kiem_tra': []}
        if schema is study.SUBJECT_SCHEMA:
            return {'tong_quan': 'Môn học', 'lien_ket': [],
                    'nhom': [{'ten': 'Phụ lục', 'mo_ta': '', 'do_lien_quan': 'tham_khao', 'muc': [dict(item('Ví dụ', 'tham_khao'), buoi=['Buổi 1'])]},
                             {'ten': 'Cung cầu', 'mo_ta': '', 'do_lien_quan': 'cot_loi', 'muc': [dict(item('Cung'), buoi=['Buổi 1'])]}]}
        if schema is study.OUTLINE_SCHEMA:
            return {'muc_tieu': ['Hiểu cung cầu'], 'chuong': [{'ten': 'Cung cầu', 'tom_tat': '', 'y_chinh': [{'noi_dung': 'Cung', 'do_kho': 'co_ban', 'trong_tam': True}], 'cau_hoi_goi_y': []}],
                    'trong_tam_thi': ['Cân bằng'], 'ke_hoach_on': [{'buoc': 'Ngày 1', 'noi_dung': 'Đọc'}]}
        if schema is study.EXAM_SCHEMA:
            return {'tieu_de': 'Đề', 'thoi_gian_phut': 45,
                    'trac_nghiem': [{'cau': 'Cung là?', 'lua_chon': ['a', 'b', 'c', 'd'], 'dap_an': 'B', 'giai_thich': 'Vì', 'do_kho': 'co_ban', 'chu_de': 'Cung cầu'},
                                    {'cau': 'Thiếu lựa chọn', 'lua_chon': ['a', 'b'], 'dap_an': 'A', 'giai_thich': '', 'do_kho': 'co_ban', 'chu_de': 'x'}],
                    'tu_luan': [{'cau': 'Phân tích', 'diem': 3, 'do_kho': 'nang_cao', 'chu_de': 'Cung cầu', 'goi_y_cham': ['Ý 1']}]}
        raise AssertionError('unexpected schema')
    return generate


def office(path, parts):
    with zipfile.ZipFile(path, 'w') as bundle:
        for name, xml in parts.items():
            bundle.writestr(name, xml)
    return path


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_office_and_text_files_are_read_without_running_them(self):
        docx = office(self.root / 'a.docx', {'word/document.xml': f'<w:document {W}><w:body><w:p><w:r><w:t>Định nghĩa </w:t></w:r><w:r><w:t>cung</w:t></w:r></w:p><w:p/></w:body></w:document>'})
        self.assertEqual(documents.text_of(docx), 'Định nghĩa cung')
        slide = lambda text: f'<p:sld xmlns:p="x" {A}><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:sld>'
        pptx = office(self.root / 'b.pptx', {'ppt/slides/slide10.xml': slide('Mười'), 'ppt/slides/slide2.xml': slide('Hai'),
                                             'ppt/notesSlides/notesSlide2.xml': f'<n {A}><a:p><a:r><a:t>Ghi chú hai</a:t></a:r></a:p><a:p><a:r><a:t>2</a:t></a:r></a:p></n>'})
        self.assertEqual(documents.text_of(pptx), 'Slide 1: Hai\n  Ghi chú: Ghi chú hai\nSlide 2: Mười')
        (self.root / 'c.txt').write_bytes('Tiếng Việt'.encode('utf-16'))
        self.assertEqual(documents.text_of(self.root / 'c.txt'), 'Tiếng Việt')

    def test_names_types_and_limits(self):
        self.assertEqual(documents.safe_name('../../Bài 1: <cung>.PDF'), 'Bài 1_ _cung_.pdf')
        for name in ('virus.exe', 'macro.docm', 'noext'):
            with self.assertRaises(ValueError):
                documents.safe_name(name)
        image = self.root / 'big.png'
        image.write_bytes(b'0' * (documents.IMAGE_LIMIT + 1))
        parts, warning = documents.parts_for(image, 'claude')
        self.assertEqual(parts, [])
        self.assertIn('5 MB', warning)
        broken = self.root / 'broken.docx'
        broken.write_bytes(b'not a zip')
        self.assertEqual(documents.parts_for(broken, 'claude')[0], [])

    def test_pdf_goes_whole_to_claude_and_as_text_to_ollama(self):
        from pypdf import PdfWriter
        pdf = self.root / 'scan.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with pdf.open('wb') as stream:
            writer.write(stream)
        parts, warning = documents.parts_for(pdf, 'claude')
        self.assertEqual(parts[0]['kind'], 'pdf')
        self.assertIsNone(warning)
        parts, warning = documents.parts_for(pdf, 'ollama')
        self.assertEqual(parts, [])
        self.assertIn('scan', warning)


class StudyPipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        # Resolved like the app's own root, so Windows 8.3 temp paths (RUNNER~1) compare equal.
        self.root = Path(self.directory.name).resolve()
        self.calls = []
        self.patches = [patch.object(study, 'root', lambda: self.root),
                        patch.object(study.ai, 'generate', fake_generate(self.calls)),
                        patch.object(study.ai, 'settings', lambda: dict(CONFIG)),
                        patch.object(study.ai, 'enabled', lambda config=None: True),
                        patch.object(study.transcribe, 'model_ready', lambda: False)]
        for item_patch in self.patches:
            item_patch.start()

    def tearDown(self):
        for item_patch in reversed(self.patches):
            item_patch.stop()
        self.directory.cleanup()

    def lesson(self, subject='Kinh tế vi mô', title='Buổi 1', transcript='[00:00] Cung và cầu'):
        folder = self.root / subject / ('2026-10-0' + str(len(list((self.root / subject).glob('*'))) + 1 if (self.root / subject).exists() else 1) + '_' + title)
        (folder / '02_Tom_tat').mkdir(parents=True)
        (folder / '01_Tai_lieu_goc').mkdir()
        (folder / 'buoi_hoc.json').write_text(json.dumps({'subject': subject, 'title': title, 'requested': folder.name[:10] + 'T08:00:00'}), encoding='utf-8')
        if transcript:
            (folder / '02_Tom_tat/ban_chep_loi.txt').write_text(transcript, encoding='utf-8')
        return folder

    def test_lesson_subject_outline_exam_and_index_stay_in_sync(self):
        folder = self.lesson()
        subject = folder.parent
        self.assertEqual(study.session_status(folder), 'stale')
        notes = study.analyze_session(subject, folder)
        self.assertEqual([i['ten'] for i in notes['nhom'][0]['muc']], ['Cung', 'Cầu', 'Phụ'])
        self.assertEqual(study.session_status(folder), 'ready')
        self.assertTrue((folder / '02_Tom_tat/he_thong_buoi.md').is_file())
        data = study.aggregate_subject(subject)
        self.assertEqual(data['nhom'][0]['ten'], 'Cung cầu')
        self.assertTrue((subject / '00_Tong_hop_mon/he_thong_kien_thuc.md').is_file())
        study.make_outline(subject)
        exam = study.make_exam(subject, multiple_choice=2, essays=1)
        self.assertEqual(len(exam['trac_nghiem']), 1)
        self.assertEqual(study.exam(subject, exam['_meta']['id'])['tieu_de'], 'Đề')
        markdown = (subject / '00_Tong_hop_mon/de_thi_thu' / (exam['_meta']['id'] + '.md')).read_text(encoding='utf-8')
        self.assertIn('Đáp án', markdown)
        index = (self.root / '00_Tong_hop/Muc_luc.md').read_text(encoding='utf-8')
        self.assertIn('Kinh tế vi mô', index)
        self.assertIn('đã hệ thống hoá 1', index)
        # New material makes the lesson, then the subject map and outline, out of date.
        (folder / study.MATERIALS).mkdir(parents=True)
        (folder / study.MATERIALS / 'them.txt').write_text('Độ co giãn', encoding='utf-8')
        self.assertEqual(study.session_status(folder), 'stale')
        detail = study.subject_detail('Kinh tế vi mô')
        self.assertEqual(detail['lessons'][0]['materials'], ['them.txt'])
        self.assertEqual(len(detail['exams']), 1)
        for bad in ('../x', '00_Tong_hop', ''):
            with self.assertRaises(ValueError):
                study.subject_dir(bad)
        with self.assertRaises(ValueError):
            study.exam(subject, '../../secret')

    def test_engine_runs_lesson_then_subject_then_outline_and_does_not_retry_failures(self):
        folder = self.lesson()
        engine = study.Engine()
        for _ in range(4):
            engine.scan()
            engine.run_jobs()
        schemas = [c['schema'] for c in self.calls]
        self.assertEqual(schemas, [study.SESSION_SCHEMA, study.SUBJECT_SCHEMA, study.OUTLINE_SCHEMA])
        overview = study.overview(engine)
        self.assertEqual(overview['subjects'][0]['ready'], 1)
        self.assertTrue(overview['subjects'][0]['outline_current'])
        # A failing job is remembered for these inputs and not repeated on every scan.
        (folder / '02_Tom_tat/ban_chep_loi.txt').write_text('[00:00] Bài mới', encoding='utf-8')
        failing = []
        def broken(*args, **kwargs):
            failing.append(1)
            raise ai.AIError('Hết hạn mức')
        with patch.object(study.ai, 'generate', broken):
            for _ in range(3):
                engine.scan()
                engine.run_jobs()
        self.assertEqual(len(failing), 1)
        self.assertIn('Hết hạn mức', engine.status()['errors']['Kinh tế vi mô'])
        engine.request('subject', 'Kinh tế vi mô')
        self.assertEqual(len(engine.jobs), 1)

    def test_long_input_is_split_and_attachments_ride_with_the_first_part(self):
        folder = self.lesson(transcript='\n'.join('[00:%02d] câu %d' % (i % 60, i) for i in range(400)))
        (folder / '01_Tai_lieu_goc/slide_0001.jpg').write_bytes(b'jpg')
        with patch.object(study.ai, 'input_chars', lambda config=None: 2000):
            study.analyze_session(folder.parent, folder)
        session_calls = [c for c in self.calls if c['schema'] is study.SESSION_SCHEMA]
        self.assertGreater(len(session_calls), 2)
        with_images = [i for i, c in enumerate(session_calls) if any(p['kind'] == 'image' for p in c['parts'])]
        self.assertEqual(with_images, [0])

    def test_audio_waits_for_transcription_only_when_the_model_exists(self):
        folder = self.lesson(transcript='')
        (folder / '01_Tai_lieu_goc/am_thanh.wav').write_bytes(b'RIFF')
        (folder / study.MATERIALS).mkdir(parents=True)
        (folder / study.MATERIALS / 'slide.txt').write_text('Slide', encoding='utf-8')
        self.assertEqual(study.transcription_state(folder), 'needed')
        self.assertEqual(study.session_status(folder), 'stale')
        notes = study.analyze_session(folder.parent, folder)
        self.assertIn('bộ chép lời', ' '.join(notes['_meta']['warnings']))
        started = []
        with patch.object(study.transcribe, 'model_ready', lambda: True), patch.object(study.runner, 'start_transcription', started.append):
            self.assertEqual(study.session_status(folder), 'waiting_transcript')
            # An old recording is only transcribed in the background when automatic sync is on.
            with patch.object(study.ai, 'settings', lambda: dict(CONFIG, auto=False)):
                study.Engine().scan()
            self.assertEqual(started, [])
            study.Engine().scan()
            self.assertEqual(started, [folder])
            # Uploaded audio is transcribed even with sync off.
            started.clear()
            upload = self.lesson(title='Ghi âm tải lên', transcript='')
            (upload / study.MATERIALS).mkdir(parents=True)
            (upload / study.MATERIALS / 'bai.m4a').write_bytes(b'audio')
            with patch.object(study.ai, 'settings', lambda: dict(CONFIG, auto=False)):
                study.Engine().scan()
            self.assertEqual(started, [upload])


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name).resolve()
        self.patch = patch.object(study, 'root', lambda: self.root)
        self.patch.start()
        self.service = Service(port=0)
        threading.Thread(target=self.service.http.serve_forever, daemon=True).start()

    def tearDown(self):
        self.service.http.shutdown()
        self.service.http.server_close()
        self.patch.stop()
        self.directory.cleanup()

    def upload(self, data, **query):
        request = urllib.request.Request(self.service.base + '/study/upload?' + urllib.parse.urlencode(query), data=data, method='POST',
                                         headers={'X-App-Token': self.service.token, 'Content-Type': 'application/octet-stream'})
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    def test_upload_creates_a_lesson_then_adds_to_it(self):
        first = self.upload(b'Noi dung', subject='Toán cao cấp', name='chuong1.txt', title='Chương 1')
        lesson = next((self.root / 'Toán cao cấp').iterdir())
        self.assertEqual((lesson / study.MATERIALS / 'chuong1.txt').read_bytes(), b'Noi dung')
        self.assertEqual(json.loads((lesson / 'buoi_hoc.json').read_text(encoding='utf-8'))['source'], 'upload')
        import library
        with patch.object(library, 'preferences', lambda: {'recordings_root': str(self.root)}):
            second = self.upload(b'Khac', lesson=first['lesson'], name='chuong1.txt')
        self.assertEqual(second['file'], 'chuong1_2.txt')
        self.assertEqual(len(list((self.root / 'Toán cao cấp').iterdir())), 1)
        self.assertEqual(study.subject_detail('Toán cao cấp')['lessons'][0]['materials'], ['chuong1.txt', 'chuong1_2.txt'])

    def test_upload_rejects_bad_type_subject_and_missing_token(self):
        for query in ({'subject': 'Môn', 'name': 'run.exe'}, {'subject': '..', 'name': 'a.txt'}, {'subject': '00_Tong_hop', 'name': 'a.txt'}):
            with self.subTest(query=query), self.assertRaises(urllib.error.HTTPError) as result:
                self.upload(b'x', **query)
            self.assertEqual(result.exception.code, 400)
        request = urllib.request.Request(self.service.base + '/study/upload?subject=M&name=a.txt', data=b'x', method='POST')
        with self.assertRaises(urllib.error.HTTPError) as result:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(result.exception.code, 403)
        self.assertFalse(any(self.root.rglob('*.txt')))

    def test_study_script_is_served(self):
        with urllib.request.urlopen(self.service.base + '/study.js', timeout=5) as response:
            self.assertIn(b'function loadStudy', response.read())


if __name__ == '__main__':
    unittest.main()
