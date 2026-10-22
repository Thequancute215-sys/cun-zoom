# Kiểm thử và giới hạn xác nhận

Các mức kiểm tra được phân biệt rõ:

1. **Source/unit/integration**: parser link, lịch định kỳ/hủy/múi giờ, mã hóa và lỗi khóa, HTTP Basic Auth, Host/Origin/token, tải ZIP đúng phạm vi.
2. **Docker smoke**: build Ubuntu x86-64, chạy non-root, giao diện thật, từ chối truy cập không đăng nhập, giữ cấu hình qua restart.
3. **Native SDK**: biên dịch với SDK Linux chính thức được cung cấp riêng và khởi tạo SDK không vào phòng.
4. **Phòng thật**: xác thực/OAuth/OBF, host nhận bot, cho quyền ghi, nói thử/chia sẻ slide, tải và nghe/xem file thực tế.

CI công khai kiểm tra mức 1–2. SDK không được phân phối trong CI công khai. Mức 3 được kiểm tra riêng khi có gói SDK hợp lệ; chỉ ghi đạt khi có log biên dịch và init trả thành công. Mức 4 phải thử với phòng được phép của người cài; không suy từ SDK init hay thời gian đã chờ.

## Kết quả bản 2.0.0 — 22/10/2026 (Asia/Bangkok)

| Mức | Kết quả thực tế |
| --- | --- |
| Source/unit/integration | Đạt 20 tests; kiểm tra JavaScript đạt |
| Docker | Build Ubuntu 22.04 x86-64 đạt; HTTP thật, UID 10001, đăng nhập, CSRF, mã hóa và dữ liệu qua restart đạt |
| Native SDK | Biên dịch/link và `InitSDK` đạt với Meeting SDK Linux x86-64 **7.1.5.4432**; output `{"state":"sdk_loaded","code":0,"amount":0}` |
| SDK OAuth / phòng thật | **Chưa kiểm tra** trong bản Docker; người cài cần thử tài khoản/OAuth/OBF, quyền ghi, âm thanh và slide thực tế |

Docker/source: [CI thành công](https://github.com/Thequancute215-sys/cun-zoom/actions/runs/39656651267), mã kiểm tra `9513c0d1fb6d35d068cb037d3f50adf20fbaf83d`. Quy trình phát hành chạy lại cùng nhóm kiểm tra trên commit phát hành.

SDK được cung cấp qua kho kiểm tra riêng tư, không xuất bản archive hoặc thư viện vào kho này. Bài kiểm tra native riêng đạt lúc **01:54:46 ngày 22/10/2026 UTC+7**. SHA-256 của archive chính thức đã dùng: `459561050c5f3291756fef612ad70406feffed7b3b4820ed5f6418444e8f7da3`.

Không dùng bản này cho buổi học quan trọng trước khi kiểm tra một phòng riêng được phép. Khởi tạo SDK không xác nhận quyền ứng dụng, OAuth, âm thanh hoặc slide trong một cuộc họp.
