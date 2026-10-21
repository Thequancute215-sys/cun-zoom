# Kiểm thử và giới hạn xác nhận

Các mức kiểm tra được phân biệt rõ:

1. **Source/unit/integration**: parser link, lịch định kỳ/hủy/múi giờ, mã hóa và lỗi khóa, HTTP Basic Auth, Host/Origin/token, tải ZIP đúng phạm vi.
2. **Docker smoke**: build Ubuntu x86-64, chạy non-root, giao diện thật, từ chối truy cập không đăng nhập, giữ cấu hình qua restart.
3. **Native SDK**: biên dịch với SDK Linux chính thức được cung cấp riêng và khởi tạo SDK không vào phòng.
4. **Phòng thật**: xác thực/OAuth/OBF, host nhận bot, cho quyền ghi, nói thử/chia sẻ slide, tải và nghe/xem file thực tế.

CI công khai kiểm tra mức 1–2. SDK không được phân phối trong CI công khai. Mức 3 được kiểm tra riêng khi có gói SDK hợp lệ; chỉ ghi đạt khi có log biên dịch và init trả thành công. Mức 4 phải thử với phòng được phép của người cài; không suy từ SDK init hay thời gian đã chờ.

Trạng thái phát hành ban đầu: đang hoàn tất xác minh Docker/native. Xem ghi chú release và Actions cho kết quả cập nhật; không dùng bản thử cho buổi học quan trọng trước khi thử phòng riêng.
