# Phát triển

## Cấu trúc

- `src/server.py`: API Python, kiểm tra Host/Origin/token, Basic Auth của Docker, PKCE và thư viện.
- `src/vault.py`: DPAPI trên desktop Windows; Fernet trên Linux. Không rơi về plaintext khi lỗi.
- `src/calendar_watch.py`: đọc iCal, lọc lịch và chống nhắc lặp.
- `src/runner.py`: sở hữu worker, truyền token qua stdin riêng; không đưa bí mật vào argv.
- `native/linux_bot.cpp`: SDK init/auth/join, raw recording đúng quyền, WAV và JPEG.
- `native/bot.cpp`, `scripts/prepare_sdk.py`, `scripts/build_native.py`, `scripts/build.py`, `src/main.py`: bản desktop Windows (WebView2, khay hệ thống, `CunZoom.exe`); xem [WINDOWS.md](WINDOWS.md).
- `src/ai_backend.py`: AI tuỳ chọn — Claude qua SDK `anthropic` (khóa của người dùng, JSON theo schema, PDF/ảnh, fallback khi bị từ chối, cache) hoặc Ollama qua HTTP local; cấu hình mã hóa trong `ai.vault`.
- `src/documents.py`: đọc file tải lên (PDF qua `pypdf`, DOCX/PPTX bằng XML chuẩn, ảnh, TXT/MD); không thực thi nội dung.
- `src/study.py`: ghi chú từng buổi, hệ thống kiến thức của môn, đề cương, đề thi thử, mục lục tổng; bộ đồng bộ chạy nền theo dấu vân tay nội dung file, một việc AI mỗi lúc, không tự thử lại lỗi với cùng dữ liệu. `web/study.js` là giao diện Ôn tập và cài đặt AI.
- `src/sdk_setup.py`: cài SDK Windows của người dùng từ file ZIP chính thức (chỉ chép `x64/bin`, chặn đường dẫn không an toàn, không chạy nội dung ZIP); `prepare_sdk.py` dùng chung phần giải nén.
- `src/paths.py`: thư mục dữ liệu theo nền tảng; trên Windows tiếp tục dùng vị trí và kho khóa của bản 1.x (chỉ sao chép, không xóa).
- `scripts/build_linux.py`: tạo adapter từ header đã preprocess của SDK được mount, biên dịch mã ứng dụng.
- `scripts/container_entry.py`: Xvfb/PulseAudio riêng trong container; build/cache worker rồi chạy web app.
- `web/`: frontend HTML/CSS/JS, font local; không có framework/CDN bắt buộc.

Ảnh công khai chứa mã worker và compiler; **không** chứa SDK. Khi khởi động với SDK được mount read-only, worker được biên dịch và lưu trong volume. Token SDK, mật khẩu phòng và OBF đi qua pipe stdin riêng, không qua dòng lệnh hoặc log ứng dụng.

## Kiểm tra source

```text
python -m venv .venv
# Kích hoạt .venv theo hệ điều hành của bạn
python -m pip install -r requirements.txt
python scripts/check_source.py
python scripts/workflow_map.py check
python -m unittest discover -s tests -v
node --check web/app.js
```

Kiểm tra Docker:

```text
docker build -t cun-zoom-test .
docker run -d --name cun-zoom-test -p 127.0.0.1:18767:18766 -e PUBLIC_ORIGIN=http://127.0.0.1:18767 cun-zoom-test
python scripts/smoke_container.py cun-zoom-test
docker stop cun-zoom-test
docker rm cun-zoom-test
```

Nếu có SDK riêng, mount `/opt/zoom-sdk:ro` theo Compose. Kiểm tra khởi tạo không vào phòng:

```text
docker compose exec app /data/native/CunZoomBot /opt/zoom-sdk check
```

Lệnh trên cần môi trường runtime do entrypoint chuẩn bị, gồm `LD_LIBRARY_PATH`; dùng hướng dẫn VALIDATION nếu gọi riêng ngoài container. Kiểm tra init không có nghĩa được cấp OAuth/quyền ghi.

## Đóng gói và release

Mọi bản cập nhật phải dùng Understand Anything để rà và cập nhật bản đồ dự án trước khi bàn giao. Đọc [WORKFLOW.md](WORKFLOW.md) để xem quy trình, lệnh refresh và cách mở dashboard; [AGENTS.md](../AGENTS.md) ghi quy tắc cho tác nhân. CI so khớp nội dung nguồn và hai graph, không chỉ kiểm tra thời gian tạo file.

Workflow `CI and release (Windows EXE + Docker)` chạy kiểm tra Python, JS và bản đồ trên Linux; tests trên Windows rồi build và tự kiểm tra `CunZoom.exe` (giữ làm artifact 14 ngày); build image và thử HTTP thật. Với workflow_dispatch, bật `publish_release`, điền `version` (ví dụ `2.1.0`, phải trùng `VERSION` trong `src/paths.py`). Chỉ sau khi cả Windows và Docker đạt mới push image lên GHCR, tạo tag/release, gắn `CunZoom.exe` (không kèm SDK), gói source và SHA256SUMS. Cách cấp SDK Windows cho CI nằm trong [WINDOWS.md](WINDOWS.md#kho-sdk-giữ-riêng-tư).

Gói source lấy từ Git tracked files; SDK/runtime/keys bị loại bằng `.gitignore` và allowlist Docker context. Lần đầu push package, kiểm tra visibility của **package GHCR** là Public; visibility của repo không tự bảo đảm điều đó. Không biến repo lịch sử cá nhân thành public để tránh lộ SDK hoặc cấu hình cũ.

Không commit `vendor/zoom-linux`, `.env`, `*.vault`, `*.dpapi`, `vault.key`, `access-password.txt`, iCal, WAV/JPEG buổi học hay các file build. Khi sửa giao diện, giữ chức năng thực, trạng thái lỗi và khả năng dùng bàn phím; không thêm số liệu demo vào trạng thái người dùng.
