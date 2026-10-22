# Bản Windows (CunZoom.exe)

Ứng dụng desktop Windows x64: cửa sổ WebView2, biểu tượng khay hệ thống, mở link lớp trên máy và lưu bài giảng vào thư mục bạn chọn. Cùng mã nguồn với bản Docker; khác ở cách chạy và cách mã hóa (Windows dùng DPAPI của tài khoản Windows).

Bản này trước đây nằm ở repo `AI-Zoom` (1.0.0 – 1.1.1). Từ 2.1.0, Windows và Docker được phát hành cùng nhau từ repo này.

## Dùng ứng dụng

1. Tải `CunZoom.exe` từ [Releases](https://github.com/Thequancute215-sys/cun-zoom/releases) và mở trên Windows 10/11 x64. Không cần cài Python. Cần [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (thường có sẵn).
2. Trong **Cài đặt → Kết nối**, dán địa chỉ iCal riêng tư của Google Calendar và chọn từ khóa môn học. Có thể bật nhắc trước 30 phút và tự mở link lớp trước 2 phút.
3. Thêm cấu hình ứng dụng Meeting SDK của bạn, kết nối Zoom và bấm **Kiểm tra Zoom**. Xem [cấu hình Zoom và Calendar](ZOOM_AND_CALENDAR.md).
4. Vào lớp, mở **Phòng Zoom**, đánh dấu xác nhận đã vào đúng lớp và được phép ghi, rồi bấm **Bắt đầu bot**. Âm thanh và ảnh slide lưu trong thư mục môn học.
5. Đóng cửa sổ để thu gọn xuống khay hệ thống. Chọn **Thoát Cún Zoom** để dừng cả theo dõi lịch.

Ứng dụng không vượt phòng chờ, quyền host hoặc quy định duyệt ứng dụng của Zoom. Không chạy song song bản Windows và bản Docker cho cùng một phòng.

## Nâng cấp từ 1.x — dữ liệu được giữ nguyên

Chỉ cần thay `CunZoom.exe` cũ bằng bản mới (thoát bản cũ ở khay hệ thống trước). Bản 2.1.0 tự nhận lại dữ liệu cũ trên **cùng máy, cùng tài khoản Windows**:

| Dữ liệu bản 1.x | Bản 2.1.0 làm gì |
| --- | --- |
| Thư mục dữ liệu `D:\HocTap_Zoom\Du_lieu_ung_dung` (nếu máy có ổ D:) hoặc `%LOCALAPPDATA%\CunZoom` | Tiếp tục dùng đúng thư mục đó |
| `quyen_zoom.dpapi`, `calendar.dpapi` | **Sao chép** thành `zoom.vault`, `calendar.vault` ở cùng thư mục. File cũ được giữ, không bị xóa hay sửa |
| Bài giảng trong `D:\HocTap_Zoom\<Môn>` hoặc `Documents\CunZoom` | Thư viện vẫn đọc thư mục cũ; thư mục bạn đã tự chọn trong Cài đặt cũng được giữ |
| Bộ chép lời đã tải ở `D:\HocTap_Zoom\Cong_cu\models` | Dùng lại, không tải lại ~150 MB |

Nếu đã có `zoom.vault`/`calendar.vault`, ứng dụng không ghi đè. DPAPI chỉ giải mã được trên đúng tài khoản Windows đã mã hóa; chuyển sang máy khác thì nhập lại cấu hình. Muốn quay lại bản cũ: mở lại `CunZoom.exe` 1.1.1, các file `.dpapi` vẫn còn nguyên.

## Build và phát hành

CunZoom.exe được build trên GitHub Actions (job `windows` trong [workflow CI](../.github/workflows/docker-release.yml)):

1. Cài bộ phụ thuộc đã khóa `requirements-windows-lock.txt`, chạy toàn bộ tests trên Windows.
2. Tải Windows Meeting SDK `zoom-sdk-csharp-wrapper-7.2.1.49056.zip` từ release `sdk-7.2.1` của repo kho SDK, đối chiếu SHA-256 đã ghim, rồi `scripts/prepare_sdk.py`.
3. `scripts/build_native.py` biên dịch `native/bot.cpp` thành `CunZoomBot.exe`; `scripts/build.py` đóng gói `CunZoom.exe` bằng PyInstaller.
4. Chạy `CunZoom.exe --self-test` (không vào phòng): SDK nạp được, mã hóa, HTTPS và tài nguyên giao diện phải đạt.
5. Mỗi lần chạy giữ exe 14 ngày dưới dạng artifact `CunZoom-windows`. Khi chạy thủ công với `publish_release`, exe được gắn vào cùng Release với image Docker.

Nếu không đọc được SDK, job vẫn chạy tests nhưng bỏ qua bước build exe (phát hành thì báo lỗi).

### Kho SDK (bắt buộc giữ riêng tư)

SDK Zoom có điều khoản riêng, **không** được commit hoặc đăng công khai. Mặc định workflow đọc release `sdk-7.2.1` của repo `Thequancute215-sys/AI-Zoom`. Sau khi đặt repo đó ở chế độ **Private**:

1. Tạo fine-grained token chỉ có quyền *Contents: Read* trên repo kho SDK.
2. Thêm vào repo này: **Settings → Secrets and variables → Actions → New repository secret** tên `WINDOWS_SDK_TOKEN`.
3. (Tuỳ chọn) đổi kho bằng biến `WINDOWS_SDK_REPO` và `WINDOWS_SDK_TAG`. Đổi phiên bản SDK thì cập nhật `SDK_ASSET`/`SDK_SHA256` trong workflow.

### Build trên máy Windows

Cần Python 3.12 và Microsoft C++ Build Tools (thành phần *MSVC x64*).

```text
python -m pip install -r requirements-windows-lock.txt
python -m unittest discover -s tests -v
python scripts/prepare_sdk.py <đường-dẫn>\zoom-sdk-csharp-wrapper-7.2.1.49056.zip
python scripts/build_native.py
python scripts/build.py
```

Kết quả ở `dist/CunZoom.exe` cùng `SHA256SUMS.txt` và `build-info.json`. Chạy giao diện khi phát triển: `python src/main.py`; chạy loopback để thử giao diện trong trình duyệt: `python src/main.py --serve --port 18767 --data-dir .local/preview --no-migrate`.
