# Cún Zoom

Trợ lý lưu bài học Zoom trên máy của bạn: theo dõi lịch Google, ghi âm cuộc họp được phép, chụp màn hình chia sẻ và sắp xếp bài giảng theo môn. Giao diện tiếng Việt, có chế độ sáng/tối, tìm kiếm và thư viện bài học.

Một mã nguồn, hai cách chạy:

| Cách chạy | Dành cho | Bắt đầu |
| --- | --- | --- |
| **Windows — `CunZoom.exe`** | Máy Windows 10/11 x64; cửa sổ riêng, khay hệ thống, tự mở link lớp | Tải exe ở [Releases](https://github.com/Thequancute215-sys/cun-zoom/releases), đọc [hướng dẫn Windows](docs/WINDOWS.md) |
| **Docker — Linux x86-64** | Máy chủ/Linux hoặc Docker Desktop; giao diện web có đăng nhập | Làm theo [hướng dẫn cài Docker](docs/INSTALL.md) |

Bản Windows trước đây ở repo `AI-Zoom` (1.x) nay được phát hành từ repo này; nâng cấp giữ nguyên cấu hình và bài giảng cũ trên cùng máy ([chi tiết](docs/WINDOWS.md#nâng-cấp-từ-1x--dữ-liệu-được-giữ-nguyên)). Mỗi người dùng cần tài khoản Zoom và ứng dụng Meeting SDK của **chính mình** ([cách cấu hình](docs/ZOOM_AND_CALENDAR.md)); không có khóa dùng chung. **Không bản nào chứa Zoom SDK**: mỗi người tự tải Zoom Meeting SDK chính thức bằng tài khoản Zoom của mình (Windows: chọn file zip trong ứng dụng; Docker: đặt vào `vendor/zoom-linux`).

**Phạm vi hỗ trợ Zoom:** [trang Meeting SDK Linux](https://developers.zoom.us/docs/meeting-sdk/linux/) hiện hướng bot/notetaker mới sang RTMS; [OBF FAQ](https://developers.zoom.us/docs/meeting-sdk/obf-faq/) vẫn mô tả OBF cho ứng dụng legacy. Module SDK của bản này chỉ dành cho trường hợp Zoom cho phép tài khoản/app của bạn sử dụng. Không coi cài Cún Zoom hoặc có OBF là đã được Zoom chấp thuận. RTMS chưa được triển khai trong bản này.

Tất cả hướng dẫn, giải thích cơ chế, nguồn và skill bảo trì được gom tại [mục lục bàn giao](docs/HANDOVER.md).

## Cài bản Windows

Làm theo **[hướng dẫn cài đặt từng bước cho Windows](docs/WINDOWS.md#cài-đặt-từng-bước)** (khoảng 20–30 phút lần đầu):

1. Tải `CunZoom.exe` ở [Releases](https://github.com/Thequancute215-sys/cun-zoom/releases). Không cần Python hay Docker. Windows có thể cảnh báo SmartScreen vì exe chưa ký số.
2. Tạo ứng dụng Zoom của bạn và tải **Zoom Meeting SDK cho Windows** (bản 7.2.1.49056) từ Zoom Marketplace.
3. Trong Cún Zoom: **Cài đặt → Kết nối → Cài Zoom SDK (.zip)**, chọn file vừa tải.
4. Nhập khóa Zoom, bấm **Kiểm tra Zoom**, kết nối lịch Google và thử ghi trong một phòng thử.

## Cài bản Docker

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

Nếu muốn chạy bản Docker trên Windows, dùng Docker Desktop ở chế độ Linux containers. Docker Desktop/WSL2 có thể cần bật ảo hóa và khởi động lại máy; xem tài liệu Docker chính thức trước khi cài. Không chạy song song hai bản bot ghi cùng một phòng.

## Chức năng hiện có

| Phần | Hoạt động |
| --- | --- |
| Lịch học | Đọc iCal Google Calendar, lọc từ khóa môn, xem 14 ngày tới, nhắc trước 30 phút |
| Link phòng | Nhận link Zoom hoặc ID + mật khẩu; chuẩn bị thư mục theo môn/buổi |
| Ghi bài | Bot Meeting SDK (Windows hoặc Linux), OBF, chỉ ghi khi Zoom cho quyền; microphone và camera tắt |
| Âm thanh | WAV PCM từ dữ liệu thực nhận, không phải file mô phỏng |
| Slide | JPEG từ luồng màn hình chia sẻ, tối đa một ảnh mỗi 30 giây |
| Chép lời | Faster Whisper chạy CPU, mô hình tải một lần; trích ý là bản nháp cần đối chiếu |
| Thư viện | Đọc bản chép/tóm tắt; Windows mở thư mục trên máy, Docker tải ZIP từng buổi từ volume `/data` |

**Giới hạn:** bot không thay thế tài khoản học viên để điểm danh, không tự vượt phòng chờ hoặc quyền ghi. Với cơ chế OBF, người cấp quyền cần có mặt trong cuộc họp. Bản Windows tự mở link lớp khi ứng dụng đang chạy; bản Docker không thể mở Zoom trên máy của bạn khi đóng giao diện: link đến giờ học xuất hiện trong giao diện đang mở để bạn bấm. Theo dõi lịch không đồng nghĩa tự bắt đầu ghi.

## Mã nguồn, kiểm tra và giấy phép

- [Bản đồ workflow theo Understand Anything](docs/WORKFLOW.md): luồng người dùng, từng bước thực hiện và file nguồn; quy tắc cập nhật nằm trong [AGENTS.md](AGENTS.md).
- [Kiến trúc và cách phát triển](docs/DEVELOPMENT.md).
- [Phạm vi kiểm thử của bản phát hành](docs/VALIDATION.md).
- MIT cho mã ứng dụng; xem [thành phần bên thứ ba](THIRD_PARTY_NOTICES.md). Zoom SDK chịu điều khoản riêng.
- Mỗi lần push chạy kiểm tra nguồn, tests trên Linux và Windows, build `CunZoom.exe` và đóng gói Docker. Phát hành bằng cách chạy workflow thủ công với `publish_release`; exe và image chỉ được đăng khi mọi bước đạt.

Mỗi người cài bắt đầu bằng cấu hình trống. Không có email, lịch iCal riêng tư, token Zoom hoặc bản ghi của người phát triển trong repository này.
