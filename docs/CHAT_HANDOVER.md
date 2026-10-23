# Bàn giao cuộc chat — tài khoản, OTP, key bản quyền và production Cún Zoom

> Tài liệu dành để bàn giao trực tiếp cho lập trình viên/Claude Code. Phân biệt mã đã viết, kiểm thử cục bộ, đề xuất và việc chưa hoàn thành. **Chưa triển khai production thật, chưa phát hành ứng dụng thương mại.**
>
> Repository: `Thequancute215-sys/cun-zoom`. Nền phiên làm việc: `53decc9d4b95fc032f132c375f05960eb5e824a2` (v2.2.0). Các thay đổi trong phiên này đang ở working tree khi lập tài liệu; không coi chúng đã có trên `main`. Thời điểm bàn giao: tháng 10/2026.

## 1. Yêu cầu của chủ sản phẩm

- Bán Cún Zoom cho khách; đăng nhập bằng Gmail/email hoặc số điện thoại, xác minh OTP.
- Key là **mã bản quyền Cún Zoom do chủ sản phẩm phát hành**, không phải API key AI hay Zoom SDK key.
- Hỗ trợ ứng dụng cài trên máy và website. Website phiên bản đầu dùng để đăng ký/đăng nhập, kích hoạt bản quyền, quản lý thiết bị và tải ứng dụng.
- Tối ưu chi phí; key chỉ dùng một lần. Chủ sản phẩm muốn có cấu hình production, hướng dẫn rõ để Claude Code tiếp tục và cập nhật workflow GitHub theo tiến độ.
- Cần bàn giao đầy đủ cả công việc làm dở và lý do lựa chọn giải pháp.

**Điểm chưa chốt:** câu yêu cầu ban đầu có “OTP để lấy mật khẩu mặc định”. Mã hiện tại chọn đăng nhập không mật khẩu qua OTP, không sinh mật khẩu mặc định và chưa tích hợp Google OAuth. Đây là lựa chọn triển khai cần chủ sản phẩm xác nhận, không được ghi thành yêu cầu đã duyệt. “Gmail” hiện nghĩa là địa chỉ email nhận OTP, không phải nút “Đăng nhập với Google”.

## 2. Cách tiếp cận và lý do

### Tách dịch vụ tài khoản khỏi ứng dụng local

Ứng dụng gốc xử lý Zoom, ghi âm, bài học và AI trên máy khách. Đưa HTTP server local lên Internet không tự biến nó thành SaaS an toàn nhiều khách. Vì vậy backend tài khoản được tách riêng; website chỉ phục vụ tài khoản/quyền/thiết bị/tải ứng dụng. Dữ liệu học vẫn ở máy khách; chưa có workspace dùng chung, lưu trữ transcript cloud hay đồng bộ nhiều máy.

### Workers + D1, email trước, SMS sau

Cloudflare Workers phục vụ API và portal; D1 lưu tài khoản, phiên, quyền và thiết bị. Hướng này tránh vận hành VPS thường trực ở giai đoạn thử bán. Resend gửi OTP email; SMS qua Twilio đã có adapter nhưng tắt mặc định vì SMS tính phí theo lượt và dễ bị lạm dụng. Không cam kết chi phí bằng 0: phải kiểm tra hạn mức/giá hiện hành của từng nhà cung cấp và đặt cảnh báo ngân sách. Có giới hạn OTP theo IP, danh tính và tổng ngày.

### Xác minh danh tính không đồng nghĩa đã mua hàng

Ai xác minh email/số điện thoại cũng có thể tạo tài khoản. Chỉ chủ sản phẩm gọi thao tác quản trị `grant` mới cấp gói cho đúng danh tính. OTP không tự tạo quyền sử dụng. Chưa có tích hợp thanh toán: cấp gói hiện là thao tác thủ công sau khi chủ sản phẩm xác nhận giao dịch.

### Hai nghĩa khác nhau của “key một lần”

1. **Hiển thị một lần:** khách đã xác thực yêu cầu lấy key của gói được cấp. Backend sinh ngẫu nhiên, trả bản rõ đúng một lần, chỉ giữ digest trong DB. Lệnh cấp gói của admin không in key.
2. **Kích hoạt một lần:** khách dùng key để gắn gói vào tài khoản; cập nhật có điều kiện trong DB ngăn hai yêu cầu đồng thời cùng nhận quyền.

Lý do: không giữ kho key bản rõ, không để ai biết email là lấy được quyền, và giảm rủi ro key chia sẻ cho nhiều tài khoản. Đây vẫn là quyền phần mềm do máy khách thực thi, không bảo đảm chống crack tuyệt đối. Repository có nền MIT; cần giữ nghĩa vụ giấy phép và bán rõ giá trị dịch vụ/hỗ trợ thay vì hứa khóa local không thể bị sửa.

**Đánh đổi chưa giải quyết:** mất phản hồi mạng ngay sau khi key được tạo thì khách không thể lấy lại bản rõ. Kích hoạt lại cùng key hiện trả 409, chưa có phục hồi retry idempotent như tài liệu Word đề xuất. Cần thiết kế quy trình cấp lại có audit hoặc trả lại kết quả kích hoạt cho cùng chủ sở hữu; không nên mở hiển thị key nhiều lần để chữa tạm.

### Kiểm tra quyền ngắn và bảo vệ token

Máy khách lưu token phiên trong vault DPAPI/Fernet, ràng buộc với backend origin; không đưa token vào localStorage của portal. Website dùng cookie HttpOnly/SameSite Strict. Máy khách kiểm tra quyền online và cache tối đa 60 giây để thu hồi/giới hạn thiết bị có tác dụng sớm. **Chưa làm signed offline lease**; lựa chọn này làm ứng dụng phụ thuộc mạng và hiện có thể dừng bot đang chạy. Cần sửa/chốt chính sách trước khi bán.

## 3. Những việc đã viết trong mã

| Phần | File chính | Trạng thái thực tế |
| --- | --- | --- |
| Backend OTP, phiên, gói, key, thiết bị | `accounts/worker.mjs` | Đã viết và test cục bộ bằng Worker/D1 giả lập nhà cung cấp email |
| Schema D1 và ràng buộc tranh chấp | `accounts/migrations/0001_accounts.sql` | Đã chạy trong test; chưa migrate DB production |
| CLI cấp/thu hồi gói | `accounts/admin.mjs` | Đã viết; admin token qua môi trường, không phải giao diện quản trị |
| Cấu hình dev | `accounts/wrangler.jsonc`, `.dev.vars.example` | Mẫu local; database ID không phải DB thật |
| Sinh cấu hình production | `accounts/configure-production.mjs` | Đã viết, kiểm tra cú pháp và bundle dry-run bằng thông tin mẫu |
| Workflow deploy thủ công | `.github/workflows/accounts-deploy.yml` | Đã viết; chưa chạy GitHub Actions/deploy thật |
| CI tài khoản | `.github/workflows/docker-release.yml` | Thêm Node/check/test accounts; chưa có bằng chứng run trên GitHub |
| Client thương mại local | `src/account_client.py` | Đã viết lưu vault, gọi API, kiểm tra quyền, cache và quản lý thiết bị |
| Cổng tài khoản dùng chung web/desktop | `web/account.html`, `account.css`, `account.js` | Đã viết và kiểm tra trình duyệt local |
| Gắn quyền vào server/app | `src/server.py`, `web/app.js`, `web/index.html` | Đã viết màn khóa, API tài khoản, link tài khoản và các gate quyền |
| Chặn tác vụ nền khi không có quyền | `src/calendar_watch.py`, `src/study.py` | Đã viết; chính sách sản phẩm cần chỉnh như mục 7 |
| Build gắn backend cố định | `scripts/build.py --accounts-url` | Đã viết; chưa build EXE Windows thương mại |
| Kiểm thử mới | `tests/test_accounts.py`, `accounts/test/accounts.test.mjs` | 9 test Python mới, 12 test Worker |
| Tài liệu | `docs/ACCOUNTS.md`, `CLAUDE.md`, README, HANDOVER | Đã bổ sung; file này tổng hợp việc đã/chưa làm |
| Bản đồ workflow | `scripts/workflow_map.py`, `.ua/` | Có phân tích mới; xem trạng thái xác minh ở mục 11 |

### OTP và phiên đang hoạt động thế nào

- Chuẩn hóa email chữ thường hoặc số điện thoại dạng E.164.
- OTP 6 số ngẫu nhiên; hiệu lực 5 phút, tối đa 5 lần sai; lưu HMAC, không lưu OTP bản rõ trong DB.
- OTP mới làm OTP cũ không dùng được; OTP đã xác minh không dùng lại, kể cả yêu cầu song song.
- Giới hạn hiện tại: 1 lượt/phút/danh tính, 5 lượt/giờ/danh tính, 15 lượt/giờ/IP; mặc định 100 lượt/ngày toàn hệ thống. Có thêm giới hạn API và xác minh.
- Phiên opaque 7 ngày, DB chỉ lưu hash; logout thu hồi phiên. Website dùng cookie; desktop nhận token qua proxy local rồi lưu vault.
- Kiểm tra HTTPS/origin/body size, không bật CORS rộng; không phục vụ toàn bộ giao diện quản lý local qua website public.
- SMS bị tắt mặc định. Chưa thử gửi email/SMS thật; test dùng nhà cung cấp giả lập.

