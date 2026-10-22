"""Maintain reviewed Understand Anything artifacts; check works without its Node tools.

refresh requires a freshly reviewed domain analysis and the upstream core validator.
It never pretends that hashing changed source performs a business-flow analysis.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ('.ua/domain-graph.json', '.ua/knowledge-graph.json',
             '.ua/config.json', '.ua/tooling.json', 'docs/WORKFLOW.md')
SNAPSHOT = '.ua/source-snapshot.json'
SKIP_PARTS = {'.git', '.venv', '__pycache__', 'build', 'dist', '.local', 'data'}
TEXT_SUFFIXES = {'.py', '.mjs', '.js', '.html', '.css', '.md', '.json', '.yml', '.yaml', '.txt', '.svg'}

DESCRIPTIONS = {
    'src/access_control.py': 'Kiểm tra Basic Auth trong Docker; tạo và đọc mật khẩu local.',
    'src/calendar_watch.py': 'Đọc iCal, mở rộng lịch lặp, lọc buổi Zoom và chống nhắc trùng.',
    'src/container_main.py': 'Khởi động API trong container và dừng bộ ghi khi thoát.',
    'src/library.py': 'Liệt kê buổi theo môn, giới hạn đường dẫn và tải tài liệu hoặc ZIP.',
    'src/main.py': 'Điểm vào desktop Windows; cửa sổ/tray và chế độ chạy dịch vụ.',
    'src/paths.py': 'Đường dẫn đa nền tảng, phiên bản, thiết lập theo bản cài và nhận lại dữ liệu Windows 1.x.',
    'src/platform_actions.py': 'Chuyển thông báo/link vào giao diện Docker hoặc hành động desktop Windows.',
    'src/sdk_setup.py': 'Cài Zoom SDK Windows của người dùng từ ZIP chính thức: chỉ chép x64/bin, chặn đường dẫn không an toàn.',
    'src/room_link.py': 'Phân tích URL Zoom hoặc ID phòng, kiểm tra dữ liệu đầu vào.',
    'src/runner.py': 'Quản lý worker duy nhất, OBF, pipe riêng, trạng thái, dừng và lỗi.',
    'src/server.py': 'API có xác thực, Host/Origin/token, OAuth PKCE và điều phối chức năng.',
    'src/transcribe.py': 'Chép lời WAV bằng Faster Whisper local và trích ý thành bản nháp.',
    'src/vault.py': 'Lưu bí mật bằng Fernet trên Linux hoặc DPAPI trên Windows.',
    'native/linux_bot.cpp': 'Meeting SDK Linux: init/auth/join, quyền ghi, WAV và ảnh luồng chia sẻ.',
    'native/bot.cpp': 'Worker CunZoomBot.exe của bản Windows, dùng Windows Meeting SDK; không phải bộ ghi Linux.',
    'scripts/container_entry.py': 'Chuẩn bị Xvfb/PulseAudio, build/cache worker từ SDK riêng, chạy API.',
    'scripts/build_linux.py': 'Tạo adapter phù hợp header SDK và biên dịch worker Linux.',
    'scripts/build.py': 'Đóng gói CunZoom.exe với PyInstaller, không kèm Zoom SDK; ghi SHA-256 và thông tin build.',
    'scripts/build_native.py': 'Biên dịch worker Windows bằng công cụ Microsoft.',
    'scripts/prepare_sdk.py': 'Giải nén SDK Windows x64 vào thư mục build cho CI/nhà phát triển, dùng chung bộ giải nén an toàn.',
    'scripts/check_source.py': 'Chặn tệp runtime, khóa, SDK và nguồn lịch riêng tư khi xuất bản.',
    'scripts/smoke_container.py': 'Kiểm tra HTTP thật, xác thực, CSRF và dữ liệu qua lần khởi động lại.',
    'scripts/workflow_map.py': 'Sinh bản đồ file và Mermaid từ graph đã rà; CI phát hiện lệch nguồn.',
    'scripts/validate_workflow_graphs.mjs': 'Gọi validator thực của Understand Anything, từ chối dữ liệu bị loại hoặc sửa ngầm.',
    'web/app.js': 'Điều khiển giao diện lịch, phòng Zoom, cấu hình, thư viện và trạng thái.',
    'web/index.html': 'Bố cục màn hình và các biểu mẫu tiếng Việt.',
    'web/style.css': 'Kiểu dáng, bố cục đáp ứng, chế độ sáng/tối và trạng thái tương tác.',
    'web/tokens.css': 'Thông số màu, chữ và khoảng cách dùng trong giao diện.',
    'web/fonts.css': 'Khai báo font tải tại máy; không phụ thuộc CDN.',
    'web/logo.svg': 'Logo ứng dụng dùng trong giao diện.',
    'tokens.css': 'Bản token thiết kế ở gốc dự án; giao diện nạp web/tokens.css.',
    'design.md': 'Nguyên tắc giao diện, nội dung và trạng thái cần giữ khi chỉnh thiết kế.',
    'Dockerfile': 'Image Linux chạy non-root, chứa mã ứng dụng/compiler, không đóng gói SDK.',
    'compose.yaml': 'Cổng loopback, volume dữ liệu và mount SDK chỉ đọc.',
    '.dockerignore': 'Giới hạn nội dung gửi vào Docker build context.',
    '.gitignore': 'Loại tệp sinh ra, dữ liệu riêng, SDK và dữ liệu tạm Understand Anything.',
    '.github/workflows/docker-release.yml': 'Kiểm tra source/bản đồ/tests trên Linux và Windows, build CunZoom.exe và Docker, smoke test và phát hành theo yêu cầu.',
    'AGENTS.md': 'Quy tắc bắt buộc dùng Understand Anything khi bảo trì dự án.',
    'README.md': 'Cách bắt đầu, chức năng, giới hạn và liên kết tài liệu dự án.',
    'LICENSE': 'Giấy phép MIT cho mã ứng dụng.',
    'THIRD_PARTY_NOTICES.md': 'Ghi nhận và phân biệt giấy phép thành phần bên thứ ba.',
    'docs/DEVELOPMENT.md': 'Kiến trúc, phát triển, kiểm tra và quy trình phát hành.',
    'docs/INSTALL.md': 'Các bước cài Docker/SDK, cấu hình và khởi động ứng dụng.',
    'docs/OPERATIONS.md': 'Cách dùng, sao lưu thủ công, cập nhật và xử lý lỗi.',
    'docs/VALIDATION.md': 'Bằng chứng kiểm thử và phần chưa được xác minh trong phòng Zoom thật.',
    'docs/ZOOM_AND_CALENDAR.md': 'Cấu hình OAuth, điều kiện Zoom và nguồn Google Calendar riêng.',
    'docs/RELEASE_NOTES.md': 'Phạm vi chức năng và giới hạn của các bản phát hành 2.x.',
    'docs/WINDOWS.md': 'Dùng, nâng cấp từ 1.x giữ dữ liệu, và build/phát hành CunZoom.exe cùng kho SDK riêng tư.',
    'requirements-windows-lock.txt': 'Phiên bản khóa chính xác của phụ thuộc để build CunZoom.exe.',
    'vendor/README.md': 'Nơi người cài tự đặt SDK chính thức; không có SDK trong Git.',
    'docs/HANDOVER.md': 'Mục lục bàn giao: cơ chế, nguồn, cài đặt, vận hành, kiểm chứng và skill.',
    'skills/workflow/SKILL.md': 'Skill dùng lại quy tắc Understand Anything khi dựng và bảo trì bản đồ dự án.',
    'skills/workflow/references/cun-zoom.md': 'Áp dụng skill workflow vào repo Cún Zoom và cách cài lại skill.',
    'skills/workflow/agents/openai.yaml': 'Tên hiển thị và lời gọi mẫu của skill workflow trong Codex.',
}
LAYERS = {
    'interface': ('Giao diện', 'Màn hình, thiết kế và tài nguyên frontend.'),
    'service': ('Dịch vụ và cấu hình', 'API, truy cập, lịch, dữ liệu và thiết lập.'),
    'capture': ('Bộ ghi và SDK', 'Quản lý tiến trình, ghi được phép, chép lời và công cụ biên dịch.'),
    'delivery': ('Cài đặt và phát hành', 'Điểm vào, Docker và pipeline xuất bản.'),
    'quality': ('Kiểm tra và bản đồ', 'Kiểm thử, kiểm tra nguồn, graph và quy tắc bảo trì.'),
    'reference': ('Hướng dẫn', 'Tài liệu cài đặt, vận hành, kiểm thử và giấy phép.'),
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def source_files():
    names = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0'))
    result = []
    for name in sorted(names):
        path = PurePosixPath(name)
        if not name or name in ARTIFACTS or name == SNAPSHOT or path.parts[0] == '.ua':
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.parts[0] == 'vendor' and name != 'vendor/README.md':
            continue
        if (ROOT / name).is_file():
            result.append(name)
    return result


def digest(relative):
    raw = (ROOT / relative).read_bytes()
    # Git/checkout line endings vary across Windows/Linux; logical source must not.
    if Path(relative).suffix in TEXT_SUFFIXES or Path(relative).name in {'Dockerfile', 'LICENSE', '.gitignore', '.dockerignore'}:
        raw = raw.replace(b'\r\n', b'\n')
    return hashlib.sha256(raw).hexdigest()


def write_json(relative, value):
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))


def validate(graph, domain=False):
    nodes = graph['nodes']
    by_id = {node['id']: node for node in nodes}
    public_source = set(source_files())
    assert len(by_id) == len(nodes), 'Duplicate graph node IDs'
    for node in nodes:
        assert node['name'] and node['summary'] and node['tags'], 'Missing node description'
        if 'filePath' in node:
            value = node['filePath']
            path = PurePosixPath(value)
            assert not path.is_absolute() and '..' not in path.parts and '\\' not in value and ':' not in value, value
            assert value in public_source, 'Graph points outside public source: ' + value
            lines = (ROOT / value).read_text(encoding='utf-8-sig').splitlines()
            start, end = node.get('lineRange', [1, len(lines)])
            assert 1 <= start <= end <= len(lines), 'Invalid source line range: ' + value
    for edge in graph['edges']:
        assert edge['source'] in by_id and edge['target'] in by_id, 'Dangling edge'
        assert edge['source'] != edge['target'], 'Self edge'
        assert 0 <= edge['weight'] <= 1 and edge['direction'] in {'forward', 'backward', 'bidirectional'}
    if domain:
        for node in nodes:
            if node['type'] in {'flow', 'step'}:
                relation = 'contains_flow' if node['type'] == 'flow' else 'flow_step'
                parents = [e for e in graph['edges'] if e['type'] == relation and e['target'] == node['id']]
                assert len(parents) == 1, 'Missing/duplicate parent: ' + node['id']
                parent_type = 'domain' if node['type'] == 'flow' else 'flow'
                assert by_id[parents[0]['source']]['type'] == parent_type
        for node in nodes:
            if node['type'] == 'flow':
                steps = [e for e in graph['edges'] if e['type'] == 'flow_step' and e['source'] == node['id']]
                assert steps and len({e['weight'] for e in steps}) == len(steps), 'Ambiguous step order'
    else:
        layered = [node for layer in graph['layers'] for node in layer['nodeIds']]
        assert len(layered) == len(set(layered)) and set(layered) == set(by_id), 'Every overview file needs one layer'


def layer_for(name):
    if name.startswith(('web/', 'tokens', 'design')):
        return 'interface'
    if name.startswith(('native/', 'scripts/build', 'scripts/prepare_sdk')) or name in {'src/runner.py', 'src/transcribe.py'}:
        return 'capture'
    if name.startswith(('tests/', 'skills/workflow/')) or name == 'AGENTS.md' or name.startswith(('scripts/check', 'scripts/smoke', 'scripts/workflow', 'scripts/validate')):
        return 'quality'
    if name.startswith('src/') and name not in {'src/main.py', 'src/container_main.py'}:
        return 'service'
    if name in {'Dockerfile', 'compose.yaml', '.dockerignore', '.gitignore', 'src/main.py', 'src/container_main.py', 'scripts/container_entry.py'} or name.startswith(('.github/', 'requirements')):
        return 'delivery'
    return 'reference'


def overview(project):
    names = [n for n in source_files() if Path(n).suffix in TEXT_SUFFIXES or n in {'Dockerfile', 'LICENSE', '.gitignore', '.dockerignore'}]
    nodes, edges = [], []
    for name in names:
        layer = layer_for(name)
        node_type = 'document' if name.endswith(('.md', '.txt')) or name == 'LICENSE' else 'file'
        if name.startswith('.github/'):
            node_type = 'pipeline'
        elif name.endswith(('.yaml', '.yml')) or name in {'.gitignore', '.dockerignore', 'Dockerfile'}:
            node_type = 'config'
        description = DESCRIPTIONS.get(name)
        if not description:
            description = ('Kiểm thử ' + Path(name).stem.removeprefix('test_') + '.') if name.startswith('tests/') else ('Khai báo phụ thuộc hoặc giấy phép: ' + name + '.')
        nodes.append({'id': 'file:' + name, 'type': node_type, 'name': name,
                      'summary': description, 'tags': [layer], 'complexity': 'complex' if name in {'src/server.py', 'src/runner.py', 'native/linux_bot.cpp'} else 'moderate',
                      'filePath': name, 'lineRange': [1, max(1, len((ROOT / name).read_text(encoding='utf-8-sig').splitlines()))]})

    def connect(source, target, kind, description):
        if source in names and target in names and source != target:
            item = {'source': 'file:' + source, 'target': 'file:' + target, 'type': kind, 'direction': 'forward', 'description': description, 'weight': 0.8}
            if item not in edges:
                edges.append(item)

    # Import relationships are extracted from Python source, not inferred from names.
    modules = {Path(n).stem: n for n in names if n.startswith('src/') and n.endswith('.py')}
    for name in names:
        if name.endswith('.py'):
            tree = ast.parse((ROOT / name).read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                imported = [n.name for n in node.names] if isinstance(node, ast.Import) else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                for module in imported:
                    if module.split('.')[0] in modules:
                        connect(name, modules[module.split('.')[0]], 'imports', 'Import được đọc từ AST Python.')

    for source, target, kind, description in [
        ('web/index.html', 'web/app.js', 'depends_on', 'Nạp script giao diện.'),
        ('web/index.html', 'web/style.css', 'depends_on', 'Nạp kiểu dáng màn hình.'),
        ('web/index.html', 'web/tokens.css', 'depends_on', 'Nạp token thiết kế.'),
        ('web/index.html', 'web/fonts.css', 'depends_on', 'Nạp font local.'),
        ('web/app.js', 'src/server.py', 'calls', 'Gọi API và nhận trạng thái/sự kiện trình duyệt.'),
        ('src/server.py', 'web/index.html', 'serves', 'Phục vụ frontend có xác thực.'),
        ('src/runner.py', 'native/linux_bot.cpp', 'triggers', 'Chạy worker Linux bằng pipe stdin riêng.'),
        ('src/runner.py', 'native/bot.cpp', 'triggers', 'Chạy CunZoomBot.exe trên Windows, tách khỏi Linux.'),
        ('.github/workflows/docker-release.yml', 'scripts/build.py', 'deploys', 'Build và tự kiểm tra CunZoom.exe trước khi phát hành.'),
        ('.github/workflows/docker-release.yml', 'requirements-windows-lock.txt', 'depends_on', 'Cài phụ thuộc Windows đã khóa.'),
        ('scripts/build_native.py', 'native/bot.cpp', 'depends_on', 'Biên dịch worker Windows với SDK đã chuẩn bị.'),
        ('scripts/build.py', 'src/main.py', 'depends_on', 'Điểm vào được đóng gói thành CunZoom.exe.'),
        ('scripts/prepare_sdk.py', 'src/sdk_setup.py', 'depends_on', 'Dùng chung bộ giải nén SDK an toàn.'),
        ('compose.yaml', 'Dockerfile', 'configures', 'Build image hoặc chạy bản image được chọn.'),
        ('Dockerfile', 'scripts/container_entry.py', 'triggers', 'ENTRYPOINT chuẩn bị runtime.'),
        ('scripts/container_entry.py', 'scripts/build_linux.py', 'triggers', 'Build/cache worker nếu có SDK hợp lệ.'),
        ('scripts/container_entry.py', 'src/container_main.py', 'triggers', 'Chạy dịch vụ web container.'),
        ('scripts/build_linux.py', 'native/linux_bot.cpp', 'depends_on', 'Biên dịch với SDK tự cung cấp.'),
        ('.github/workflows/docker-release.yml', 'Dockerfile', 'deploys', 'Build rồi smoke test trước khi phát hành theo yêu cầu.'),
        ('.github/workflows/docker-release.yml', 'scripts/workflow_map.py', 'validates', 'Không chấp nhận bản đồ lệch source.'),
        ('.github/workflows/docker-release.yml', 'scripts/check_source.py', 'validates', 'Chặn dữ liệu riêng và SDK khỏi source.'),
        ('.github/workflows/docker-release.yml', 'scripts/smoke_container.py', 'triggers', 'Kiểm tra container bằng HTTP thật.'),
        ('AGENTS.md', 'scripts/workflow_map.py', 'documents', 'Yêu cầu quy trình Understand Anything cho mỗi thay đổi.'),
        ('scripts/workflow_map.py', 'scripts/validate_workflow_graphs.mjs', 'triggers', 'Refresh bắt buộc gọi validator upstream.'),
    ]:
        connect(source, target, kind, description)
    layers = [{'id': key, 'name': label, 'description': detail, 'nodeIds': [n['id'] for n in nodes if key in n['tags']]} for key, (label, detail) in LAYERS.items()]
    tour = [{'order': i, 'title': layer['name'], 'description': layer['description'], 'nodeIds': layer['nodeIds']} for i, layer in enumerate(layers, 1)]
    return {'version': '1.0.0', 'kind': 'codebase', 'project': {**project, 'description': 'Bản đồ cấp file và import Python được trích từ AST; không phải graph toàn bộ hàm. ' + project['description']}, 'nodes': nodes, 'edges': edges, 'layers': layers, 'tour': tour}


def workflow_markdown(graph):
    nodes = {n['id']: n for n in graph['nodes']}
    domains = [n for n in nodes.values() if n['type'] == 'domain']
    lines = ['# Bản đồ workflow Cún Zoom', '',
             'Đọc từ trên xuống: cài ứng dụng → kết nối → theo dõi lịch → ghi buổi được phép → đọc bài giảng. Bản đồ này dùng graph của **Understand Anything**; mỗi bước bên dưới có đường dẫn tới mã thực hiện.', '',
             '```mermaid', 'flowchart LR',
             '  setup["1 · Cài đặt và mở ứng dụng"] --> auth["2 · Cấu hình và cấp quyền Zoom"]',
             '  auth --> calendar["3 · Đọc lịch và nhắc học"]',
             '  calendar --> room["Người dùng mở link / vào lớp"]',
             '  room --> consent{"Được phép ghi và đủ quyền Zoom?"}',
             '  consent -- Có --> capture["4 · Bắt đầu ghi · WAV + ảnh slide"]',
             '  consent -- Chưa --> wait["Báo trạng thái · chờ quyền / sửa cấu hình"]',
             '  capture --> stop["Dừng / xử lý ngắt kết nối"]',
             '  stop --> library["5 · Chép lời · đọc bản nháp · tải ZIP"]',
             '  update["Bảo trì mã nguồn"] --> map["Understand Anything · rà lại workflow"]',
             '  map --> ci["Kiểm tra bản đồ + tests + Docker smoke"]',
             '  ci --> release["Phát hành khi có yêu cầu"]', '```', '',
             '**Điểm cần nhớ:** bản Windows tự mở link lớp, bản Docker chỉ đưa link tới giao diện; cả hai đều không tự vào phòng hoặc tự ghi. Ghi cần OAuth/OBF, người cấp quyền có mặt và host cho phép. Bản Linux đã kiểm tra build/SDK init; OAuth và ghi phòng thật chưa được xác minh. RTMS chưa có.', '',
             '## Các luồng và bước thực hiện', '']
    for domain in domains:
        lines += ['### ' + domain['name'], '', domain['summary'], '']
        flows = [nodes[e['target']] for e in graph['edges'] if e['type'] == 'contains_flow' and e['source'] == domain['id']]
        for flow in flows:
            ordered = sorted((e for e in graph['edges'] if e['type'] == 'flow_step' and e['source'] == flow['id']), key=lambda e: e['weight'])
            steps = [nodes[e['target']] for e in ordered]
            lines += ['<details>', '<summary>' + flow['name'] + '</summary>', '', flow['summary'], '',
                      '**Bắt đầu:** ' + flow.get('domainMeta', {}).get('entryPoint', 'Thao tác người dùng'), '',
                      '```mermaid', 'flowchart LR']
            for i, step in enumerate(steps, 1):
                label = step['name'].replace('"', "'").replace('\n', ' ')
                lines.append(f'  s{i}["{i} · {label}"]')
                if i > 1:
                    lines.append(f'  s{i-1} --> s{i}')
            lines += ['```', '', '| Bước | Thực hiện | Mã nguồn |', '| --- | --- | --- |']
            for i, step in enumerate(steps, 1):
                filename = step.get('filePath')
                link = f'[{filename}](../{filename}#L{step.get("lineRange", [1])[0]})' if filename else 'Thao tác thủ công'
                lines.append(f'| {i}. {step["name"]} | {step["summary"].replace("|", "/")} | {link} |')
            lines += ['', '</details>', '']
    lines += ['## Mở bản đồ tương tác', '',
              '- Dữ liệu luồng: [domain-graph.json](../.ua/domain-graph.json).',
              '- Kiến trúc cấp file, quan hệ import Python và các điểm nối đã rà: [knowledge-graph.json](../.ua/knowledge-graph.json). Chưa phân tích toàn bộ hàm/call graph.',
              '- Công cụ: [fork Understand Anything được chỉ định](https://github.com/Thequancute215-sys/understand-anything), phiên bản/commit trong [tooling.json](../.ua/tooling.json).', '',
              'Cài ba skill `understand`, `understand-domain`, `understand-dashboard` từ repo đó theo hướng dẫn của nó. Gọi `understand-dashboard` với đường dẫn bản clone Cún Zoom. Dùng URL đầy đủ có `?token=` mà dashboard in ra; token chỉ dùng local, không commit.', '',
              'Trong dashboard: chọn **Domain**, bấm một miền rồi chọn luồng trong bảng chi tiết, bấm một bước để đọc giải thích; chọn **Structural** để xem các file liên quan.', '',
              '## Cập nhật bắt buộc sau mỗi thay đổi', '',
              '1. Đọc [AGENTS.md](../AGENTS.md), graph hiện tại và nguồn bị ảnh hưởng.',
              '2. Dùng skill `understand-domain --full` trong checkout của fork được ghim. Chạy script `extract-domain-context.py` theo skill, giao domain-analyzer rà dữ liệu với mã thật. Lưu phân tích mới ở `.ua/intermediate/domain-analysis.json`. Không lấy graph cũ rồi chỉ đổi ngày.',
              '3. Build core của công cụ một lần (`pnpm install --frozen-lockfile --ignore-scripts`, rồi `pnpm --filter @understand-anything/core build` từ gốc plugin). Python và Node phải có trên PATH. Chạy:', '',
              '```text', 'python scripts/workflow_map.py refresh --plugin-root <duong-dan>/understand-anything-plugin --domain-graph .ua/intermediate/domain-analysis.json --review-note "Mo ta luong da doi va nguon da doi chieu"',
              'python scripts/workflow_map.py check', '```', '',
              '4. Mở dashboard, kiểm tra luồng vừa thay đổi và ít nhất một bước. Commit nguồn, hai graph, trang này và snapshot cùng lần bàn giao. Trước khi commit phải xóa dữ liệu trung gian theo skill; không lưu link token của viewer vào Git.',
              '5. CI chạy `check` trước tests/build; nguồn, graph hoặc tài liệu sinh ra bị lệch snapshot sẽ bị từ chối. Kiểm tra này phát hiện thay đổi nội dung, không thay thế việc phân tích ý nghĩa của thay đổi.', '',
              '`.ua/config.json` đặt `autoUpdate: true` cho công cụ hỗ trợ tính năng này. Trong Codex, việc duy trì được ràng buộc bằng AGENTS và CI; không có tiến trình AI tự chạy nền chỉ nhờ cấu hình đó.', '',
              '## Phạm vi dữ liệu và kiểm chứng', '',
              'Graph chỉ chứa source công khai và quy trình đã thấy trong mã/hướng dẫn. SDK, dữ liệu học, iCal, token và cấu hình cá nhân không thuộc bản đồ. [VALIDATION.md](VALIDATION.md) là nguồn về kết quả kiểm thử; không coi một bước trên sơ đồ là bằng chứng thao tác đã thành công.', '',
              'Ngày phân tích và commit nền nằm trong metadata của hai graph. [source-snapshot.json](../.ua/source-snapshot.json) đối chiếu chính xác nội dung nguồn đã rà, kể cả khi commit chứa thêm artifact.']
    return '\n'.join(lines) + '\n'


def check():
    snapshot = load(SNAPSHOT)
    current = {n: digest(n) for n in source_files()}
    expected = snapshot['sourceFiles']
    changed = sorted(n for n in current.keys() | expected.keys() if current.get(n) != expected.get(n))
    changed += [n for n in ARTIFACTS if not (ROOT / n).is_file() or digest(n) != snapshot['artifacts'].get(n)]
    assert not changed, 'Workflow map is stale; review with Understand Anything and refresh: ' + ', '.join(changed)
    validate(load('.ua/domain-graph.json'), domain=True)
    validate(load('.ua/knowledge-graph.json'))
    print(f'Workflow map OK: {len(current)} source files; reviewed domain + file graphs match snapshot.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check')
    refresh = commands.add_parser('refresh')
    refresh.add_argument('--plugin-root', type=Path, required=True)
    refresh.add_argument('--domain-graph', type=Path, required=True)
    refresh.add_argument('--review-note', required=True)
    args = parser.parse_args()
    if args.command == 'check':
        check()
        return
    tooling = load('.ua/tooling.json')
    plugin = args.plugin_root.resolve()
    plugin_commit = subprocess.check_output(['git', '-C', str(plugin), 'rev-parse', 'HEAD']).decode().strip()
    assert plugin_commit == tooling['commit'], 'Use the pinned Understand Anything checkout or explicitly review a tooling upgrade.'
    graph = json.loads(args.domain_graph.read_text(encoding='utf-8-sig'))
    # v2.9.7 draws the badge as round(weight * 10). Keep ordering AND 1..N labels.
    for flow in (n for n in graph['nodes'] if n['type'] == 'flow'):
        steps = sorted((e for e in graph['edges'] if e['type'] == 'flow_step' and e['source'] == flow['id']), key=lambda e: e['weight'])
        assert len(steps) <= 10, 'Split a long flow before using the v2.9.7 step badges.'
        for index, edge in enumerate(steps, 1):
            edge['weight'] = round(index / 10, 1)
    graph['project']['analyzedAt'] = datetime.now(timezone.utc).isoformat()
    graph['project']['gitCommitHash'] = git('rev-parse', 'HEAD')
    validate(graph, domain=True)
    write_json('.ua/domain-graph.json', graph)
    write_json('.ua/knowledge-graph.json', overview(graph['project']))
    subprocess.run(['node', str(ROOT / 'scripts/validate_workflow_graphs.mjs'), str(plugin),
                    str(ROOT / '.ua/domain-graph.json'), str(ROOT / '.ua/knowledge-graph.json')], check=True)
    (ROOT / 'docs/WORKFLOW.md').write_text(workflow_markdown(graph), encoding='utf-8')
    write_json(SNAPSHOT, {'version': 1, 'reviewedAt': graph['project']['analyzedAt'],
                         'sourceBaseCommit': graph['project']['gitCommitHash'], 'reviewNote': args.review_note,
                         'sourceFiles': {n: digest(n) for n in source_files()},
                         'artifacts': {n: digest(n) for n in ARTIFACTS}})
    check()


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
