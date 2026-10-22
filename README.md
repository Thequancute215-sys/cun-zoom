# Cún Zoom

Trợ lý lưu bài học Zoom trên máy của bạn: theo dõi lịch Google, ghi âm cuộc họp được phép, chụp màn hình chia sẻ và sắp xếp bài giảng theo môn. Giao diện tiếng Việt, có chế độ sáng/tối, tìm kiếm và thư viện bài học.

**Bản Docker dành cho Linux x86-64. Người cài tự tải Zoom Meeting SDK chính thức và tự cấu hình ứng dụng Zoom.** Không có khóa dùng chung; SDK không nằm trong image hoặc mã nguồn.

**Phạm vi hỗ trợ Zoom:** [trang Meeting SDK Linux](https://developers.zoom.us/docs/meeting-sdk/linux/) hiện hướng bot/notetaker mới sang RTMS; [OBF FAQ](https://developers.zoom.us/docs/meeting-sdk/obf-faq/) vẫn mô tả OBF cho ứng dụng legacy. Module SDK của bản này chỉ dành cho trường hợp Zoom cho phép tài khoản/app của bạn sử dụng. Không coi cài Docker hoặc có OBF là đã được Zoom chấp thuận. RTMS chưa được triển khai trong bản này.

## Cài và dùng

Tất cả hướng dẫn, giải thích cơ chế, nguồn và skill bảo trì được gom tại [mục lục bàn giao](docs/HANDOVER.md).

1. Đọc [hướng dẫn cài đặt từng bước](docs/INSTALL.md): Docker, tải SDK, đặt đúng thư mục, chạy ứng dụng và lấy mật khẩu local.
2. Làm theo [hướng dẫn cấu hình Zoom và Google Calendar](docs/ZOOM_AND_CALENDAR.md).
3. Xem [cách dùng, cập nhật, sao lưu và xử lý lỗi](docs/OPERATIONS.md).

```bash
git clone https://github.com/Thequancute215-sys/cun-zoom.git
cd cun-zoom
mkdir -p vendor/zoom-linux
# Giải nén SDK chính thức vào vendor/zoom-linux theo docs/INSTALL.md.
docker compose up -d --build
docker compose exec app cat /data/access-password.txt
```

Mở **http://127.0.0.1:18767**, tên đăng nhập **cunzoom**, mật khẩu là dòng vừa lấy ở trên. Không đưa mật khẩu lên GitHub/chat. Lần đầu có thể cần vài phút để biên dịch bộ ghi với SDK do bạn cung cấp.

Trên Windows, dùng Docker Desktop ở chế độ Linux containers. Docker Desktop/WSL2 có thể cần bật ảo hóa và khởi động lại máy; xem tài liệu Docker chính thức trước khi cài. Không chạy song song hai bản bot ghi cùng một phòng.

## Chức năng hiện có

| Phần | Hoạt động |
| --- | --- |
| Lịch học | Đọc iCal Google Calendar, lọc từ khóa môn, xem 14 ngày tới, nhắc trước 30 phút |
| Link phòng | Nhận link Zoom hoặc ID + mật khẩu; chuẩn bị thư mục theo môn/buổi |
| Ghi bài | Bot Meeting SDK Linux, OBF, chỉ ghi khi Zoom cho quyền; microphone và camera tắt |
| Âm thanh | WAV PCM từ dữ liệu thực nhận, không phải file mô phỏng |
| Slide | JPEG từ luồng màn hình chia sẻ, tối đa một ảnh mỗi 30 giây |
| Chép lời | Faster Whisper chạy CPU, mô hình tải một lần; trích ý là bản nháp cần đối chiếu |
| Thư viện | Đọc bản chép/tóm tắt, tải ZIP từng buổi; dữ liệu nằm trong volume `/data` |

**Giới hạn:** bot không thay thế tài khoản học viên để điểm danh, không tự vượt phòng chờ hoặc quyền ghi. Với cơ chế OBF, người cấp quyền cần có mặt trong cuộc họp. Docker không thể mở Zoom trên máy chủ của bạn khi đóng giao diện: link đến giờ học xuất hiện trong giao diện đang mở để bạn bấm. Theo dõi lịch không đồng nghĩa tự bắt đầu ghi.

## Mã nguồn, kiểm tra và giấy phép

- [Bản đồ workflow theo Understand Anything](docs/WORKFLOW.md): luồng người dùng, từng bước thực hiện và file nguồn; quy tắc cập nhật nằm trong [AGENTS.md](AGENTS.md).
- [Kiến trúc và cách phát triển](docs/DEVELOPMENT.md).
- [Phạm vi kiểm thử của bản phát hành](docs/VALIDATION.md).
- MIT cho mã ứng dụng; xem [thành phần bên thứ ba](THIRD_PARTY_NOTICES.md). Zoom SDK chịu điều khoản riêng.
- Mỗi lần push chạy kiểm tra nguồn, unit/integration tests và đóng gói Docker. Tag `v*` chạy quy trình phát hành khi các bước kiểm tra đạt.

Mỗi người cài bắt đầu bằng cấu hình trống. Không có email, lịch iCal riêng tư, token Zoom hoặc bản ghi của người phát triển trong repository này.
