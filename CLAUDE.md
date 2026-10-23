# Cún Zoom — điểm bắt đầu cho Claude Code

Đọc [AGENTS.md](AGENTS.md) trước khi sửa mã. Quy tắc Understand Anything và chốt bản đồ áp dụng cả cho Claude Code.

1. Đọc [đặc tả và bàn giao cuộc chat](docs/CHAT_HANDOVER.md): quyết định đã chốt, kết quả kiểm thử và việc chưa làm.
2. Đọc [tài khoản/bản quyền](docs/ACCOUNTS.md) để hiểu OTP, key một lần, thiết bị và triển khai Workers/D1.
3. Đọc [mục lục bàn giao](docs/HANDOVER.md), [workflow](docs/WORKFLOW.md) và nguồn thực hiện. Bản đồ không thay thế đọc mã.
4. Website hiện là cổng tài khoản/bản quyền; bài giảng vẫn nằm trên máy khách. Không biến một volume local thành SaaS nhiều khách.
5. Không coi deploy dry-run hoặc test provider giả lập là production đã hoạt động. Không giả định SDK, OAuth/OBF, phòng Zoom thật hoặc OTP thật đã được kiểm chứng.

Điểm vào chính: `accounts/worker.mjs`, `accounts/admin.mjs`, `accounts/configure-production.mjs`, `src/account_client.py`, `src/server.py`, `web/account.*`.

Không in/commit OTP, key, cookie/token phiên, API secret, SDK, DB khách hoặc dữ liệu học. Các cấu hình production sinh trong `accounts/.wrangler/` chỉ có địa chỉ/binding công khai và bị Git bỏ qua; secret phải nhập qua Cloudflare/GitHub secrets.

Trước khi tiếp tục phát hành: xử lý các khác biệt với tài liệu Word nêu trong bàn giao, đặc biệt đọc/xuất dữ liệu khi hết gói, dừng bản ghi khi mất quyền/mạng và chính sách offline. Không tự ghi các mục này là đã được chủ sản phẩm duyệt.