## 4. Phần tạo key đang làm dở — bàn giao chi tiết

### Luồng hiện có

1. Admin xác nhận khách đã mua, chạy `grant` với email/số điện thoại chính xác, số ngày và số thiết bị.
2. Khách yêu cầu OTP, xác minh để có phiên.
3. Khách bấm lấy key cho gói được cấp: `/api/licenses/key` sinh `CZ-` cộng 40 ký tự hex (160 bit ngẫu nhiên).
4. Key hiện một lần trên giao diện; DB lưu digest. Điều kiện cập nhật nguyên tử bảo đảm yêu cầu song song chỉ một yêu cầu lấy được key.
5. Khách bấm dùng key hoặc nhập key vào `/api/licenses/redeem`; backend gắn `owner_id`, bắt đầu hạn dùng theo số ngày của gói, đánh dấu tiêu thụ.
6. Desktop đăng ký UUID của lần cài qua `/api/devices/activate`; trigger DB giữ giới hạn số thiết bị ngay cả khi có cạnh tranh.
7. `/api/licenses/check` kiểm tra chủ sở hữu, thiết bị, hết hạn và thu hồi. Khách có thể xóa thiết bị của mình; admin có thể thu hồi gói.

**Quyền admin:** `ADMIN_TOKEN` là bearer secret, hiện chưa có MFA/RBAC/giao diện nhân viên. Chỉ đưa vào môi trường CLI hoặc GitHub/Cloudflare secrets; không gửi qua chat, không đặt vào frontend.

### Dữ liệu

Các bảng hiện có: `users`, OTP/challenge, rate limits, `sessions`, `licenses`, `devices`, audit cấp/thu hồi. Schema thật là nguồn chuẩn để lấy tên cột. Gói giữ danh tính được cấp, digest key, chủ sở hữu sau kích hoạt, số ngày, số thiết bị, hạn và trạng thái thu hồi. Chưa có orders, payment events, plan catalog, workspace, credit ledger hoặc lịch sử gia hạn đầy đủ.

### API hiện có

Tất cả đường dẫn sau nằm dưới `/api/` và dùng POST:

| Nhóm | Đường dẫn |
| --- | --- |
| Danh tính/phiên | `otp/request`, `otp/verify`, `logout`, `me` |
| Key/quyền | `licenses/key`, `licenses/redeem`, `licenses/check` |
| Thiết bị | `devices/activate`, `devices/remove` |
| Quản trị | `admin/grant`, `admin/revoke` |

GET `/health` phục vụ kiểm tra dịch vụ; portal dùng tài nguyên account được whitelist. Đây là API hiện tại, không phải toàn bộ hợp đồng `/v1` đề xuất trong Word.

### Việc phải hoàn tất trước khi bán

- [ ] Chốt OTP không mật khẩu hay cần Google OAuth/mật khẩu; không phát mật khẩu chung cho mọi khách.
- [ ] Xử lý mất phản hồi lúc nhận key; thiết kế cấp lại/audit và retry kích hoạt idempotent cho cùng chủ sở hữu.
- [ ] Chốt chuyển máy, cooldown, khôi phục tài khoản và hỗ trợ khách mất thiết bị.
- [ ] Có quy trình gia hạn, hủy/hoàn tiền, chống cấp trùng giao dịch; hiện chỉ grant/revoke thủ công.
- [ ] Chốt hạn gói bắt đầu lúc cấp hay kích hoạt; mã hiện bắt đầu khi redeem.
- [ ] Chốt quyền đọc/xuất khi hết hạn và xử lý phiên Zoom đang ghi; sửa gate/watchdog cho đúng.
- [ ] Quyết định offline lease có chữ ký hay giữ online; nếu làm offline phải thiết kế khóa ký, xoay khóa, đồng hồ và thu hồi.
- [ ] Chạy nghiệm thu key với mạng chập chờn, nhiều máy, retry, thu hồi và nâng cấp phiên bản trên Windows thật.
- [ ] Xây quản trị có xác thực mạnh/audit nếu nhiều người cấp quyền; chưa tự động hóa bán hàng.

## 5. Kết quả kiểm thử đã có

- Python: **63 test pass**, bao gồm 9 test mới cho client/quyền local. Log phiên này: `/tmp/cun-zoom-license-python-tests.log` (file tạm, không bảo đảm tồn tại sau khi đổi môi trường).
- Worker: **12 test pass** với Miniflare/D1 và email provider giả lập. Bao phủ OTP hết hạn/sai/replay/cạnh tranh, phiên/logout, rate limit, phân quyền admin/khách, key chỉ hiển thị và dùng một lần, cô lập tài khoản, thiết bị và thu hồi/hết hạn.
- Chromium/Playwright local: OTP portal, lấy key một lần, reload/redeem, bố cục mobile, desktop login/activate, vào ứng dụng, xóa thiết bị rồi khóa lại; không có page error. Đây là dữ liệu thử, không phải khách thật.
- Kiểm tra source/cú pháp JS đã chạy. Worker bundle dry-run cho cấu hình local và cấu hình production **mẫu** đã thành công; dry-run không tạo hạ tầng.
- Trước thay đổi thương mại, onboarding đã cài Python/Node, chạy 54 test nền và Docker smoke test non-root/auth/CSRF/vault/restart. **Không dùng kết quả Docker nền đó để khẳng định bản thương mại mới đã qua Docker integration.**
- Chưa gửi OTP thật, chưa chạy Twilio thật, chưa build/kiểm thử EXE Windows thương mại, chưa chạy phòng Zoom thật hoặc xác nhận phê duyệt SDK/OBF/RTMS.

## 6. Production: đã chuẩn bị gì, thiếu gì

**Đã chuẩn bị cấu hình production, chưa có máy chủ production đang chạy.** Hướng triển khai hiện dùng dịch vụ serverless, không cần một VPS riêng cho backend tài khoản.

`configure-production.mjs` yêu cầu origin HTTPS chính xác, UUID D1 thật, sender email và URL tải HTTPS; sinh `accounts/.wrangler/production.json` bị Git bỏ qua. Không ghi credential vào file đó. Sample đã dùng để dry-run không được mang đi deploy như thông tin thật.

Workflow `accounts-deploy.yml` chạy thủ công, dùng environment `accounts-production`: cài deps → test → kiểm tra cấu hình → sinh config → dry-run → migrate D1 remote → deploy → nạp secrets qua stdin → kiểm tra health. Chưa thực thi workflow này trên GitHub. Có khoảng chuyển tiếp giữa deploy và nạp secrets, cần tính đến khi đưa hệ thống đang có khách lên bản mới.

### Cần người triển khai cung cấp trong dashboard dịch vụ

GitHub environment variables:

- `CLOUDFLARE_ACCOUNT_ID`
- `ACCOUNTS_PUBLIC_ORIGIN`: origin HTTPS thực của portal/API, không có dấu `/` cuối.
- `ACCOUNTS_D1_DATABASE_ID`: UUID DB đã tạo.
- `ACCOUNTS_EMAIL_FROM`: địa chỉ đã xác minh trên Resend.
- `ACCOUNTS_DOWNLOAD_URL`: link bản cài **thương mại** thật.
- `ACCOUNTS_WORKER_NAME`: tên Worker, có giá trị mặc định trong script.

GitHub/Cloudflare secrets:

- `CLOUDFLARE_API_TOKEN` có quyền triển khai Worker/D1 cần thiết.
- `OTP_SECRET`, `ADMIN_TOKEN`: ngẫu nhiên, mỗi giá trị ít nhất 32 ký tự.
- `RESEND_API_KEY`.

Không đưa giá trị secret vào Markdown/chat/Git. SMS vẫn tắt; nếu mở cần cấu hình và kiểm thử Twilio riêng. Domain tùy chỉnh/DNS và xác minh sender cần thao tác thật trong dịch vụ, workflow hiện không tự đăng ký domain. Tạo DB, backup/restore, cảnh báo lỗi/chi phí, retention và rotation secret vẫn cần hoàn tất.

### Thứ tự tiếp tục triển khai

1. Xử lý các quyết định sản phẩm và rủi ro phát hành ở mục 7 trước khi bán rộng.
2. Tạo Worker/D1, chọn origin thật và xác minh sender Resend; thiết lập vars/secrets qua dashboard an toàn.
3. Chạy cấu hình/dry-run và migration trên staging trước, sau đó workflow production; kiểm tra `/health` cùng OTP và grant/redeem thật.
4. Build Windows với `--accounts-url https://<origin-thật>`; file cấu hình được bundle cố định. Bản đóng gói không nhận đổi origin qua biến môi trường như bản source dev.
5. Đưa artifact thương mại đúng vào URL tải; nghiệm thu trên máy Windows sạch. CI Windows hiện vẫn chưa truyền `--accounts-url`, nên **bản release mặc định chưa tự trở thành bản thương mại**.
6. Kiểm thử thu hồi/hết hạn/mất mạng, phục hồi DB, xác minh không lộ secret và kiểm tra dữ liệu khách cũ trước khi mở bán.

## 7. Khác biệt phải giải quyết với tài liệu Word

File Word là đánh giá và phương án phát triển ở commit nền. Những câu “chưa sửa mã”, “working tree sạch”, “54 test”, “82 file” trong phụ lục là lịch sử của tài liệu gốc, **không mô tả working tree bàn giao hiện tại**. Các phát hiện của Word chưa được phiên này tái hiện/sửa chỉ vì đã chép vào tài liệu.

