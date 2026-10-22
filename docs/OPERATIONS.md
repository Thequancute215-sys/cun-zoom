# Sử dụng, cập nhật và sao lưu — bản Docker

Bản Windows (`CunZoom.exe`): xem mục sao lưu, cập nhật và xử lý lỗi trong [WINDOWS.md](WINDOWS.md).

## Khởi động / dừng

Chạy trong thư mục có `compose.yaml`:

```text
docker compose up -d
docker compose ps
docker compose logs --tail=100 app
docker compose stop
docker compose start
```

`restart: unless-stopped` cho phép container trở lại khi Docker khởi động. Máy tắt/ngủ hoặc Docker Desktop chưa chạy thì bot không theo dõi/ghi được. Không tự hứa bot có thể dự lớp thay người dùng; OBF và quyền chủ phòng vẫn áp dụng.

Để dừng một buổi ghi, dùng **Dừng và rời phòng** trước khi dừng container. Docker gửi tín hiệu dừng và ứng dụng có khoảng thời gian đóng WAV; cưỡng bức kill/tắt điện có thể làm tệp cuối hỏng hoặc thiếu đoạn cuối.

## Thư mục bài giảng

```text
/data/lessons/
├── 00_Tong_hop/Muc_luc.md
└── Ten_mon/
    ├── 00_Tong_hop_mon/          hệ thống kiến thức, đề cương, đề thi thử (xem STUDY.md)
    └── YYYY-MM-DD_HH-MM-SS_Ten_buoi_maduynhat/
        ├── buoi_hoc.json
        ├── 01_Tai_lieu_goc/
        │   ├── am_thanh.wav
        │   ├── slide_0001.jpg ...
        │   └── tai_lieu/          file tải lên
        ├── 02_Tom_tat/
        │   ├── ban_chep_loi.txt
        │   ├── tom_tat_nhap.md
        │   ├── he_thong_buoi.md   ghi chú AI của buổi
        │   └── trang_thai.json
        └── 03_Bai_tap_va_on_tap/
```

Trong giao diện, chọn một buổi → **Tải buổi học (.zip)**. Chỉ tải dữ liệu thuộc buổi đã chọn; không đưa khóa cấu hình vào ZIP. Một buổi không nhận âm thanh vẫn có thể có thư mục trạng thái lỗi, không được hiểu là đã ghi.

## Chép lời

Trong **Cài đặt → Lưu trữ**, bấm **Tải bộ chép lời** một lần. Mô hình được tải từ Hugging Face bằng kết nối của máy cài, lưu trong volume; lần chép tiếp theo chạy local CPU với mô hình đã có. Không gửi âm thanh lên API chép lời.

Sau buổi có âm thanh, ứng dụng chạy chép lời. Theo dõi `02_Tom_tat/trang_thai.json`; nếu mô hình chưa tải, tải mô hình rồi có thể chạy lại bằng đường dẫn buổi thực tế:

```text
docker compose exec app python /app/src/transcribe.py /data/lessons/Ten_mon/Thu_muc_buoi
```

Không đoán tên thư mục; xem danh sách bằng `docker compose exec app ls /data/lessons`. Đường dẫn có dấu cách phải đặt trong dấu ngoặc kép. Bản trích ý dùng quy tắc chọn câu, chưa tự đối chiếu slide; hãy kiểm tra thuật ngữ, số liệu và hạn nộp.

## Sao lưu toàn bộ

1. Dừng ghi, đợi chép lời xong nếu có.
2. Dừng container để có bản sao nhất quán.
3. Sao lưu **toàn bộ `/data`**, bao gồm `vault.key`, `zoom.vault`, `calendar.vault`, `ai.vault`, `access-password.txt`, mô hình và lessons.

Các lệnh sau dùng trong terminal tại thư mục dự án. Tạo thư mục backup trước (PowerShell: `New-Item -ItemType Directory -Force backup`; Linux: `mkdir -p backup`).

```text
docker compose stop app
docker compose run --rm --no-deps -v ./backup:/backup app tar -czf /backup/cun-zoom-backup.tgz -C /data .
docker compose start app
```

File backup chứa thông tin truy cập cá nhân. Mã hóa/giữ riêng file này; không upload lên Releases/Issues. Trên Linux nếu thư mục host không cho UID 10001 ghi, cấp quyền **riêng thư mục backup** cho UID đó hoặc dùng cách `docker compose cp`; không mở `chmod 777` toàn bộ ổ đĩa.

