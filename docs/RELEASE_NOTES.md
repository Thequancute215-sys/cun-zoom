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