| Vấn đề | Mã trong phiên này | Word đề xuất / việc cần quyết định |
| --- | --- | --- |
| Hết hạn | Gate chặn hầu hết thao tác, cả đọc/tải; stop/quit vẫn được phép | Giữ đọc/xuất dữ liệu thuộc khách; sửa gate theo từng năng lực |
| Đang ghi Zoom khi mất quyền/mạng | Watchdog kiểm tra 15 giây, có thể dừng bot sau khi cache quyền tối đa 60 giây không còn hợp lệ | Không âm thầm cắt bản ghi đang chạy; chốt hành vi và thông báo rõ |
| Offline | Kiểm tra online, fail-closed khi cache hết | Word gợi ý lease Ed25519 72 giờ, refresh 24 giờ; chưa làm |
| Retry redeem | Key tiêu thụ rồi trả 409 ở lần sau | Cùng chủ sở hữu retry nên trả lại kết quả cũ một cách an toàn |
| Độ dài key | 20 byte ngẫu nhiên = 160 bit | Word gợi ý 32 byte; cần đồng bộ đặc tả, không ghi đã thực hiện 32 byte |
| Backend | D1 nhỏ, cấp gói thủ công | Orders/payment/workspaces/entitlement ledger là hạng mục sau, chưa có |
| Tích hợp Zoom | Dựa nền Meeting SDK/OAuth/OBF hiện có | RTMS/adapter/thử phòng thật/phê duyệt là việc độc lập chưa hoàn thành |

## 8. Backlog từ Word chưa làm trong phiên này

### P0 — độ tin cậy và điều kiện phát hành

- [ ] Tái hiện/sửa `_chunks` cắt mất phần còn lại của dòng dài; test giữ đầy đủ nội dung trong budget.
- [ ] Không gọi AI khi TXT/tài liệu không có nội dung đọc được.
- [ ] Fingerprint theo byte nội dung và model/cấu hình, tránh chỉ dựa tên/kích thước/mtime.
- [ ] Kiểm chứng Zoom thực tế, quyền SDK/OBF và hướng RTMS phù hợp trước khi cam kết bán.
- [ ] Giải quyết chính sách đọc/xuất, ghi đang chạy và mất mạng của phần license như mục 7.

### P1 — đợt thương mại đầu

- [ ] Schema đầu ra AI, kiểm tra bằng chứng/source refs, retry có giới hạn, đáp án trắc nghiệm hợp lệ.
- [ ] Job bền vững SQLite, retry/backoff, lease/fencing, restart không mất trạng thái; theo dõi usage/cost.
- [ ] Thư viện trên 300 mục, UUID bền vững khi di chuyển file, phân trang và tìm kiếm.
- [ ] Thanh toán payOS: chữ ký webhook, số tiền/tiền tệ, inbox/outbox, unique transaction, duplicate/out-of-order, reconciliation.
- [ ] Gia hạn từ `max(hạn hiện tại, server now)`, hoàn tiền/thu hồi có ledger; MFA/RBAC/audit quản trị.
- [ ] Kế hoạch entitlement theo tính năng/phiên bản, lease offline và chuyển thiết bị theo chính sách đã chốt.
- [ ] Ký mã Windows/update manifest, migration/backup/restore/rollback và chẩn đoán có redaction.

### P2 — sau khi xác nhận nhu cầu

- [ ] Chế độ họp: biên bản, quyết định, action items có dẫn chứng; không tự bịa người nói/deadline.
- [ ] Transcript JSON có thời gian/source, xuất Word, từ điển thuật ngữ, tìm kiếm FTS trước embeddings.
- [ ] Recording chunk/manifest/checksum, kiểm tra dung lượng, xử lý mất điện; pHash/debounce slide.
- [ ] Multi-tenant workspace, phân quyền dữ liệu và dịch vụ AI cloud nếu cần.
- [ ] Credit ledger/reserve/consume và metering phía server chỉ khi nhà cung cấp thực sự chịu chi phí AI; không tính tiền theo số phút client tự báo.

Các ước lượng 35–56 ngày dev trong Word là đề xuất của tài liệu gốc, không phải tiến độ đã thực hiện hoặc cam kết thời gian của phiên này.

## 9. Nghiệm thu cần bổ sung

Word có T01–T14, hiện chưa hoàn thành trọn bộ: bảo toàn text dài; input rỗng; content/model digest; schema/bằng chứng AI; thư viện 301+; restart jobs; key duplicate/mất phản hồi; webhook giả/duplicate/out-of-order; gia hạn/hoàn tiền/thiết bị; offline/đồng hồ/lease; quota/concurrency/fencing; cô lập workspace; Zoom thật/reconnect; disk/power/update/restore. Test license hiện tại chỉ bao phủ một phần, không thay thế bộ này.

## 10. Chỉ dẫn cho người tiếp nhận / Claude Code

Đọc theo thứ tự: `AGENTS.md` → file này → `docs/ACCOUNTS.md` → `docs/WORKFLOW.md` → mã nguồn liên quan. `CLAUDE.md` ở root là điểm vào ngắn. Giữ dữ liệu học/API key AI/SDK ở ngoài Git. Không thay đổi mô hình bán hàng hoặc mở toàn bộ app local public chỉ vì đã có portal.