### Khôi phục sang lần cài mới

Đặt file backup vào `./backup`, bảo đảm không có bản ghi mới cần giữ trong volume đích, dừng app rồi:

```text
docker compose stop app
docker compose run --rm --no-deps -v ./backup:/backup:ro app tar -xzf /backup/cun-zoom-backup.tgz -C /data
docker compose start app
```

Khôi phục ghi đè tệp cùng tên; sao lưu volume đích trước. Khóa sai/mất khóa sẽ không giải mã được cấu hình. Cấu hình của bản Windows (DPAPI) không chuyển thẳng sang Fernet Linux; hãy nhập lại cấu hình trong Docker thay vì chép file `.dpapi`/`.vault` của Windows.

## Cập nhật

Đọc ghi chú release, sao lưu trước, dừng buổi ghi. Với source:

```text
git pull --ff-only
docker compose up -d --build
```

Với image có sẵn, cập nhật phiên bản trong `compose.yaml` theo release đã chọn:

```text
docker compose pull
docker compose up -d --no-build
```

Volume được giữ khi đổi image. **Không dùng `docker compose down -v`** nếu còn cần dữ liệu. SDK không tự cập nhật: tải bản mới từ Zoom, thay thư mục SDK khi bot đã dừng, rồi restart; worker tự biên dịch lại khi SDK thay đổi. Bản SDK mới có thể đổi API; xem kết quả biên dịch trước khi dùng.

## Chẩn đoán nhanh

| Hiện tượng | Kiểm tra / cách xử lý |
| --- | --- |
| Không mở được trang | Docker đang chạy; `docker compose ps`; đúng cổng 18767; không nhầm bản Windows 18766 |
| 401 | Dùng username `cunzoom` và mật khẩu `/data/access-password.txt` của đúng volume |
| Host/Origin không hợp lệ | Địa chỉ truy cập phải khớp `PUBLIC_ORIGIN`; nếu đổi cổng sửa cả Compose và redirect Zoom |
| Chưa có bộ chạy | Kiểm tra `vendor/zoom-linux/h/zoom_sdk.h`, `libmeetingsdk.so`, logs biên dịch; không dùng Windows/Video SDK |
| C++ build thất bại | SDK khác API/kiến trúc; đọc logs, dùng phiên bản đã kiểm tra và tạo issue với lỗi đã che dữ liệu cá nhân |
| SDK auth thất bại | Kiểm tra Client ID/Secret cùng app và cùng môi trường; đồng hồ máy đúng; mạng không chặn Zoom |
| OAuth redirect mismatch | URI phải đúng từng ký tự và đúng cổng, không đổi `127.0.0.1` thành `localhost` một phía |
| OBF bị từ chối | Tài khoản cấp OAuth phải ở trong phòng; kiểm tra scope, app approval và chính sách Zoom |
| Chờ phòng / chờ ghi | Host nhận bot và cấp quyền; không có cách hợp lệ để bot tự vượt bước này |
| 0 B âm thanh | Kiểm tra quyền và thử nói trong phòng; không coi trạng thái vào phòng là ghi thành công |
| 0 slide | Cần có người chia sẻ màn hình; bot không chụp video camera thành slide |
| Thiếu mô hình | Tải mô hình trong Cài đặt, xem log chép lời; không cần cài GPU |
| Không đọc được lịch | Nguồn iCal đúng, mạng HTTPS, chưa đặt lại private URL; chỉ nguồn Google Calendar được chấp nhận |

## Khóa và truy cập

Docker chạy UID 10001, không privileged, không mount Docker socket hoặc thiết bị microphone/camera của máy. Cấu hình dùng Fernet, tệp khóa/ mật khẩu tạo quyền owner-only. Khóa mặc định cùng volume nên không bảo vệ trước người đã có toàn quyền đọc cả volume. Người quản trị có thể mount khóa ngoài bằng `CUN_ZOOM_KEY_FILE` và `CUN_ZOOM_ACCESS_KEY_FILE`; tệp phải tồn tại, UID 10001 đọc được, khóa Fernet hợp lệ và mật khẩu local tối thiểu 24 ký tự. Không đưa bí mật vào Dockerfile/build args hoặc commit `.env`.
