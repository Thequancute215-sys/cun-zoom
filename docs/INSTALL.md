# Cài đặt Docker từng bước

Chỉ dùng trên Windows và không cần Docker? Tải `CunZoom.exe` và làm theo [hướng dẫn Windows](WINDOWS.md) — nhanh hơn, không cần tự tải SDK.

## 1. Chuẩn bị máy

- Máy **Intel/AMD x86-64** chạy Linux, hoặc Docker Desktop với Linux containers trên Windows/macOS Intel. Bản này chưa hỗ trợ ARM/Apple Silicon; không khuyến nghị ép chạy QEMU/Rosetta cho Meeting SDK.
- Docker Engine + Compose v2; trên Windows dùng [Docker Desktop chính thức](https://docs.docker.com/desktop/setup/install/windows-install/).
- Khuyến nghị 4 CPU, 8 GB RAM và ít nhất 5 GB trống cho image, mô hình và bản ghi. Đây là cấu hình khuyến nghị, không phải giới hạn hiệu năng đã đo.
- Tài khoản Zoom có quyền tạo General App/Meeting SDK; quyền vào phòng và ghi phải được chủ phòng cho phép.
- Máy phải bật, có mạng và không ngủ trong buổi ghi.

Kiểm tra trong Terminal/PowerShell:

```text
docker version
docker compose version
```

Nếu Docker chưa chạy, mở Docker Desktop và chờ trạng thái Engine running. Có thể giữ bản Windows `CunZoom.exe` song song (cổng 18766, Docker dùng 18767), nhưng không cho cả hai ghi cùng một phòng.

## 2. Tải mã nguồn

```text
git clone https://github.com/Thequancute215-sys/cun-zoom.git
cd cun-zoom
```

Nếu chưa cài Git, vào [Releases](https://github.com/Thequancute215-sys/cun-zoom/releases), tải gói mã nguồn ZIP rồi giải nén. Mở terminal ngay trong thư mục chứa `compose.yaml`.

## 3. Tự tải đúng SDK

Trước khi cấu hình app mới, đọc giới hạn hỗ trợ Zoom ở đầu README. Zoom đang hướng bot/notetaker mới sang RTMS; chỉ dùng module Meeting SDK nếu tài khoản/app của bạn được Zoom cho phép trường hợp này. RTMS không có trong bản hiện tại.

1. Vào [Zoom App Marketplace](https://marketplace.zoom.us/), đăng nhập tài khoản của **chính bạn**.
2. Mở ứng dụng của bạn trong Develop; ứng dụng phải bật Meeting SDK. Nếu tạo mới, xem [hướng dẫn Zoom](https://developers.zoom.us/docs/meeting-sdk/linux/get-started/download/).
3. Chọn **Features → Embed → Meeting SDK → Linux-x86_64**.
4. Tải SDK chính thức. Bản dùng để kiểm tra tích hợp này là **7.1.5.4432**; không dùng Windows SDK/C# SDK hoặc Video SDK để thay thế.
5. Giải nén TAR.XZ. Tạo thư mục `vendor/zoom-linux` trong thư mục dự án, rồi chép **nội dung** SDK vào đó.

Cấu trúc phải là:

```text
cun-zoom/
├── compose.yaml
├── Dockerfile
└── vendor/
    └── zoom-linux/
        ├── h/
        │   └── zoom_sdk.h
        ├── libmeetingsdk.so
        ├── libcml.so
        ├── libmpg123.so
        └── qt_libs/
```

Không lồng thêm một thư mục mang tên gói tải xuống giữa `zoom-linux` và `h`. Giữ đủ các tệp còn lại trong gói SDK, kể cả thư mục bản dịch/tài nguyên nếu có.

Trên Linux có thể giải nén như sau, thay đường dẫn bằng tệp bạn vừa tải:

```bash
mkdir -p vendor/zoom-linux
tar -xJf /duong-dan/zoom-meeting-sdk-linux_x86_64-7.1.5.4432.tar.xz -C vendor/zoom-linux
```

Nếu gói SDK chứa thư mục bao ngoài, di chuyển nội dung thư mục đó lên một cấp. Trên Windows, dùng phần mềm giải nén hỗ trợ TAR.XZ; có thể phải giải nén hai lớp. Không tải SDK từ nguồn không rõ và không đưa thư mục SDK lên public repo.

## 4. Khởi động

Trong thư mục có `compose.yaml`:

```text
docker compose up -d --build
docker compose ps
docker compose logs --tail=80 app
```

Lần đầu tải image nền, thư viện chép lời và biên dịch worker nên chậm hơn các lần sau. SDK chỉ được mount **read-only**, không được chép vào image công khai. Worker được biên dịch trong volume và tái dùng khi SDK/mã không đổi.

Nếu chưa có SDK, giao diện vẫn chạy và báo chưa có bộ ghi. Khi đặt đủ SDK, chạy `docker compose restart app`.

## 5. Đăng nhập giao diện local

```text
docker compose exec app cat /data/access-password.txt
```

Mở **http://127.0.0.1:18767**:

- Username: `cunzoom`.
- Password: chuỗi ngẫu nhiên riêng của lần cài, lấy bằng lệnh trên.

Không dùng Client Secret Zoom làm mật khẩu này. Mật khẩu được giữ qua restart. Chỉ người có quyền đọc volume mới lấy được mật khẩu và khóa mã hóa; bảo vệ tài khoản máy và bản sao lưu.

Nếu đổi cổng host, sửa **cả** `ports` và `PUBLIC_ORIGIN` trong Compose, đồng thời sửa OAuth redirect trong Zoom. Ví dụ cổng 18768 cần `127.0.0.1:18768:18766` và `PUBLIC_ORIGIN=http://127.0.0.1:18768`.

Compose mặc định chỉ mở trên localhost. Không đổi thành `0.0.0.0` để đưa thẳng ứng dụng ra Internet. Triển khai từ xa cần proxy HTTPS và quản lý truy cập phù hợp; không nằm trong hướng dẫn cài local này.

## 6. Thiết lập Zoom, lịch và thử ghi

Theo [ZOOM_AND_CALENDAR.md](ZOOM_AND_CALENDAR.md). Kiểm tra trong một phòng thử được phép trước khi dùng cho lớp thật. Khi host chưa cấp quyền, trạng thái chờ quyền/không có âm thanh là đúng; không được xem là đã ghi thành công.

## Nếu chỉ muốn dùng image có sẵn

Sau khi đặt SDK và tải `compose.yaml` từ bản phát hành:

```text
docker compose pull
docker compose up -d --no-build
```

Nếu registry báo không tìm thấy hoặc từ chối quyền, dùng cách build từ source ở bước 4; không cần chia sẻ token GitHub cá nhân để build source công khai.
