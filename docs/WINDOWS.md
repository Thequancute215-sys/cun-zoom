# Bản Windows (CunZoom.exe)

Ứng dụng desktop Windows x64: cửa sổ riêng, biểu tượng ở khay hệ thống, tự mở link lớp và lưu bài giảng vào thư mục bạn chọn. Cùng mã nguồn với bản Docker; khác ở cách chạy và cách mã hóa (Windows dùng DPAPI của tài khoản Windows).

`CunZoom.exe` **không kèm Zoom Meeting SDK**. Mỗi người tự tải SDK chính thức từ Zoom bằng tài khoản của mình rồi cài vào ứng dụng bằng một nút bấm (Bước 4). Nhờ vậy, mỗi người tự đồng ý với điều khoản SDK của Zoom và repo này không phân phối phần mềm của Zoom.

Bản này trước đây nằm ở repo `AI-Zoom` (1.0.0 – 1.1.1). Từ 2.1.0, Windows và Docker được phát hành cùng nhau từ repo này.

## Cài đặt từng bước

Làm lần lượt; mất khoảng 20–30 phút lần đầu. Không gửi Client Secret, mật khẩu hay link lịch riêng cho người khác, kể cả người chia sẻ ứng dụng này.

### Bước 0. Chuẩn bị

- Máy **Windows 10 hoặc 11, 64-bit**, còn ít nhất 1 GB trống (SDK khoảng 300 MB, bộ chép lời khoảng 150 MB, cộng bài giảng).
- [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) — thường có sẵn trên Windows 10/11; nếu ứng dụng mở ra cửa sổ trắng thì cài nó.
- Một **tài khoản Zoom của chính bạn**. Bạn sẽ tạo một ứng dụng Zoom (miễn phí) trên tài khoản này để lấy khóa và tải SDK.

### Bước 1. Tải CunZoom.exe

