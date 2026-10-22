# Kết nối Zoom và Google Calendar

Áp dụng cho cả bản Windows (`CunZoom.exe`) và bản Docker. Chỗ nào khác nhau được ghi rõ **Windows** / **Docker**.

Mỗi người dùng cần tài khoản Zoom và ứng dụng Meeting SDK của **chính mình**. Không chia sẻ Client ID/Secret của bạn cho người khác dùng chung.

## A. Chuẩn bị ứng dụng Zoom của bạn

1. Đăng nhập [Zoom App Marketplace](https://marketplace.zoom.us/), tạo/mở **General App** kiểu user-managed phù hợp với tài khoản của bạn.
2. Trong **Features → Embed**, bật **Meeting SDK** và khai báo đúng trường hợp meeting bot/notetaker. Bản này dùng **OBF (On Behalf Of)**; không dùng ZAK để né yêu cầu OBF.
3. Trong phần OAuth, bật cấu hình public client/PKCE mà Zoom cung cấp. Ghi nhận **Client ID**, **Client Secret**, **Public client ID** của đúng môi trường Development hoặc Production. Nếu giao diện tài khoản không có public client/PKCE, dừng và đối chiếu tài liệu Zoom; không tự điền một mã bất kỳ.
4. Đăng ký redirect URI:
   - **Docker:** chính xác `http://127.0.0.1:18767/oauth/callback` (đổi cổng thì đổi theo, xem INSTALL).
   - **Windows:** mỗi lần kết nối, ứng dụng mở một cổng loopback tạm `http://127.0.0.1:<cổng>/oauth/callback` (giữ nguyên cách của bản 1.x). Cấu hình app phải chấp nhận redirect loopback này; nếu Zoom báo `redirect_uri` không khớp, xem phần xử lý lỗi trong [WINDOWS.md](WINDOWS.md#xử-lý-lỗi-thường-gặp).

   Nếu Zoom yêu cầu HTTPS hoặc chặn loopback với cấu hình của tài khoản bạn, làm theo cấu hình được Zoom hỗ trợ; không bỏ kiểm tra bảo mật.
5. Cấp scope tối thiểu để lấy user OBF token, thường được Zoom ghi là **`user:read:token`** trong API `GET /users/me/token?type=onbehalf&meeting_id=...`. Tên hiển thị/scopes có thể thay đổi theo loại app; kiểm tra [OBF FAQ](https://developers.zoom.us/docs/meeting-sdk/obf-faq/) và [User token API](https://developers.zoom.us/docs/api/users/#tag/users/GET/users/{userId}/token). Không thêm quyền đọc/sửa lịch, hồ sơ hoặc cuộc họp nếu không cần.
6. Hoàn thiện thông tin app mà Zoom yêu cầu và thêm ứng dụng vào tài khoản của bạn để thử. Phòng ngoài tài khoản chủ app có thể cần Zoom phê duyệt **Request to share**; cài Cún Zoom không tự cấp quyền này.

Không đăng Client Secret, OAuth token, SDK JWT hoặc iCal riêng tư lên Issues. Nếu lỡ lộ khóa, thu hồi/đổi khóa tại dịch vụ gốc; xóa khỏi giao diện không thu hồi bản đã bị sao chép.

## B. Lưu cấu hình trong Cún Zoom

1. **Windows:** mở `CunZoom.exe`. **Docker:** mở `http://127.0.0.1:18767`, đăng nhập mật khẩu local.
2. Vào **Cài đặt → Kết nối → Ứng dụng Zoom**.
3. Điền ba trường ID/Secret ở trên. Mật khẩu phòng mặc định là tùy chọn.
4. Bấm **Lưu có mã hóa**. Lần sửa tiếp theo để trống Client Secret để giữ khóa đã lưu.
5. Bấm **Kiểm tra Zoom**. Đây là bài kiểm tra khởi tạo + xác thực SDK, **không** vào cuộc họp và **không** chứng minh đã có quyền ghi.
6. Bấm **Kết nối lại tài khoản Zoom**. **Windows** tự mở trang Zoom trong trình duyệt mặc định; **Docker** hiện liên kết trong giao diện để bạn bấm. Đăng nhập/cấp quyền trên trang Zoom thật. Không nhập mật khẩu Zoom vào Cún Zoom.
7. Quay lại Cún Zoom; kiểm tra trạng thái đã kết nối. Nếu sai redirect, sửa đúng địa chỉ trong Zoom (và trong Compose với Docker), rồi kết nối lại.

## C. Thử ghi trong một phòng được phép

1. Mở Zoom bình thường và tham gia cuộc họp bằng **tài khoản đã cấp OAuth**. Với OBF, tài khoản đó phải ở trong phòng để bot tham gia theo cơ chế Zoom cho phép.
2. Trong Cún Zoom → **Phòng Zoom**, điền tên môn, tên buổi, link/ID. Link có `pwd` có thể chứa mã mã hóa; nhập mật khẩu thật khi cần.
3. Xác nhận đúng phòng và đã được phép ghi. Bấm **Bắt đầu bot**.
4. Nếu có phòng chờ, chủ phòng phải nhận bot. Bot hiện tên `Cun - Tro ly ghi bai`.
5. Host/co-host cấp quyền local recording cho bot khi Zoom yêu cầu. Bot không tự chiếm quyền host.
6. Nói một đoạn và chia sẻ màn hình ít nhất 35 giây trong phòng thử.
7. Kiểm tra **Âm thanh** tăng và **Ảnh slide** xuất hiện; bấm **Dừng và rời phòng**.
8. Vào **Bài giảng**: **Windows** bấm **Mở thư mục trên máy**, **Docker** bấm **Tải buổi học (.zip)**. Nghe WAV và mở JPEG để kiểm tra nội dung thật.

Không có âm thanh thực nhận thì không coi là đã ghi thành công. Bot tắt micro và camera trong phòng, không phát lại âm thanh qua SDK. Với Docker, mic/camera của máy cũng không được mount vào container.

## D. Kết nối lịch học Google — chỉ đọc

1. Đăng nhập Google Calendar bằng tài khoản chứa lịch học của bạn.
2. **Cài đặt → chọn đúng lịch → Tích hợp lịch → Địa chỉ bí mật ở định dạng iCal**.
3. Dán địa chỉ vào **Cún Zoom → Cài đặt → Google Calendar**. Địa chỉ này có quyền đọc lịch; không công khai và không gửi trong chat/Issues.
4. Điền từ khóa thực sự có trong tiêu đề môn. Nhiều từ khóa phân tách bằng `;`, ví dụ `Kinh tế vi mô; Tiếng Anh`.
5. Xác nhận đúng lịch, bật theo dõi và lưu. Bấm đồng bộ rồi đối chiếu ngày giờ.

Ứng dụng đọc nguồn Google iCal qua HTTPS, không sửa sự kiện. Theo dõi 14 ngày tới, bỏ sự kiện cả ngày/đã hủy/không khớp từ khóa/không có một phòng Zoom rõ ràng. Múi giờ hiển thị **Asia/Bangkok (UTC+7)**; không suy đoán giờ còn thiếu.

Với tùy chọn mở link trước 2 phút:

- **Windows:** ứng dụng (kể cả khi đang thu gọn ở khay) mở link lớp bằng Zoom/trình duyệt mặc định, mỗi buổi một lần, và hiện thông báo nhắc trước 30 phút. Máy phải bật và ứng dụng phải đang chạy.
- **Docker:** link phòng được gửi lên giao diện để bạn bấm; không điều khiển trình duyệt của máy khi tab đã đóng. Giữ giao diện mở nếu muốn thấy nhắc tức thời.

Cả hai bản đều **không** tự vào phòng hay tự bật ghi.

## E. Thu hồi kết nối

Thu hồi OAuth tại trang quản lý ứng dụng của Zoom. Nếu muốn vô hiệu nguồn iCal đã lộ, đặt lại địa chỉ bí mật tại Google Calendar và cập nhật nguồn mới trong ứng dụng. **Docker:** khóa dữ liệu là riêng mỗi lần cài; sao lưu đúng cả dữ liệu lẫn khóa trước khi di chuyển máy. **Windows:** cấu hình được mã hóa bằng tài khoản Windows (DPAPI); sang máy khác cần nhập lại cấu hình.
