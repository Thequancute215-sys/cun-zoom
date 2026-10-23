# Tài khoản và bản quyền thương mại

Website tài khoản dùng Cloudflare Workers + D1 và tài nguyên tĩnh trong `web/account.*`. Nó phục vụ đăng nhập, nhận/kích hoạt mã bản quyền, quản lý thiết bị và liên kết tải ứng dụng. Bài giảng, SDK và dữ liệu học không được đưa lên website này; đây không phải dịch vụ chạy nhiều phiên Zoom của nhiều khách trên một server.

## Luồng của khách và người bán

1. Khách nhập email (kể cả Gmail) hoặc SĐT quốc tế, nhận OTP 6 số, xác minh. Đây là OTP qua email/SMS, không phải nút Google OAuth. Bản đầu dùng OTP không mật khẩu; phiên có hạn 7 ngày nên không xin mã mỗi lần mở ứng dụng.
2. Khách chọn một gói đang bán và gửi **đơn** ngay trên trang tài khoản (website hoặc trong ứng dụng), nhận **mã CK** dạng `CZ` + 8 ký tự để ghi vào nội dung chuyển khoản. Người bán đối chiếu sao kê rồi **duyệt** đơn trên trang quản trị `/admin`; duyệt sẽ cấp gói đúng số ngày và số máy của đơn. Người bán vẫn có thể cấp gói trực tiếp (trên `/admin` hoặc bằng CLI). Chưa tích hợp cổng thanh toán hoặc tự nhận biết chuyển khoản.
3. Khách thấy gói **Chờ lấy mã**, bấm lấy key. Key ngẫu nhiên 160 bit, chỉ trả về một lần; server chỉ lưu SHA-256 của key. OTP hoặc đăng ký tài khoản không tự cấp gói miễn phí.
4. Khách lưu key và kích hoạt. Chỉ tài khoản sở hữu email/SĐT được cấp gói mới dùng được; một key chỉ kích hoạt một lần. Thời hạn gói bắt đầu từ thời điểm kích hoạt, không phải lúc người bán cấp gói.
5. Khách đăng nhập trong bản ứng dụng thương mại, chọn **Dùng trên máy này**. Các lần đăng nhập sau dùng bản quyền đã gắn với tài khoản; không tiêu thụ lại key. Khách có thể gỡ thiết bị trên website để chuyển máy.

Email và số điện thoại là hai danh tính riêng ở bản đầu, chưa có luồng liên kết tài khoản. Cấp gói đúng danh tính khách dùng để đăng nhập.

Nếu mất key trước khi kích hoạt (ví dụ mất mạng ngay lúc nhận), người bán chạy `reissue` cho gói đó. Lệnh này xóa digest của key cũ (key cũ không còn dùng được) và ghi audit; khách đăng nhập rồi lấy key mới như lần đầu. Không có chức năng đọc lại key cũ, và tải lại trang cũng không hiển thị lại key. `reissue` từ chối gói đã kích hoạt.

Nếu mất phản hồi lúc kích hoạt, khách nhập lại đúng key đó: cùng chủ sở hữu nhận lại kết quả kích hoạt cũ, hạn dùng không được cộng thêm. Tài khoản khác vẫn nhận lỗi như key không hợp lệ.

## Chi phí và giới hạn mặc định

