# Cún Zoom 2.1.0 · Windows + Docker

Gộp bản Windows (repo `AI-Zoom`, 1.0.0 – 1.1.1) vào repo này. Một mã nguồn, một quy trình kiểm tra, một Release gồm `CunZoom.exe` và image Docker.

- **Windows:** `CunZoom.exe` được build lại trên CI từ mã hiện tại (giao diện 1.1 + các sửa lỗi của 2.0.0) và tự kiểm tra trước khi đăng. Đọc [hướng dẫn cài đặt từng bước](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/WINDOWS.md#cài-đặt-từng-bước).
- **Zoom SDK không còn nằm trong exe.** Tải Zoom Meeting SDK Windows 7.2.1.49056 từ Zoom Marketplace và cài một lần trong **Cài đặt → Kết nối → Cài Zoom SDK (.zip)**. Người nâng cấp từ 1.x cũng cần làm bước này.
- **Nâng cấp từ 1.x giữ dữ liệu:** dùng tiếp thư mục dữ liệu và thư mục bài giảng cũ, sao chép (không xóa) `quyen_zoom.dpapi`/`calendar.dpapi` sang tên mới, dùng lại bộ chép lời đã tải.
- Giao diện hiển thị đúng hành vi theo nền tảng: Windows tự mở link lớp và thu gọn xuống khay; Docker chuyển link tới giao diện đang mở.
- Docker không đổi chức năng so với 2.0.0; image `ghcr.io/thequancute215-sys/cun-zoom:2.1.0`.

Chưa kiểm tra OAuth/ghi trong phòng Zoom thật của bản 2.1.0; thử với phòng được phép trước buổi học quan trọng. Xem [phạm vi kiểm thử](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/VALIDATION.md).

---

# Cún Zoom 2.0.0 · Docker Linux

Bản mã nguồn mở MIT, có Docker Linux x86-64 và giao diện tiếng Việt.

Module Meeting SDK cần quyền/phê duyệt phù hợp của Zoom. Tài liệu Zoom hiện hướng bot mới sang RTMS; bản này chưa tích hợp RTMS. Không hứa hỗ trợ mọi tài khoản hoặc tự vào lớp trước người cấp OBF.

- Đọc lịch Google iCal, lọc môn, nhắc lịch, chuẩn bị link phòng.
- Bộ ghi native Linux dùng Zoom Meeting SDK do người cài cung cấp riêng; ghi WAV và ảnh màn hình chia sẻ sau khi Zoom cấp quyền.
- Chép lời local, trích ý dạng nháp, thư viện và tải ZIP từng buổi.
- Đăng nhập local bằng mật khẩu ngẫu nhiên; cấu hình mã hóa, chạy non-root, volume giữ dữ liệu qua cập nhật.
- SDK, Client Secret, token, lịch và bản ghi cá nhân không nằm trong image/source/release.

**Bắt đầu tại [hướng dẫn cài đặt](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/INSTALL.md)**, sau đó làm theo [cấu hình Zoom và Calendar](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/ZOOM_AND_CALENDAR.md).

Image: `ghcr.io/thequancute215-sys/cun-zoom:2.0.0`. Có thể tự build bằng `docker compose up -d --build` từ source công khai.

Đã đạt 20 tests, Docker HTTP smoke/restart và biên dịch + khởi tạo SDK Linux 7.1.5.4432 (`sdk_loaded`, code `0`). Chưa kiểm tra OAuth/ghi trong phòng Zoom thật của bản Docker; cần thử phòng được phép trước khi dùng cho lớp chính thức.

Xem [phạm vi kiểm thử](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/VALIDATION.md). Kiểm tra SDK không thay thế thử nghiệm ghi trong phòng thật được phép. Bot cần OBF và quyền host; đóng tab Docker không tự mở Zoom trên host, link nhắc học xuất hiện khi giao diện đang mở.