1. Mở [trang Releases](https://github.com/Thequancute215-sys/cun-zoom/releases), chọn bản mới nhất, mục **Assets**, tải `CunZoom.exe` và `SHA256SUMS`.
2. Đặt `CunZoom.exe` vào một thư mục cố định, ví dụ `Documents\CunZoom`. Dữ liệu không nằm cạnh exe, nên sau này thay exe không mất gì.
3. (Nên làm) Kiểm tra file tải về không bị sửa: mở PowerShell trong thư mục đó, chạy `Get-FileHash .\CunZoom.exe -Algorithm SHA256` và so chuỗi kết quả với dòng `CunZoom.exe` trong `SHA256SUMS` (không phân biệt hoa/thường).
4. Mở `CunZoom.exe`. Nếu Windows hiện **"Windows protected your PC"**: exe chưa được ký số. Khi đã tải đúng từ trang Releases và mã SHA-256 khớp, bấm **More info → Run anyway**.

### Bước 2. Tạo ứng dụng Zoom của bạn

Làm theo [mục A trong hướng dẫn Zoom và Calendar](ZOOM_AND_CALENDAR.md#a-chuẩn-bị-ứng-dụng-zoom-của-bạn). Ghi lại **Client ID**, **Client Secret** và **Public client ID** ở chỗ riêng tư.

### Bước 3. Tải Zoom Meeting SDK cho Windows

1. Vào [Zoom App Marketplace](https://marketplace.zoom.us/), đăng nhập, mở ứng dụng vừa tạo ở Bước 2.
2. Trong **Features → Embed → Meeting SDK**, chọn tải SDK, nền tảng **Windows**. Giao diện Zoom có thể đổi tên mục; nếu không thấy, xem [trang Meeting SDK Windows của Zoom](https://developers.zoom.us/docs/meeting-sdk/windows/).
3. Chọn phiên bản **7.2.1.49056**. Gói đã được kiểm tra với ứng dụng là `zoom-sdk-csharp-wrapper-7.2.1.49056.zip`. Ứng dụng nhận gói Meeting SDK Windows nào có thư mục `x64\bin\sdk.dll`; gói không đúng sẽ bị từ chối mà không thay đổi gì.
4. **Giữ nguyên file `.zip`**, không cần giải nén.

Lưu ý:

- Không dùng SDK macOS, Linux, Android/iOS, Web hay **Video SDK** — chỉ Meeting SDK **Windows**.
- Bộ ghi của Cún Zoom được biên dịch cho bản 7.2.1.49056. Nếu Zoom không còn cho tải bản này, có thể thử bản 7.x gần nhất; nếu ở Bước 5 **Kiểm tra Zoom** báo lỗi, báo cho người chia sẻ ứng dụng phiên bản SDK bạn tải được (không gửi khóa) để build lại bộ ghi.
- Chỉ tải SDK từ Zoom. Không nhận file SDK do người khác gửi.

### Bước 4. Cài SDK vào Cún Zoom

1. Mở Cún Zoom → **Cài đặt → Kết nối**, tìm thẻ **Ứng dụng Zoom**, phần **Zoom Meeting SDK**.
2. Bấm **Cài Zoom SDK (.zip)** và chọn file zip ở Bước 3.
3. Đợi vài giây đến khi dòng trạng thái hiện **"Đã cài Zoom SDK trên máy này."**

Ứng dụng chỉ chép phần chạy 64-bit (`x64\bin`) của gói vào thư mục dữ liệu (`...\CunZoom\zoom-sdk`), không chạy bất kỳ file nào trong zip. Nếu báo **"File ZIP không phải Zoom Meeting SDK Windows x64"**, bạn đã chọn nhầm gói; ứng dụng không thay đổi gì. Có thể xóa file zip sau khi cài xong. Cài lại (ví dụ đổi phiên bản) cũng bằng nút này.

### Bước 5. Nhập khóa Zoom và kiểm tra

Làm theo [mục B](ZOOM_AND_CALENDAR.md#b-lưu-cấu-hình-trong-cún-zoom): điền Client ID/Secret/Public client ID → **Lưu có mã hóa** → **Kiểm tra Zoom** → **Kết nối lại tài khoản Zoom**. Bài kiểm tra không vào phòng họp nào.

### Bước 6. Kết nối lịch học Google (tuỳ chọn)

Làm theo [mục D](ZOOM_AND_CALENDAR.md#d-kết-nối-lịch-học-google--chỉ-đọc). Có thể bật nhắc trước 30 phút và tự mở link lớp trước 2 phút.

### Bước 7. Thử ghi trong một phòng thử

Làm theo [mục C](ZOOM_AND_CALENDAR.md#c-thử-ghi-trong-một-phòng-được-phép) với một phòng Zoom do bạn tạo trước khi dùng cho lớp thật.

## Dùng hằng ngày

1. Vào lớp Zoom bằng tài khoản đã kết nối ở Bước 5.
2. Trong Cún Zoom mở **Phòng Zoom**, chọn buổi từ lịch hoặc dán link, đánh dấu xác nhận đã vào đúng lớp và được phép ghi, rồi bấm **Bắt đầu bot**.
3. Chủ phòng nhận bot và cho phép ghi. Âm thanh và ảnh slide được lưu theo môn; sau buổi học, ứng dụng chép lời trên máy (cần tải bộ chép lời một lần trong **Cài đặt → Lưu trữ**).
4. Đóng cửa sổ chỉ thu gọn xuống khay hệ thống. Chọn **Thoát Cún Zoom** để dừng hẳn và dừng theo dõi lịch.

Ứng dụng không vượt phòng chờ, quyền host hoặc quy định duyệt ứng dụng của Zoom. Không chạy song song bản Windows và bản Docker cho cùng một phòng.

Dữ liệu nằm ở hai nơi: thư mục dữ liệu (cấu hình mã hóa, Zoom SDK, bộ chép lời; mặc định `%LOCALAPPDATA%\CunZoom`) và thư mục bài giảng (xem/đổi trong **Cài đặt → Lưu trữ**). Không có gì được gửi lên GitHub.

## Nâng cấp từ 1.x — dữ liệu được giữ nguyên

Thoát bản cũ ở khay hệ thống, thay `CunZoom.exe` bằng bản mới, rồi **cài Zoom SDK một lần** (Bước 3–4) vì bản 1.x có SDK nằm sẵn trong exe còn bản mới thì không. Bản 2.1.0 tự nhận lại dữ liệu cũ trên **cùng máy, cùng tài khoản Windows**:

| Dữ liệu bản 1.x | Bản 2.1.0 làm gì |
| --- | --- |
| Thư mục dữ liệu `D:\HocTap_Zoom\Du_lieu_ung_dung` (nếu máy có ổ D:) hoặc `%LOCALAPPDATA%\CunZoom` | Tiếp tục dùng đúng thư mục đó |
| `quyen_zoom.dpapi`, `calendar.dpapi` | **Sao chép** thành `zoom.vault`, `calendar.vault` ở cùng thư mục. File cũ được giữ, không bị xóa hay sửa |
| Bài giảng trong `D:\HocTap_Zoom\<Môn>` hoặc `Documents\CunZoom` | Thư viện vẫn đọc thư mục cũ; thư mục bạn đã tự chọn trong Cài đặt cũng được giữ |
| Bộ chép lời đã tải ở `D:\HocTap_Zoom\Cong_cu\models` | Dùng lại, không tải lại ~150 MB |
| Zoom SDK nằm trong exe 1.x | Cài lại một lần bằng **Cài Zoom SDK (.zip)** |

Nếu đã có `zoom.vault`/`calendar.vault`, ứng dụng không ghi đè. DPAPI chỉ giải mã được trên đúng tài khoản Windows đã mã hóa; chuyển sang máy khác thì nhập lại cấu hình. Muốn quay lại bản cũ: mở lại `CunZoom.exe` 1.1.1, các file `.dpapi` vẫn còn nguyên.

## Sao lưu và cập nhật

- **Sao lưu:** thoát ứng dụng (khay → **Thoát Cún Zoom**), rồi chép nguyên thư mục dữ liệu và thư mục bài giảng sang ổ khác. Cấu hình `.vault` chỉ mở được bằng đúng tài khoản Windows đó; trên máy mới, bài giảng dùng lại được nhưng cấu hình Zoom/lịch phải nhập lại và cài lại SDK.
- **Cập nhật:** tải exe mới ở Releases, thoát bản đang chạy ở khay, thay file. Dữ liệu và SDK đã cài được giữ nguyên. Đọc ghi chú phát hành xem có cần đổi phiên bản SDK không.
- **Kiểm tra file tải về:** so SHA-256 với `SHA256SUMS` trong cùng Release (Bước 1).

## Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| "Windows protected your PC" (SmartScreen) | exe chưa được ký số. Chỉ tải từ trang Releases của repo này, so SHA-256 khớp `SHA256SUMS`, rồi chọn **More info → Run anyway** |
| Cửa sổ trắng hoặc không mở | Cài [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) rồi mở lại |
| "Cún Zoom đang chạy" | Ứng dụng đã chạy ở khay hệ thống; mở từ biểu tượng khay |
| "Cổng ứng dụng đang được sử dụng" | Cổng 18766 đang bị chiếm, thường do bản cũ chưa thoát; thoát bản cũ ở khay hoặc khởi động lại máy |
| "Chưa có Zoom SDK" / "Chưa có bộ chạy" | Làm Bước 3–4 |
| "File ZIP không phải Zoom Meeting SDK Windows x64" | Chọn nhầm gói (macOS/Linux/Video SDK…). Tải gói Meeting SDK **Windows** ở Bước 3 |
| Kiểm tra Zoom thất bại ngay sau khi cài SDK | Phiên bản SDK khác 7.2.1.49056 có thể không khớp bộ ghi; cài đúng phiên bản, hoặc báo phiên bản bạn có cho người chia sẻ ứng dụng |
| Kiểm tra Zoom thất bại (SDK đúng) | Client ID/Secret phải cùng một app và cùng môi trường; đồng hồ máy đúng; mạng không chặn Zoom |
| Zoom báo `redirect_uri` không khớp | Bản Windows dùng cổng loopback tạm cho mỗi lần kết nối; đối chiếu cấu hình redirect của app với tài liệu Zoom cho ứng dụng desktop PKCE. Nếu tài khoản bắt buộc URI cố định, dùng bản Docker |
| Bot chờ phòng / 0 B âm thanh | Host phải nhận bot và cấp quyền ghi; tài khoản đã kết nối OAuth phải ở trong phòng (OBF) |
| Không thấy bài giảng cũ sau nâng cấp | **Cài đặt → Lưu trữ → Chọn thư mục khác**, chọn thư mục bài giảng cũ |

Xử lý lỗi chung của bot, lịch và chép lời: xem bảng chẩn đoán trong [OPERATIONS.md](OPERATIONS.md#chẩn-đoán-nhanh) (bỏ qua các dòng chỉ dành cho Docker).

## Build và phát hành

CunZoom.exe được build trên GitHub Actions (job `windows` trong [workflow CI](../.github/workflows/docker-release.yml)):

1. Cài bộ phụ thuộc đã khóa `requirements-windows-lock.txt`, chạy toàn bộ tests trên Windows.
2. Tải Windows Meeting SDK `zoom-sdk-csharp-wrapper-7.2.1.49056.zip` từ kho SDK riêng tư, đối chiếu SHA-256 đã ghim, rồi `scripts/prepare_sdk.py`. SDK chỉ dùng để biên dịch và tự kiểm tra trên máy CI.
3. `scripts/build_native.py` biên dịch `native/bot.cpp` thành `CunZoomBot.exe` (nạp `sdk.dll` của người dùng khi chạy); `scripts/build.py` đóng gói `CunZoom.exe` bằng PyInstaller **không kèm SDK**.
4. Chạy `CunZoom.exe --self-test` (không vào phòng) với SDK của CI đặt bên ngoài, đúng như SDK người dùng tự cài: SDK nạp được, mã hóa, HTTPS và tài nguyên giao diện phải đạt; CI dừng nếu exe có chứa SDK.
5. Mỗi lần chạy giữ exe 14 ngày dưới dạng artifact `CunZoom-windows`. Khi chạy thủ công với `publish_release`, exe được gắn vào cùng Release với image Docker.

Nếu không đọc được SDK, job vẫn chạy tests nhưng bỏ qua bước build exe (phát hành thì báo lỗi).

### Kho SDK (giữ riêng tư)

Archive SDK Zoom có điều khoản riêng: **không** commit vào repo công khai này và không đăng kèm Release. Workflow đọc archive từ release `sdk-7.2.1` của repo cũ `Thequancute215-sys/AI-Zoom`, được giữ ở chế độ **Private + Archived** chỉ để làm kho SDK (repo archived vẫn cho đọc release).

Vì kho SDK là private, CI cần một token chỉ đọc:

1. GitHub → **Settings → Developer settings → Fine-grained tokens → Generate new token**. *Repository access*: chỉ chọn `AI-Zoom`; *Permissions*: **Contents: Read-only**; đặt ngày hết hạn.
2. Repo này → **Settings → Secrets and variables → Actions → New repository secret**, tên `WINDOWS_SDK_TOKEN`, dán token.
3. Khi token hết hạn, tạo token mới và cập nhật secret.
4. (Tuỳ chọn) đổi kho bằng biến `WINDOWS_SDK_REPO` và `WINDOWS_SDK_TAG`. Đổi phiên bản SDK thì cập nhật `SDK_ASSET`/`SDK_SHA256` trong workflow, `TESTED_VERSION` trong `src/sdk_setup.py` và Bước 3 ở trên.

### Build trên máy Windows

Cần Python 3.12 và Microsoft C++ Build Tools (thành phần *MSVC x64*).

```text
python -m pip install -r requirements-windows-lock.txt
python -m unittest discover -s tests -v
python scripts/prepare_sdk.py <đường-dẫn>\zoom-sdk-csharp-wrapper-7.2.1.49056.zip
python scripts/build_native.py
python scripts/build.py
```

Kết quả ở `dist/CunZoom.exe` (không kèm SDK) cùng `SHA256SUMS.txt` và `build-info.json`. Khi chạy từ mã nguồn (`python src/main.py`), ứng dụng tự dùng SDK trong `vendor/zoom/bin` do `prepare_sdk.py` tạo; exe đóng gói thì dùng SDK người dùng cài ở Bước 4. Chạy loopback để thử giao diện trong trình duyệt: `python src/main.py --serve --port 18767 --data-dir .local/preview --no-migrate`.