- Không cần VPS luôn bật. Dùng Workers/D1 và tài nguyên tĩnh; có thể dùng địa chỉ `workers.dev` ban đầu. Hạn mức miễn phí không phải cam kết miễn phí vô hạn: xem [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) và [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) tại thời điểm triển khai.
- Email qua [Resend](https://resend.com/pricing) là mặc định; cần tên miền gửi email đã xác minh để gửi cho khách thật. Domain và lưu lượng vượt hạn mức có thể phát sinh phí.
- SMS qua [Twilio](https://www.twilio.com/en-us/sms/pricing) mặc định **tắt**. Chỉ bật khi đã có sender hợp lệ, cấu hình quốc gia gửi và ngân sách. Phí SMS tùy quốc gia/nhà mạng.
- Mặc định tối đa 100 yêu cầu gửi OTP/ngày cho toàn hệ thống, 5/giờ cho một danh tính và 15/giờ cho một IP; có giới hạn theo phút. Cả lần nhà cung cấp báo lỗi vẫn tính vào ngân sách để tránh thử lại vô hạn. Cửa sổ rate limit là cửa sổ thời gian cố định.
- OTP hết hạn sau 5 phút, tối đa 5 lần nhập; mã mới vô hiệu mã cũ. Mã OTP được HMAC với secret riêng, không lưu bản rõ hoặc trả trong API.
- Phiên web dùng cookie HttpOnly, SameSite=Strict và Secure trên HTTPS; desktop lưu bearer token trong vault DPAPI/Fernet. Không lưu token/OTP/key vào localStorage.
- Kiểm tra bản quyền trên ứng dụng cache tối đa 60 giây, giới hạn bởi hạn gói, và được làm mới ngầm trước khi hết hạn. Giao diện, `/status` và các vòng nền chỉ đọc kết quả đã cache, không chờ mạng. Khi kiểm tra thất bại, lần thử nền tiếp theo sau 15 giây. Chỉ thao tác trả phí người dùng vừa bấm mới chờ server trả lời (tối đa 10 giây).
- Khi chưa đăng nhập, chưa kích hoạt, hết hạn hoặc mất mạng sau khi cache hết hạn, ứng dụng **vẫn mở**. Người dùng vẫn xem lịch đã đồng bộ, đọc, tải/xuất bài giảng và ghi chú, mở thư mục, sửa hoặc xóa cấu hình, ngắt kết nối Zoom, tắt theo dõi lịch, dừng bot và thoát ứng dụng. Chỉ việc bắt đầu xử lý mới phải chờ bản quyền: ghi Zoom và kiểm tra SDK, kết nối Zoom, cấu hình/đồng bộ/bật theo dõi lịch, tải bộ chép lời hoặc SDK, kiểm tra AI, đồng bộ Ôn tập, tạo đề, tải tài liệu lên; cả chép lời và hệ thống hoá AI chạy nền cũng tạm dừng. Danh sách nằm ở `PAID_ROUTES` trong `src/server.py`.
- **Không cắt buổi đang ghi:** bot đã chạy thì ghi tiếp đến khi người dùng dừng hoặc buổi kết thúc, kể cả khi bản quyền hết hạn hoặc mất mạng giữa chừng; bản chép lời của buổi đó vẫn được tạo. Việc AI đã gửi đi có thể hoàn thành; không xóa kết quả/bài giảng đã có.
- Chưa có gói dùng offline (lease có chữ ký): mất mạng lâu hơn thời gian cache thì không bắt đầu được việc trả phí mới. Đây là điểm chủ sản phẩm cần chốt.

## Triển khai website

Từ thư mục `accounts/`, dùng Node 22+ và `npm ci`. `npm test` chạy Worker/D1 thật trong Miniflare với nhà cung cấp email giả lập; không gửi email/SMS và không tính phí.

1. Đăng nhập Cloudflare bằng `npx wrangler login`, tạo DB bằng `npx wrangler d1 create cun-zoom-accounts`.
2. Điền `database_id` trả về vào `accounts/wrangler.jsonc`. Điền `PUBLIC_ORIGIN` là origin HTTPS cuối cùng (không dấu `/` cuối), `EMAIL_FROM` là sender đã xác minh và `DOWNLOAD_URL` là nơi tải bản thương mại của bạn. Liên kết mặc định GitHub chỉ là nơi tải bản cộng đồng; không coi đó là bản thương mại đã đóng gói.
3. Tạo `OTP_SECRET` và `ADMIN_TOKEN` độc lập bằng bộ sinh ngẫu nhiên an toàn, mỗi giá trị ít nhất 32 byte; lưu trong password manager. Nhập qua `npx wrangler secret put OTP_SECRET`, `npx wrangler secret put ADMIN_TOKEN`, `npx wrangler secret put RESEND_API_KEY`. Không đưa secret vào `vars`, tham số dòng lệnh, Git hoặc chat.
4. Chạy `npm run db:remote` để áp dụng migration rồi `npm run deploy`. Giữ worker chạy trước mọi đường dẫn assets; worker chỉ cho phép các tệp giao diện tài khoản, không phục vụ phần web ứng dụng hay file cấu hình.
5. Kiểm tra email thật, đăng nhập, cấp gói thử, nhận key, kích hoạt, gỡ thiết bị và thu hồi trước khi bán. Chưa xác nhận production chỉ bằng test giả lập hoặc deploy dry-run.

Nếu cần SMS: tạo secret `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, đặt `SMS_ENABLED=true` rồi deploy. SID phải dạng `AC` + 32 ký tự hex. Không cần quyền truy cập tài khoản Gmail của khách để gửi OTP email.

Phát triển local: sao chép `.dev.vars.example` thành `.dev.vars`, nhập cấu hình riêng; đặt `PUBLIC_ORIGIN=http://localhost:8787`, chạy `npm run db:local`, rồi `npm run dev`. Không có chế độ OTP cố định hoặc in OTP trong server production. Các test giữ OTP giả lập trong bộ nhớ của harness.

## Trang quản trị bán hàng (`/admin`)

Trang này chạy cùng Worker tài khoản, dùng chung D1, migration, test và workflow deploy, nên các bản cập nhật sau tự mang nó theo. Mở `https://<origin>/admin`.

- **Đăng nhập:** bằng OTP như khách. Chỉ email/SĐT có trong biến `ADMIN_IDENTITIES` (phân tách bằng dấu phẩy) mới vào được; phiên quản trị hết hiệu lực sau 12 giờ dù phiên tài khoản còn hạn. Để trống biến này thì trang quản trị đóng, CLI với `ADMIN_TOKEN` vẫn chạy. Không có mật khẩu chung nào nằm trong trang hay trong repo.
- **Tổng quan:** ô số liệu (đơn chờ duyệt, doanh thu đã duyệt, bản quyền đang dùng, người dùng mới, thiết bị hoạt động 7 ngày) và biểu đồ doanh thu theo ngày, đơn theo trạng thái, người dùng mới, bản quyền theo trạng thái. Có bộ lọc 7/30/90 ngày tính theo giờ Việt Nam, tooltip khi rê chuột, chế độ sáng/tối và bảng số liệu dưới mỗi biểu đồ.
- **Đơn hàng:** lọc theo trạng thái, tìm theo email/SĐT hoặc mã CK. **Duyệt** tạo gói trong cùng một transaction (duyệt hai lần hay hai người cùng bấm vẫn chỉ ra một gói). **Từ chối** kèm lý do để khách thấy. Khách tự hủy được đơn đang chờ; mỗi khách tối đa 3 đơn chờ và 5 lần đặt mỗi giờ.
- **Bản quyền & cấp gói:** cấp gói trực tiếp, tìm/lọc, thu hồi, cấp lại mã đã phát nhưng chưa kích hoạt. Trang không bao giờ thấy mã bản rõ; khách tự đăng nhập để lấy mã.
- **Gói bán:** thêm, sửa, tạm ẩn gói (tên, số ngày, số máy, giá đồng). Mỗi đơn giữ ảnh chụp gói lúc mua, nên sửa gói không đổi đơn cũ.
- **Nhật ký:** 100 thao tác gần nhất, gồm người thao tác (danh tính hoặc `cli`) và chi tiết; không ghi key, OTP hay token.

Khi thêm tính năng bán hàng mới (ví dụ cổng thanh toán), thêm migration `accounts/migrations/000N_*.sql`, endpoint trong `admin()` của `worker.mjs`, giao diện trong `web/admin.*` và test trong `accounts/test/`, rồi làm mới bản đồ workflow.

## Cấp và thu hồi gói

### Cấu hình production và GitHub Actions

`accounts/wrangler.jsonc` là mẫu local, còn placeholder DB và origin localhost. Không dùng mẫu đó để khẳng định production đã sẵn sàng.

`node configure-production.mjs` đọc các biến công khai `ACCOUNTS_PUBLIC_ORIGIN`, `ACCOUNTS_D1_DATABASE_ID`, `ACCOUNTS_EMAIL_FROM`, `ACCOUNTS_DOWNLOAD_URL`, `ACCOUNTS_WORKER_NAME` (mặc định `cun-zoom-accounts`) và `ACCOUNTS_ADMIN_IDENTITIES` (danh sách email/SĐT quản trị), kiểm tra rồi sinh `accounts/.wrangler/production.json`. Cũng có thể truyền các flag `--origin`, `--database`, `--sender`, `--download`, `--name`, `--admins`. Không ghi secret vào file này.

Workflow GitHub **Deploy account portal** chỉ chạy khi được gọi bằng `workflow_dispatch`. Tạo environment `accounts-production`, điền các biến trên và `CLOUDFLARE_ACCOUNT_ID`; thêm secrets `CLOUDFLARE_API_TOKEN`, `OTP_SECRET`, `ADMIN_TOKEN`, `RESEND_API_KEY`. API token Cloudflare cần quyền deploy Worker và áp dụng migration D1 cho đúng tài khoản. Workflow chạy tests, sinh cấu hình, dry-run, migration, deploy, nạp secret qua stdin rồi kiểm tra `/health`. Lần triển khai đầu có thể trả 503 từ lúc code được deploy đến lúc nạp đủ secret. Secret cần giữ ổn định ở các lần deploy tiếp theo.

Chưa chạy workflow này trên GitHub/Cloudflare thật trong phiên bàn giao. Health check không thay thế thử gửi OTP, mua/cấp gói và kích hoạt bằng khách thử. Trước migration trên DB có khách thật, tạo bản sao lưu và rà SQL; rollback Worker không tự rollback dữ liệu D1. Xem toàn bộ việc còn thiếu trong [CHAT_HANDOVER](CHAT_HANDOVER.md).

Trong shell riêng của người vận hành, nạp `ADMIN_TOKEN` bằng password manager hoặc cơ chế secret của máy. CLI đọc biến này, không nhận token qua argv; không nhúng token quản trị vào website hay exe.

```text
cd accounts
node admin.mjs grant --url https://accounts.example.com --identity khach@example.com --days 30 --devices 2
node admin.mjs revoke --url https://accounts.example.com --license ID_TRA_VE_KHI_CAP
node admin.mjs reissue --url https://accounts.example.com --license ID_TRA_VE_KHI_CAP
```

Lệnh `grant` trả ID gói và thông tin gói, không in key. Khách tự lấy key trong phiên đăng nhập của họ. `revoke` vô hiệu cả key chưa dùng và gói đã kích hoạt. `reissue` chỉ dành cho key đã phát nhưng chưa kích hoạt: key cũ mất hiệu lực, khách lấy key mới. Có audit cho cấp, thu hồi và cấp lại; không ghi key/OTP/token.

D1 lưu email/SĐT, gói và tên thiết bị: giới hạn người có quyền truy cập, bật phương án sao lưu/khôi phục phù hợp và có hướng dẫn bảo mật dữ liệu cho khách. Không đưa bản sao DB chứa dữ liệu khách vào repo. Xoay `ADMIN_TOKEN` khi cần; xoay `OTP_SECRET` làm OTP đang chờ không dùng được nhưng không tự thu hồi các phiên đã cấp.

## Kết nối bản cài trên máy

Build Windows trên môi trường Windows/CI theo hướng dẫn sẵn có:

```text
python scripts/build.py --accounts-url https://accounts.example.com
```

Origin được đóng gói trong `accounts-config.json` (chỉ có địa chỉ công khai). Exe thương mại bỏ qua biến môi trường đổi origin. Không chạy build thiếu `--accounts-url` rồi coi đó là bản thương mại: bản không có cấu hình này vẫn hoạt động như bản cộng đồng cũ. Cần build/test riêng gói Windows; test Python trên Linux không xác nhận exe.

Khi chạy source/Docker riêng một khách, truyền `CUN_ZOOM_ACCOUNTS_URL` vào process/container để dùng cùng cơ chế. Biến này chỉ được dùng ngoài exe đóng gói. Basic Auth local của Docker vẫn giữ nguyên như lớp bảo vệ máy chủ; OTP tài khoản không thay thế nó. Không dùng một volume dữ liệu chung làm website cho nhiều khách.

Mã nguồn cộng đồng đã có giấy phép MIT. Kiểm tra bản quyền trong client không thể ngăn tuyệt đối người sửa mã client; server vẫn bảo vệ việc cấp key, đăng nhập và giới hạn thiết bị của bản phân phối chính thức. Bản quyền Cún Zoom không cấp quyền Meeting SDK, OAuth/OBF hoặc quyền ghi của Zoom và không chia sẻ khóa AI/Zoom của người bán.

## Kiểm chứng

- `npm ci && npm test` trong `accounts/`: OTP, phiên, rate limit, quyền quản trị (token CLI, danh tính quản trị, phiên 12 giờ), key hiển thị/kích hoạt một lần kể cả đồng thời, đơn hàng (đặt, giới hạn, hủy, duyệt một lần, từ chối, tìm kiếm), số liệu tổng quan theo ngày Việt Nam, cô lập tài khoản, giới hạn thiết bị, hết hạn, thu hồi, Host/Origin và assets.
- `python -m unittest discover -s tests -v`: giữ tests cũ và kiểm tra vault tài khoản, cache không chặn, chỉ chặn thao tác trả phí khi chưa có quyền, không dừng buổi đang ghi, cấu hình bản thương mại.
- Chạy thử UI bằng trình duyệt trên desktop/mobile và dịch vụ account giả lập. Gửi OTP thật, Cloudflare production và đóng gói exe Windows cần cấu hình/tài khoản riêng; chỉ ghi đạt khi thực sự đã chạy.