Kiểm tra ở repo root:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/check_source.py
npm --prefix accounts ci
npm --prefix accounts test
node --check accounts/worker.mjs
node --check accounts/configure-production.mjs
```

Xem `accounts/package.json` và `docs/ACCOUNTS.md` để chạy Wrangler và CLI theo đúng cú pháp. Khi dùng CLI cấp gói, `ADMIN_TOKEN` phải có trong môi trường an toàn:

```bash
node accounts/admin.mjs grant --url https://<origin-thật> --identity <email-hoặc-E164> --days 30 --devices 1
node accounts/admin.mjs revoke --url https://<origin-thật> --license <license-id>
```

Mẫu giao việc cho Claude Code:

> Tiếp nhận Cún Zoom từ docs/CHAT_HANDOVER.md và CLAUDE.md, tuân thủ AGENTS.md. Kiểm tra working tree/branch trước khi sửa. Backend OTP/key đã có bản local; chưa production. Trước hết xử lý retry key/redeem và chính sách giữ đọc/xuất, không cắt bản ghi đang chạy; nêu rõ điểm cần chủ sản phẩm chốt về offline/mật khẩu. Không coi Word là tính năng đã làm. Sau đó triển khai staging bằng cấu hình thật qua secrets an toàn, build Windows với accounts-url, chạy nghiệm thu mạng chập chờn/thu hồi/thiết bị. Cập nhật tài liệu và bản đồ workflow cùng mã; không commit secret hoặc dữ liệu khách.

## 11. Theo dõi GitHub/workflow và giới hạn bàn giao

- Đã viết workflow CI/deploy và cập nhật công cụ lập bản đồ trong working tree.
- Đã refresh bản đồ cùng file bàn giao: 6 miền, 21 luồng, 127 bước, 158 cạnh. Validator Understand Anything xác nhận domain graph 154 node/158 cạnh và knowledge graph 90 node/89 cạnh; workflow check đạt với snapshot 101 file. Đã mở dashboard bằng Chromium, kiểm tra miền tài khoản, luồng cấp gói/lấy key và chi tiết bước sinh key với đường dẫn mã nguồn.
- Chưa có bằng chứng thay đổi đã commit/push lên GitHub hoặc GitHub Actions đã chạy. API GitHub của môi trường trả `Forbidden`; native Git vẫn đọc được remote. Không tự suy ra push thành công từ việc có file workflow local.
- `main` remote đã di chuyển so với commit nền; trước khi đưa lên cần fetch/review chênh lệch, không force push hoặc ghi đè thay đổi người khác.
- Cấu hình cloud onboarding đã được lưu dạng draft, không có bằng chứng người dùng đã publish cấu hình môi trường đó.
- Docker integration bản thương mại, staging/production, OTP thật, Windows thật và Zoom thật vẫn cần bằng chứng riêng nếu chưa có xác minh bổ sung sau mốc tài liệu này.
- `git diff --check` hiện báo trailing whitespace tại dòng mới trong `src/calendar_watch.py`, `web/app.js`, `web/index.html` do CRLF; cần chuẩn hóa có kiểm soát trước commit. Kiểm tra với `git -c core.whitespace=cr-at-eol diff --check` đã đạt; không chuẩn hóa toàn bộ file để tránh tạo diff không liên quan.

## 12. Phụ lục nguyên nội dung tài liệu Word được cung cấp

Nguồn: `Ban_giao_phat_trien_Cun_Zoom.docx` do chủ sản phẩm gửi. Phần sau là chuyển đổi sang Markdown để người nhận không cần mở lại Word; bảng và đường dẫn được giữ khi có thể. Các nhận định/phương án của tài liệu gốc được giữ như nguồn tham chiếu, không nâng thành trạng thái hoàn thành của phiên này.

---
Bàn giao phát triểnCún Zoom

Đánh giá mã nguồn và phương án thương mại hóa

Dành cho chủ sản phẩm, lập trình viên và tester • Ngày 23 tháng 10 năm 2026

Phiên bản đối chiếu: main, Cún Zoom 2.2.0

Commit: 53decc9d4b95fc032f132c375f05960eb5e824a2

Kết luận cần hành động

Ưu tiên sửa độ tin cậy của dữ liệu, xác nhận hướng tích hợp Zoom và chốt thứ khách hàng trả tiền để nhận. Sau đó mới bổ sung dịch vụ cấp quyền và thanh toán. Bản hiện tại là ứng dụng local, dùng máy và khóa AI của khách; mô hình thu phí phút cloud chưa phù hợp để áp dụng trực tiếp.

Sửa ngay ba tình huống đã tái hiện: cắt mất dòng dài, nhận diện thay đổi chỉ dựa vào metadata file, gọi AI khi tài liệu thực tế không có nội dung đọc được.

Đóng điều kiện phát hành Zoom bằng thử nghiệm phòng thật và xác nhận phương thức tích hợp phù hợp. RTMS chưa có trong mã nguồn hiện tại.

Giữ bản local MIT làm nền tảng; bán dịch vụ cài đặt, hỗ trợ, bảo trì hoặc dịch vụ cloud có giá trị riêng. Không coi key local là hàng rào chống sao chép chắc chắn.

Xây một backend nhỏ cho đơn hàng, gói dịch vụ, mã kích hoạt và thiết bị. Tách backend này khỏi HTTP server local hiện có.

Bổ sung chế độ họp với biên bản, quyết định và đầu việc có dẫn chứng; hiện sản phẩm tập trung vào bài học, môn học và ôn tập.

Cách sử dụng bản bàn giao

Các mục “Hiện trạng” gắn với nguồn tại commit trên. Các mục “Đề xuất” là đặc tả công việc cho phiên bản tiếp theo, chưa phải tính năng đã triển khai. P0 cần xử lý trước bán rộng; P1 phục vụ đợt thương mại đầu; P2 làm sau khi có nhu cầu được xác nhận.

Mốc bàn giao này là tài liệu đánh giá và triển khai. Mã nguồn repository chưa được chỉnh sửa; trạng thái làm việc vẫn sạch sau rà soát. Liên kết chứng cứ ở cuối tài liệu dùng commit cố định để developer đối chiếu.

### 1 Hiện trạng và kết quả đối chiếu

| Thành phần | Đã thấy trong mã nguồn | Ý nghĩa khi thương mại hóa |
| --- | --- | --- |
| Nền tảng | Windows EXE và Docker; dữ liệu theo từng lần cài. [R1, R9] | Chưa phải dịch vụ nhiều khách hàng dùng chung. |
| Quyền truy cập | Basic Auth cho Docker; Host, Origin và token cho API local. [R3, R10] | Chưa phải tài khoản thanh toán hoặc quyền theo gói. |
| Zoom | Meeting SDK, OAuth và OBF; một worker bot mỗi tiến trình. [R4] | Không có RTMS; người dùng tự cấp SDK và cấu hình Zoom. |
| Âm thanh | WAV thật; Faster Whisper base trên CPU; mốc bắt đầu từng đoạn. [R7, R8] | Có nền để bổ sung transcript JSON và dẫn chứng. |
| AI | Claude bằng key khách hoặc Ollama; ghi chú, tổng hợp, đề cương, đề thi. [R5, R6] | Đã có pipeline; cần tăng kiểm chứng đầu vào và đầu ra. |
| Thư viện | File local, tải ZIP; danh sách tối đa 300 buổi. [R11] | Cần phân trang và ID ổn định khi dữ liệu tăng. |
| Phát hành | CI Linux/Windows, build EXE/Docker, SHA256SUMS. [R12] | README ghi EXE chưa ký số; cần quy trình cập nhật tin cậy. |
| Thương mại | Không thấy mô-đun đơn hàng, license, gói, hóa đơn hay webhook thanh toán trong snapshot. | Cần bổ sung lớp thương mại riêng. |

Kiểm tra trong đợt rà soát

Đã chạy check_source.py, workflow_map.py check và kiểm tra cú pháp hai file JavaScript. Bản đồ khớp 82 file nguồn. Kết quả bộ unit/integration được ghi trong biên bản nghiệm thu cuối tài liệu; ba tình huống lỗi được kiểm tra bằng dữ liệu tạm và AI giả lập, không gửi nội dung thật ra ngoài.

Hồ sơ VALIDATION của 2.2.0 ghi 54 tests Linux đạt; AI thật chưa kiểm tra trong lần phát hành đó. Hồ sơ 2.1.0 ghi OAuth và phòng Zoom thật chưa kiểm tra. Kết quả tester mới hơn cần gắn với commit, hệ điều hành, tài khoản thử và log tương ứng để cập nhật hồ sơ. [R2]

### 2 Các vấn đề đã tái hiện và cách sửa

P0 Dòng văn bản dài bị mất phần đuôi

Hiện trạng: _chunks dùng line[:size]. Với một dòng 25 ký tự và size = 10, tổng đầu ra chỉ còn 10 ký tự. Khi nhánh chia nhỏ được dùng, đoạn dài một dòng có thể mất thông tin mà không báo lỗi. [R5 dòng 227–236]

Thuật toán sửa: chia mỗi dòng quá dài thành nhiều đoạn liên tiếp; ưu tiên ranh giới câu hoặc khoảng trắng nhưng phải giữ toàn bộ ký tự. Mọi nguồn text, kể cả tài liệu tải lên, đi qua cùng bộ chia. Sau bước gộp, nếu vẫn vượt ngân sách thì tiếp tục gộp theo tầng.

for source in text_sources:    chunks = split_preserving_all_text(source, budget)    partials += summarize_each(chunks)while total_tokens(partials) > merge_budget:    partials = merge_in_bounded_batches(partials)

Nghiệm thu: kiểm tra đầu, giữa và cuối file một dòng; kiểm tra đủ mã đoạn nguồn qua từng tầng. Ngân sách tính cả system prompt, schema, ảnh/PDF và phần trả lời dự kiến, không chỉ số ký tự text.

P0 Tài liệu rỗng vẫn gọi AI

Hiện trạng: fingerprint xác nhận có file, nhưng phần trích xuất có thể rỗng. Với một file TXT rỗng, analyze_session vẫn gọi ai.generate; đã tái hiện bằng mock chặn trước mạng. [R5 dòng 239–277]

Thuật toán sửa: phân loại phần đầu vào sau trích xuất thành text có nghĩa, ảnh/PDF hỗ trợ và phần bị bỏ qua. Nếu không còn phần dùng được, trả trạng thái no_usable_input, ghi lý do và không gọi AI. Với Ollama, chỉ thử lại bỏ ảnh nếu lỗi xác định là không hỗ trợ ảnh; sau bỏ ảnh phải kiểm tra lại nội dung.

P1 Dấu vân tay chưa băm nội dung

Hiện trạng: fingerprint băm tên, kích thước và mtime, không băm bytes. Thay AAAA bằng BBBB và giữ mtime cho kết quả giống nhau. Đổi model cũng chưa nằm trong dấu vân tay. [R5 dòng 183–189]

Thuật toán sửa: SHA-256 theo luồng từng file; ghép các content hash đã sắp thứ tự với parser_version, prompt_version, schema_version, provider, model và lựa chọn người dùng. Không đưa API key vào hash. Có thể dùng metadata để phát hiện nhanh, nhưng kiểm chứng bytes khi nhập/sửa hoặc đồng bộ lại bắt buộc.

### 3 Hoàn thiện pipeline AI và thư viện

Kiểm tra cấu trúc và nội dung đầu ra

Hiện trạng: ai_backend gửi JSON schema tới provider nhưng sau phản hồi chỉ json.loads. Đề thi chưa ép chính xác 4 lựa chọn ngay trong schema; trường nguồn chủ yếu là chuỗi do model tạo. [R5, R6]

1. Validate JSON Schema ở máy chủ ứng dụng bằng thư viện chuẩn. Bổ sung minItems = maxItems = 4 cho lựa chọn; giới hạn độ dài, số câu và phạm vi điểm.

2. Kiểm tra nghiệp vụ sau schema: đáp án có tồn tại, ID nguồn có trong dữ liệu đầu vào, ngày hạn có căn cứ, số câu đúng yêu cầu. JSON hợp lệ chưa chứng minh nội dung đúng.

3. Cho phép tối đa một lần sửa đầu ra với lỗi cụ thể; vẫn sai thì đánh dấu cần xem lại, giữ nguồn và không phát hành kết quả như đã xác nhận.

4. Ghi provider, model, phiên bản prompt/schema, nguồn và cảnh báo vào metadata để truy vết.

Ngăn chi phí lặp lại và kết quả bỏ sót nguồn

Engine hiện có hàng đợi và failed trong bộ nhớ, chạy một việc AI mỗi lúc. Restart làm mất dấu lỗi; lệnh chạy lại có thể phát sinh chi phí mới. Thay bằng jobs SQLite bền vững, unique trên job_key = hash(loại việc, đối tượng, input_digest, phiên bản xử lý). [R5 dòng 534–662]

Lưu usage trả về từ provider, request_id và trạng thái; báo chi phí ước lượng trước khi chạy toàn môn. max_tokens = 64000 hiện là trần output, không phải mức luôn bị tính phí; nên đặt trần theo loại việc và đo usage thực tế. [R6 dòng 124–158]

Khắc phục giới hạn thư viện

library.items chỉ trả 300 buổi mới nhất; find lại tra trên danh sách này. Vì vậy buổi cũ hơn giới hạn có thể không truy cập qua API dù file vẫn còn. ID cũng băm đường dẫn tuyệt đối, nên đổi vị trí thư mục làm đổi ID. [R11 dòng 11–52]

Hướng làm: cấp UUID cố định trong buoi_hoc.json; migration tạo UUID một lần cho dữ liệu cũ; index SQLite ánh xạ UUID với đường dẫn. API list dùng cursor và page_size; API find theo UUID không phụ thuộc trang đang hiển thị. Đổi thư mục thì cập nhật đường dẫn, không cấp lại ID.

Nghiệm thu: 301 buổi vẫn đọc/tải được buổi đầu; chuyển thư mục giữ link nội bộ; lỗi AI sau restart không tự chạy lại vô hạn; thay model hoặc schema làm dữ liệu cũ được đánh dấu cần cập nhật.

### 4 Chốt hướng tích hợp Zoom

Điều kiện phải giải quyết trước khi bán rộng

Tài liệu Meeting SDK Linux hiện nêu SDK dành cho tình huống con người sử dụng và hướng bot hoặc AI notetaker sang RTMS. FAQ vẫn có nhánh OBF cho ứng dụng legacy. Có OBF không tự chứng minh một app mới thuộc trường hợp được hỗ trợ. Cần xác nhận phạm vi tài khoản/app của dự án với Zoom. [W1, W2]

RTMS là phương án nên thử cho bản dịch vụ mới. Tài liệu yêu cầu Developer Pack credits, các scope dữ liệu và sự kiện RTMS; luồng điều khiển, host và người dùng vẫn phải đáp ứng điều kiện Zoom. Không coi việc có link họp là quyền lấy dữ liệu. [W3, W4]

Hướng triển khai theo lớp adapter

1. Tạo giao diện CaptureProvider gồm prepare, start, stop, status và events. Giữ adapter SDK cho phạm vi được phép; thêm adapter RTMS và adapter nhập bản ghi.

2. Tạo General app user-managed cho RTMS; thiết lập OAuth, webhook HTTPS và chỉ xin scope dữ liệu thực sự dùng. Làm PoC bằng phòng thử đã được host cho phép.

3. Xác minh webhook, lưu inbox chống xử lý trùng; ánh xạ tài khoản Zoom với workspace đã cấp quyền. Dùng meeting UUID cùng stream ID, không chỉ meeting ID có thể tái sử dụng.

4. Nhận stream theo SDK/tài liệu chính thức; chuẩn hóa audio, transcript, slide và trạng thái vào cùng manifest phiên để tái sử dụng pipeline học tập/họp.

5. Xử lý kết nối lại theo loại lỗi: signaling, media hay stream chấm dứt. Không tự nối lại sau thu hồi quyền hoặc người dùng chủ động dừng. Ghi khoảng dữ liệu thiếu và không hứa khôi phục phần không nhận được. [W5]

Mô hình triển khai khả thi

Bản local tiếp tục hỗ trợ nhập bản ghi/tài liệu được phép. Bản RTMS đầu tiên dùng backend có webhook công khai và worker nhận luồng; đây là hạ tầng mới, có chi phí và luồng dữ liệu cloud cần công bố. Không nhúng client secret dùng chung của nhà cung cấp vào EXE.

Nghiệm thu phòng thật: host cấp và thu hồi quyền, khách ngoài tổ chức, phòng chờ, người dùng rời phòng, mạng ngắt, kết thúc họp; nghe WAV, kiểm tra slide và transcript. Lưu bằng chứng theo commit và SDK. Chỉ mở bán luồng Zoom đã đạt; có thể bán xử lý bản ghi tải lên trước.

### 5 Mô hình bán phù hợp với mã nguồn hiện tại

Đề xuất triển khai theo hai chặng. Chặng đầu bán cài đặt, hỗ trợ và bảo trì bản local; chặng sau bán dịch vụ cloud theo tài khoản. Không cần biến toàn bộ ứng dụng thành SaaS ngay để bắt đầu thu tiền.

| Gói đề xuất | Khách trả tiền cho | Cách cấp quyền |
| --- | --- | --- |
| Community local | Mã nguồn tự cài; khách chịu máy, Zoom và AI của mình. | Giữ quyền của bản MIT; không thu hồi quyền đã cấp bởi MIT. |
| Local được hỗ trợ | Cài đặt, kiểm tra tương thích, hỗ trợ, đào tạo và dịch vụ bảo trì. | Tài khoản dịch vụ, thời hạn hỗ trợ, thiết bị đã đăng ký. |
| Cloud cá nhân | Nhận luồng hợp lệ, AI do nhà cung cấp chi trả, lưu trữ hoặc đồng bộ. | Thuê bao + quota do backend kiểm soát. |
| Nhóm | Quản trị thành viên, quyền truy cập, hạn mức chung và hỗ trợ. | Workspace, seat, vai trò và giới hạn phiên đồng thời. |

Giới hạn của key đối với mã MIT

LICENSE hiện cho phép dùng, sửa, phân phối và bán bản sao kèm điều kiện giữ thông báo. Người dùng có thể sửa bỏ kiểm tra key trong một bản local mã mở. Key vẫn hữu ích cho dịch vụ của bạn nhưng không biến mã đã phát hành thành độc quyền. Nếu thêm mô-đun riêng, cần xác định quyền sở hữu và điều kiện phân phối trước khi chọn giấy phép. [R13, W6]

Cách quyết định giá

Với local dùng key AI của khách, công bố rõ phí của bạn là phí sản phẩm/dịch vụ hỗ trợ và chi phí AI trả riêng. Với cloud, đo chi phí một phiên ở mức dùng thông thường và gần hết hạn mức: Zoom, AI, compute, lưu trữ, phí thanh toán, hỗ trợ và dự phòng lỗi.

gia_san_tham_chieu = chi_phi_phuc_vu / (1 - bien_loi_nhuan_muc_tieu)

Công thức là công cụ tính nội bộ, chưa bao gồm mọi khoản thuế hay điều khoản hợp đồng. Chưa chốt mức giá cụ thể khi chưa có số đo chi phí và nhu cầu. Tránh gói “trọn đời không giới hạn” nếu bạn chi trả AI hoặc lưu trữ theo thời gian.

### 6 Thuật toán cấp mã và quyền sử dụng

Đơn vị quyền sử dụng

Entitlement là bản ghi quyền tại backend: account_id hoặc workspace_id, plan, features, starts_at, paid_through, status, max_devices, version. Mã kích hoạt chỉ dùng đổi quyền một lần; Zoom token và Claude key là thông tin hoàn toàn khác.

Cấp và đổi mã

1. Sinh 32 byte bằng CSPRNG; mã hóa Base64URL và thêm tiền tố CZ nếu cần. Lưu SHA-256 của mã cùng order_id, grant_spec, redeem_before và trạng thái; không ghi mã nguyên văn vào log.

2. Người dùng đăng nhập tài khoản thương mại rồi đổi mã qua HTTPS. Rate limit theo tài khoản và nguồn yêu cầu; lỗi không tiết lộ mã thuộc tài khoản nào.

3. Trong một transaction: khóa bản ghi mã, kiểm tra chưa dùng/chưa thu hồi/còn hạn; tạo grant có unique source_key; đánh dấu người đổi và thời gian. Hai yêu cầu đồng thời chỉ cấp quyền một lần.

4. Nếu HTTP response mất sau commit, lần gọi lại trả kết quả grant cũ cho đúng người đổi. Không cấp thêm thời hạn. Mua trực tiếp trên website thì cấp vào tài khoản tự động, không bắt nhập key.

Token quyền có chữ ký cho bản desktop

Backend ký lease bằng Ed25519 từ thư viện chuẩn. Client chỉ có public key. Payload chứa issuer, audience, account/workspace, installation_id, features, issued_at, expires_at, entitlement_version, key_id. Serialize theo định dạng cố định hoặc dùng thư viện JWS hỗ trợ thuật toán đã chọn; tránh tự chế chữ ký.

Ví dụ chính sách để pilot: lease hợp lệ tối đa 72 giờ, làm mới mỗi 24 giờ khi có mạng; expires_at không vượt paid_through. Thu hồi online có hiệu lực khi refresh; thiết bị offline có thể dùng đến khi lease hết hạn. Đây là đánh đổi phải công bố, không hứa thu hồi tức thời offline.

installation_id là UUID ngẫu nhiên, có thể kết hợp khóa thiết bị và challenge nếu cần. Lưu bằng cơ chế bảo vệ của hệ điều hành; không khóa cứng theo IP. Chuyển máy có thao tác tự thu hồi thiết bị cũ, cooldown và đường hỗ trợ.

Hết gói vẫn cho đọc/xuất dữ liệu của khách. Chỉ chặn dịch vụ tính phí mới; không phá dữ liệu và không âm thầm cắt bản ghi đang chạy. Bảo vệ local chỉ hạn chế lạm dụng thông thường; dịch vụ cloud phải kiểm tra quyền ở server mọi lần gọi.

### 7 Thuật toán thanh toán và gia hạn

Đề xuất dùng backend thương mại riêng có PostgreSQL và worker. Có thể tích hợp payOS để nhận chuyển khoản; kiểm tra điều kiện và chi phí tài khoản trực tiếp với nhà cung cấp. Chuyển khoản xác nhận tự động không đồng nghĩa có tự động trích tiền định kỳ. [W7]

Luồng xác nhận đơn

1. Backend tạo order với giá, loại tiền, gói, kỳ hạn và account/workspace từ dữ liệu tin cậy. Khóa đơn giá tại thời điểm tạo; client không được tự quyết giá.

2. Tạo payment link với mã đơn duy nhất. return_url chỉ hiển thị trạng thái; không dùng return_url làm bằng chứng đã trả tiền.

3. Webhook: xác minh chữ ký theo SDK/tài liệu provider, đối chiếu mã đơn, số tiền và trạng thái. Lưu sự kiện vào payment_inbox trước khi trả 2xx. Event không hợp lệ bị từ chối; sự kiện test không cấp gói.

4. Worker xử lý trong transaction, có khóa order. Dùng unique(provider, transaction_id) cho tiền và unique(order_id, grant_type) cho quyền; lưu event trùng chỉ một lần.

5. Cấp quyền và đánh dấu đơn đã xử lý trong cùng transaction; ghi outbox cho thông báo để lỗi gửi không làm mất quyền hoặc cấp lại.

6. Tác vụ đối soát truy vấn trạng thái đơn còn chờ; webhook đến muộn và sai thứ tự không được ghi đè trạng thái mới. Khi nghi ngờ, lấy trạng thái hiện hành từ provider.

verify_provider_signature(raw_payload)event = persist_inbox_once(provider_event_key)BEGIN  order = lock_order(event.order_id)  validate_amount_currency_status(event, order)  record_payment_once(provider, transaction_id)  apply_grant_once(order.id, grant_spec)  mark_order_paid_and_event_processed()COMMIT

Gia hạn và hoàn tiền

Gói trả trước cùng loại: thời hạn mới = max(paid_through hiện tại, giờ server) + kỳ mua theo lịch đã quy định. Thuê bao định kỳ phải theo kỳ của provider. Nâng/hạ gói cần bảng chuyển đổi riêng, không cộng thời hạn tùy tiện.

Hủy gia hạn giữ quyền đến cuối kỳ đã trả. Hoàn tiền ghi giao dịch đảo và cập nhật quyền theo chính sách; không xóa lịch sử. Admin cộng quyền thủ công cần lý do, người thao tác và mã yêu cầu duy nhất. Cổng quản trị thương mại dùng tài khoản và MFA riêng, không dùng mật khẩu Docker local.

### 8 Dữ liệu tối thiểu cho backend thương mại

Các bảng dưới đây là thiết kế mới. Giữ database thương mại ở backend; SQLite local phục vụ index và jobs. Không dùng các file JSON local làm sổ thanh toán.

| Bảng | Trường chính | Ràng buộc cần có |
| --- | --- | --- |
| accounts | id, login_subject, email_verified, status | Unique login_subject; quyền admin riêng. |
| workspaces và members | workspace_id, account_id, role | Unique cặp workspace/account; mọi truy vấn kiểm tra membership. |
| plans | id, version, features, policy | Gói đã bán giữ snapshot hoặc version. |
| orders | id, workspace_id, amount_minor, currency, plan_snapshot, status | Mã đơn duy nhất; số tiền số nguyên, không dùng float. |
| payments và inbox | provider, transaction_id, event_key, payload_hash, status | Unique giao dịch; inbox có attempt và processed_at. |
| grants và entitlements | source_key, workspace_id, plan, starts_at, paid_through, status, version | Unique source_key; cấp quyền nguyên tử. |
| redemption_codes | code_hash, grant_spec, redeem_before, redeemed_by, redeemed_at | Unique code_hash; đổi một lần. |
| installations | id, account_id, public_key tùy chọn, revoked_at, last_seen | Giới hạn thiết bị kiểm tra trong transaction. |
| jobs local | job_key, type, input_digest, state, lease_until, attempts, result_ref | Unique job_key; trạng thái bền qua restart. |
| audit và outbox | actor, action, target, request_id, time; message state | Không ghi key/token/nội dung họp mặc định. |
| usage cloud tùy chọn | session_id, meter_id, sequence, delta, reservation | Unique sự kiện; giữ và tiêu thụ trong transaction. |

Chính sách dữ liệu

Ngày giờ backend lưu UTC, UI hiển thị theo múi giờ của khách. Mỗi cuộc họp có UUID nội bộ; định danh phòng Zoom và lần họp lưu riêng. Hóa đơn, bản ghi tài chính và dữ liệu họp có chính sách giữ/xóa khác nhau; xóa cuộc họp không xóa lịch sử thanh toán.

Các khóa mã hóa, khóa ký license và secret cổng thanh toán đặt ngoài repository. Luân chuyển khóa có key_id và thời gian chồng lấn hợp lý; không dùng cùng khóa cho license, webhook và cập nhật phần mềm.

### 9 Điểm tích hợp và hợp đồng API

| Phần | Vị trí hiện tại | Thay đổi đề xuất |
| --- | --- | --- |
| Gói và tài khoản | web/app.js, web/index.html | Thêm trang Gói của tôi, thiết bị, lịch sử đơn, đường hỗ trợ. |
| Client license | Chưa có | src/licensing.py gọi backend, verify lease, cache trong vault. |
| Kiểm tra quyền | src/server.py action | Gọi bộ kiểm tra quyền cho dịch vụ trả phí; luôn giữ đường dừng và xuất dữ liệu. |
| AI | src/ai_backend.py | Giữ BYOK; thêm provider managed chỉ qua backend, không gửi secret của nhà cung cấp vào EXE. |
| Dữ liệu và jobs | src/study.py, library.py | Tách jobs.py, content_digest.py, repository/index SQLite. |
| Ghi dữ liệu | src/runner.py, native/*.cpp | Tách adapter, session_id, heartbeat, manifest; hỗ trợ RTMS sau PoC. |
| Bảo trì | AGENTS.md và docs/WORKFLOW.md | Mọi PR sửa mã phải cập nhật graph theo quy trình đã ghim. |

API backend đề xuất

| Endpoint | Hành vi bắt buộc |
| --- | --- |
| POST /v1/orders | Tạo đơn theo gói hợp lệ; Idempotency-Key trả lại cùng đơn. |
| POST /v1/webhooks/payment | Xác minh provider; lưu inbox bền vững; không dựa vào phiên đăng nhập client. |
| GET /v1/entitlements | Chỉ trả quyền của workspace người dùng được phép truy cập. |
| POST /v1/licenses/redeem | Đổi key một lần; cùng người dùng retry nhận kết quả cũ. |
| POST /v1/installations/activate | Đăng ký thiết bị và cấp lease ký số trong giới hạn gói. |
| POST /v1/leases/refresh | Kiểm tra entitlement hiện tại; lease đã thu hồi không được gia hạn. |
| POST /v1/jobs và /v1/sessions | Chỉ cho cloud; kiểm tra quyền, quota, tính lặp và số phiên. |

Mã lỗi nên ổn định: LICENSE_EXPIRED, DEVICE_LIMIT, PAYMENT_PENDING, QUOTA_EXCEEDED, NO_USABLE_INPUT, ZOOM_PERMISSION_DENIED. UI dịch ra tiếng Việt và có hướng xử lý. request_id dùng truy vết; lỗi không chứa secret hoặc toàn bộ transcript.

### 10 Bổ sung giá trị của trợ lý họp

Hiện prompt và dữ liệu tập trung vào sinh viên, môn học, kiến thức, bài tập và đề thi. Nếu bán như trợ lý họp, nên thêm profile “Họp” và giữ profile “Học tập” để tránh đổi hành vi của người dùng cũ. [R5 dòng 37–80]

Biên bản và đầu việc có dẫn chứng

1. Chuẩn hóa transcript thành JSON: segment_id, source_id, start_ms, end_ms, text, speaker_id nếu nguồn thực sự cung cấp. Bản hiện tại mới lưu mốc bắt đầu dạng text; không tự gán danh tính người nói. [R7]

2. Chia đoạn theo chủ đề và thời lượng, có phần giao nhau nhỏ để giữ ngữ cảnh. Lưu vị trí nguồn gốc cho từng đoạn.

3. Trích xuất decisions, action_items, open_questions theo schema. Mỗi mục có evidence_refs; owner và due_date được null khi cuộc họp không xác định.

4. Kiểm tra evidence_refs tồn tại, thời gian nằm trong file; gộp mục trùng nhưng giữ nguồn. Ngày tương đối như “thứ Sáu tới” phải dựa ngày họp và múi giờ, trường hợp mơ hồ yêu cầu người dùng xác nhận.

5. Hiển thị biên bản cho người dùng sửa; bấm dẫn chứng mở đoạn tương ứng. Chỉ xuất bản hoặc gửi ra ứng dụng khác khi người dùng chủ động xác nhận.

Hỏi đáp trên dữ liệu của khách

P2: bắt đầu bằng tìm kiếm từ khóa và chỉ mục SQLite FTS; chỉ thêm embedding khi kết quả thực tế cần tìm theo nghĩa. Truy hồi top-k đoạn trong phạm vi workspace mà người dùng có quyền, sau đó AI trả lời kèm ID nguồn. Nếu bằng chứng không đủ, trả “chưa có dữ liệu để kết luận”.

Thứ nên làm trước chatbot tổng quát

| Tính năng | Cách làm | Lý do ưu tiên |
| --- | --- | --- |
| Xuất biên bản Word | Template + dữ liệu đã validate và người dùng duyệt. | Đầu ra dễ giao việc và lưu hồ sơ. |
| Đầu việc có trạng thái | UUID, owner, due_date, confirmed, completed. | Đo được giá trị sau cuộc họp. |
| Tìm trong transcript | Index và highlight đoạn; giữ mốc thời gian. | Giúp người dùng tự kiểm chứng AI. |
| Từ điển thuật ngữ | Danh sách theo tổ chức/môn, người dùng xác nhận. | Giảm sai tên riêng; không tự sửa mất bản gốc. |

### 11 Thuật toán hàng đợi và phục hồi dữ liệu

Một hàng đợi bền vững cho chép lời và AI

Hiện Engine giữ queue trong RAM; runner cũng trực tiếp khởi chạy chép lời khi bot kết thúc. Hai đường khởi động cần đi qua một scheduler chung để bảo đảm không phát sinh chép lời song song ngoài ý muốn. [R4 dòng 30–37 và 140; R5 dòng 589–601]

1. Tạo job có khóa duy nhất và trạng thái queued. Worker claim bằng transaction, ghi lease_until và worker_generation.

2. Heartbeat gia hạn lease. Chỉ worker có generation hiện hành được ghi trạng thái và công bố kết quả; worker cũ sau timeout không được ghi đè.

3. Lỗi tạm thời được retry hữu hạn với exponential backoff và jitter, tôn trọng Retry-After. Lỗi key sai, quyền bị từ chối, file rỗng hoặc schema sai không tự retry vô hạn.

4. Ghi kết quả vào file tạm rồi đổi tên nguyên tử; ghi manifest cùng phiên bản. Khi restart, phục hồi job quá hạn bằng trạng thái lease và checkpoint, không chỉ nhìn timestamp processing.

5. Nếu provider đã nhận việc nhưng response bị mất, không hứa exactly-once cho chi phí AI; ghi trạng thái chưa xác định, request_id nếu có và chính sách retry minh bạch.

Ghi âm và slide

Worker đã kiểm tra lỗi ghi, cập nhật WAV header định kỳ khoảng 5 giây và khi dừng; không cần làm lại từ đầu. Nên bổ sung preflight dung lượng ổ đĩa, heartbeat độc lập audio và bản ghi sự kiện quyền ghi. [R8]

Hướng làm: chia audio thành các đoạn hữu hạn, ví dụ 1–5 phút hoặc trước ngưỡng dung lượng cấu hình; manifest lưu sample rate, channel, timestamp và checksum từng đoạn. Khi crash, xác minh/khôi phục đoạn cuối rồi đưa phần hoàn chỉnh vào chép lời. Báo rõ đoạn mất, không gắn nhãn hoàn tất nếu thiếu dữ liệu.

Slide hiện bị giới hạn một ảnh mỗi 30 giây và AI chọn tối đa 20 ảnh. Đề xuất bắt thay đổi: lấy frame thu nhỏ, so pHash hoặc độ khác biệt pixel, bỏ vùng con trỏ nếu phù hợp, yêu cầu ổn định vài frame trước lưu. Giữ ảnh đầu/cuối, debounce và giới hạn tần suất để không tăng tải vô hạn. [R5, R8]

Các ngưỡng slide và thời lượng audio là tham số cần đo trên máy khách. Test bằng slide chuyển nhanh, animation, mất quyền ghi và hết dung lượng; không biến mục tiêu cải thiện thành cam kết thu được mọi khung hình.

### 12 Phát hành và vận hành sau bán

Onboarding có kiểm tra từng bước

Thêm wizard phân biệt: cài được SDK, xác thực được SDK, OAuth hợp lệ, vào phòng, được ghi, nhận âm thanh. Chỉ đánh dấu bước đã có bằng chứng. Cho phép khách sử dụng tính năng nhập tài liệu dù chưa cấu hình Zoom; chỉ hiển thị dịch vụ họ đã mua và khả năng thực tế của máy.

Cập nhật phần mềm tin cậy

README ghi EXE chưa ký số; CI đã phát hành checksum. Bổ sung ký số Windows theo phương thức phù hợp với nhà phát hành và manifest cập nhật có chữ ký. Ký số không bảo đảm mọi cảnh báo SmartScreen biến mất. [R1, R12]

1. Manifest gồm version, min_supported, URL artifact, SHA-256, chữ ký và key_id. Client xác minh chữ ký trước tải/chạy; checksum đơn lẻ không đủ xác minh người phát hành.

2. Không cập nhật lúc đang ghi hoặc xử lý dữ liệu. Sao lưu metadata/database, áp dụng migration có phiên bản rồi health check.

3. Có đường rollback ứng dụng và kế hoạch tương thích database. Không chạy bản cũ trên schema mới nếu chưa được kiểm chứng; khôi phục snapshot nhất quán khi cần.

4. Khóa phiên bản phụ thuộc cho bản Docker phát hành, kiểm tra lỗ hổng và lưu danh mục thành phần. CI hiện đã khóa dependencies Windows; mở rộng cùng kỷ luật sang đường phát hành còn lại.

Sao lưu và hỗ trợ

Làm chức năng xuất gói chẩn đoán chỉ gồm version, trạng thái, lỗi và cấu hình đã che bí mật. Cho khách xem trước; không tự đính kèm transcript, âm thanh, iCal hoặc token. Lưu log xoay vòng và request_id.

Sao lưu cần có dữ liệu và metadata nhất quán; khóa truy cập xử lý riêng. DPAPI của Windows không phải kho mang sang máy khác dùng trực tiếp. Sau restore trên máy mới nên yêu cầu kết nối lại tài khoản, trừ khi có quy trình xuất khóa được thiết kế và xác nhận riêng. [R14]

Với cloud, xác định thời hạn lưu audio/transcript, cách xóa và phạm vi backup trước khi bán. Theo dõi tỷ lệ nhận dữ liệu thành công, thời gian xử lý, lỗi AI, tiền/quota lệch và chi phí hỗ trợ. Thông số pilot là mục tiêu nội bộ, chưa coi là SLA công bố.

### 13 Chỉ tính phút khi có dịch vụ cloud

Phần này áp dụng nếu bạn trả chi phí nhận luồng, AI hoặc lưu trữ. Với bản local BYOK, giới hạn phút do client tự báo dễ sửa đổi và không phải số liệu thanh toán đáng tin cậy.

Thuật toán giữ và quyết toán hạn mức

1. Backend xác thực workspace và tạo session bằng Idempotency-Key. Trong transaction, giữ một suất đồng thời và một lượng credit ban đầu, ví dụ 5 phút.

2. Worker cloud tin cậy ghi sự kiện meter theo session_id và sequence. Mỗi sự kiện chỉ được áp dụng một lần; không lấy số giây hoặc số tiền từ desktop làm căn cứ duy nhất.

3. Định kỳ chuyển phần đã dùng từ reserved sang consumed và giữ thêm. Tổng giữ + tiêu thụ không vượt credit khả dụng nếu khách chưa bật chính sách vượt gói.

4. Dùng lease cho suất đồng thời và fencing generation cho worker. Worker cũ không được tiếp tục thu tiền/ghi kết quả sau khi suất được cấp lại.

5. Khi kết thúc, quyết toán phần thực tế, giải phóng giữ thừa và suất bot. Khi worker chết, sweeper đối soát tới mốc có bằng chứng; không cộng phí cho khoảng mù.

6. Ghi ledger bất biến cho grant, reserve, consume, release, expire và refund. Số dư là kết quả tổng hợp; không chỉ sửa một cột remaining.

Chốt đơn vị tính tiền trước khi triển khai

Chọn phút xử lý luồng hoặc phút dữ liệu được xử lý; không dùng số giây có tiếng nói để thay thời lượng nếu gói bán theo thời gian họp. Phòng chờ và phiên thất bại trước khi nhận dữ liệu nên không tính cho khách. Reconnect và gói tin trùng không được tạo lần thu phí mới.

Nếu một cuộc họp có nhiều người dùng cùng sản phẩm, chốt quy tắc phiên chung trước: một workspace có một phiên cho cùng lần họp và cấu hình thu thập; workspace khác có dữ liệu và quyền độc lập. Khóa chống trùng phải dùng lần họp thực tế, không chỉ số phòng.

Credit theo kỳ và credit mua thêm lưu thành từng bucket có hạn dùng rõ ràng. Tiêu thụ bucket hết hạn sớm trước; phiên đi qua ranh giới kỳ tách phần dùng theo thời điểm server. Gói đã hết hạn vẫn cho khách đọc/xuất dữ liệu trong chính sách lưu trữ đã công bố.

### 14 Bộ nghiệm thu giao cho tester

Các ca dưới đây bổ sung cho bộ test hiện có. Mỗi ca cần ghi commit, môi trường, dữ liệu vào, kết quả, bằng chứng và người xác nhận.

| Mã | Tình huống | Kết quả cần đạt |
| --- | --- | --- |
| T01 | Một dòng dài vượt ngân sách; nhiều tài liệu lớn. | Không mất phần đuôi; mọi request và bước merge trong giới hạn. |
| T02 | TXT rỗng; ảnh bị bỏ; PDF không trích được chữ. | Không gọi AI khi không còn phần đầu vào hỗ trợ; báo lý do. |
| T03 | Đổi nội dung giữ size/mtime; đổi model hoặc schema. | Đánh dấu cần cập nhật đúng; không sử dụng cache sai. |
| T04 | JSON sai schema; nguồn không tồn tại; đề thiếu lựa chọn. | Không công bố kết quả hợp lệ; sửa hữu hạn hoặc báo lỗi. |
| T05 | 301 buổi; chuyển vị trí thư viện. | Buổi cũ vẫn đọc/tải được; UUID không thay đổi. |
| T06 | Crash sau AI trả lời; restart lúc lỗi; hai đường chép lời. | Phục hồi job; không chạy lặp vô hạn, không vượt mức song song. |
| T07 | Hai lần đổi một key; mất response sau commit. | Chỉ một grant; retry đúng tài khoản trả kết quả cũ. |
| T08 | Webhook gửi lại; sai tiền; sai chữ ký; đến sai thứ tự. | Không cấp nhầm/trùng quyền; đối soát khôi phục đơn hợp lệ. |
| T09 | Gia hạn sớm; hủy; hoàn tiền; thu hồi thiết bị. | Đúng chính sách kỳ hạn; ledger và audit đầy đủ. |
| T10 | Offline; chỉnh giờ; lease hết hạn; server license lỗi. | Hành vi theo lease công bố; không mất dữ liệu, không hứa chống sửa client tuyệt đối. |
| T11 | Quota gần hết; hai phiên cùng lúc; worker cũ sống lại. | Không vượt số dư/suất; chỉ worker generation mới ghi nhận. |
| T12 | Đọc/xuất dữ liệu workspace khác; URL ID bị thay. | Bị từ chối ở backend; không lộ nội dung hay metadata. |
| T13 | Zoom phòng thật; quyền ghi bị rút; reconnect. | Đúng trạng thái, dừng đúng quyền, file nghe/xem được. |
| T14 | Hết đĩa; mất điện; update lỗi; restore máy mới. | Thông báo rõ; bảo toàn phần có thể phục hồi; rollback có kiểm chứng. |

### 15 Thứ tự triển khai và điều kiện bàn giao

| Đợt | Đầu việc và người phụ trách theo vai trò | Điều kiện chuyển bước |
| --- | --- | --- |
| AChất lượng | Dev AI sửa T01–T04; dev dữ liệu làm T05–T06; QA tái hiện và giữ regression tests. | Đóng lỗi có bằng chứng; chạy lại bộ test đang có. |
| BPilot local | Product chốt gói hỗ trợ và chính sách; backend làm đơn, key, lease; desktop thêm wizard và trang gói; QA T07–T10. | Mua thử → cấp quyền → gia hạn → hoàn/thu hồi hoạt động; khách tự cài được. |
| CBản họp | Dev AI thêm profile họp, nguồn dẫn chứng và xuất Word; product đánh giá cùng nhóm khách thử. | Biên bản và đầu việc đối chiếu được; người dùng sửa và xác nhận. |
| DCloud tùy chọn | Tech lead PoC RTMS; backend thêm workspace/quota; ops vận hành; QA T11–T14. | Xác nhận Zoom, chi phí và dữ liệu; kiểm chứng phòng thật trước bán tính năng cloud. |

Ước lượng để lập kế hoạch, chưa phải cam kết: A khoảng 5–8 ngày công; B khoảng 10–15; C khoảng 5–8; PoC và nền cloud D khoảng 15–25. Tổng 35–56 ngày công cho phạm vi nêu trên, chưa tính thời gian Zoom xét duyệt, mua chứng thư, hỗ trợ pilot và tích hợp ngoài. Cần chia ticket và ước lượng lại sau spike RTMS.

Các quyết định chủ sản phẩm cần chốt

Nhóm khách chính: học tập hay họp doanh nghiệp; chọn một nhóm để pilot trước.

Khách tự trả AI hay mua AI của bạn; dữ liệu nào rời máy khách và được lưu bao lâu.

Bán hỗ trợ/bảo trì bản local hay dịch vụ cloud; gói gồm những quyền và thiết bị nào.

Quy tắc hết hạn, đổi thiết bị, hoàn tiền, credit dư và thời gian dùng offline.

Phương án Zoom được xác nhận và người chịu trách nhiệm hồ sơ thử phòng thật.

Bộ hồ sơ developer phải giao sau triển khai

Mã và migration; API contract; cấu hình mẫu không có secret; báo cáo tests; log thử phòng thật đã ẩn dữ liệu; hướng dẫn release/rollback/restore; chính sách gói; runbook đối soát và xử lý đơn. Mọi PR thay đổi mã áp dụng AGENTS.md, cập nhật graph bằng tooling ghim và kiểm tra dashboard theo docs/WORKFLOW.md. [R15]

### 16 Biên bản kiểm tra và chứng cứ mã nguồn

Repository được đọc ở nhánh main và tag v2.2.0, commit 53decc9d4b95fc032f132c375f05960eb5e824a2. Đánh giá các nhánh khác hoặc thay đổi sau commit này cần một lần đối chiếu mới.

| Kiểm tra | Kết quả trong đợt rà soát |
| --- | --- |
| check_source.py | Đạt kiểm tra có sẵn của dự án; không phải cam kết đã quét hết mọi loại bí mật. |
| workflow_map.py check | Đạt; 82 file nguồn khớp snapshot. |
| JavaScript | web/app.js và web/study.js qua kiểm tra cú pháp. |
| Unit và integration | Đạt 54 tests Linux bằng dependencies cài riêng; Claude và Ollama dùng server giả lập. |
| Thử bổ sung không gọi mạng | 25 ký tự một dòng còn 10; hash không đổi khi nội dung cùng size/mtime đổi; TXT rỗng vẫn chạm lời gọi AI. |
| Zoom và AI thật | Chưa thực hiện trong đợt rà soát này; cần bộ hồ sơ tester theo điều kiện đã nêu. |
| Phạm vi thay đổi | Không sửa mã nguồn repository. Tài liệu này là đặc tả bàn giao phát triển. |

Lần chạy đầu thiếu dependencies, lần tiếp theo gặp cấu hình SOCKS của môi trường. Đã cài dependencies vào thư mục kiểm tra riêng và chạy các fake HTTP server trên loopback với proxy môi trường được tắt riêng cho tiến trình test. Không dùng khóa Zoom hoặc AI của người dùng.

Nguồn mã cố định theo commit

[R1 README và phạm vi sản phẩm](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/README.md)

[R2 Hồ sơ kiểm thử và giới hạn xác nhận](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/docs/VALIDATION.md)

[R3 API local và điểm gọi chức năng](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/server.py)

[R4 Quản lý worker và chép lời](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/runner.py)

[R5 Pipeline ôn tập và nhận diện thay đổi](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/study.py)

[R6 Cấu hình và lời gọi AI](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/ai_backend.py)

[R7 Chép lời và mốc thời gian](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/transcribe.py)

### 17 Nguồn tham chiếu và tài liệu triển khai

[R8a Worker ghi dữ liệu Linux](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/native/linux_bot.cpp)

[R8b Worker ghi dữ liệu Windows](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/native/bot.cpp)

[R9 Đường dẫn và phiên bản ứng dụng](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/paths.py)

[R10 Kiểm tra truy cập local](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/access_control.py)

[R11 Thư viện và giới hạn danh sách](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/src/library.py)

[R12 Quy trình CI và phát hành](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/.github/workflows/docker-release.yml)

[R13 Giấy phép của snapshot](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/LICENSE)

[R14 Sao lưu và vận hành](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/docs/OPERATIONS.md)

[R15a Quy tắc bảo trì repository](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/AGENTS.md)

[R15b Quy trình cập nhật bản đồ](https://github.com/Thequancute215-sys/cun-zoom/blob/53decc9d4b95fc032f132c375f05960eb5e824a2/docs/WORKFLOW.md)

Tài liệu nhà cung cấp đã đối chiếu ngày 23 tháng 10 năm 2026

[W1 Zoom Meeting SDK Linux và chính sách sử dụng](https://developers.zoom.us/docs/meeting-sdk/linux/)

[W2 Zoom OBF FAQ và ứng dụng legacy](https://developers.zoom.us/docs/meeting-sdk/obf-faq/)

[W3 Điều kiện bắt đầu RTMS](https://developers.zoom.us/docs/rtms/meetings/getting-started/)

[W4 Thêm RTMS vào ứng dụng](https://developers.zoom.us/docs/rtms/meetings/add-features/)

[W5 RTMS failover và reconnection](https://developers.zoom.us/docs/rtms/meetings/failover-reconnection/)

[W6 Nội dung giấy phép MIT tại Open Source Initiative](https://opensource.org/license/mit)

[W7 Webhook thông tin thanh toán payOS](https://payos.vn/docs/du-lieu-tra-ve/webhook/)

[W8 Danh sách và khả năng model Claude](https://platform.claude.com/docs/en/models/overview)

Thông số dịch vụ, model, scope và chính sách nhà cung cấp có thể thay đổi. Trước mỗi đợt release, đối chiếu lại tài liệu chính thức, thử bằng tài khoản được phép và ghim phiên bản đã kiểm chứng. Các thuật toán license, ledger và tổ chức công việc trong tài liệu là đề xuất thiết kế cho Cún Zoom, không phải chứng nhận của nhà cung cấp.

