# Bàn giao Cún Zoom

Repo hiện hành: [Thequancute215-sys/cun-zoom](https://github.com/Thequancute215-sys/cun-zoom). Tài liệu và mã ứng dụng của cả bản Windows (`CunZoom.exe`) và bản Docker nằm trong repo này; người khác có thể clone, đọc cơ chế và tự cài theo hướng dẫn. Không cần các tệp bàn giao trong lịch sử chat để đọc hoặc cài bản công khai.

## Tìm đúng tài liệu

| Cần làm gì | Nguồn |
| --- | --- |
| Hiểu chức năng và giới hạn | [README](../README.md) |
| Tiếp tục đúng trạng thái cuộc chat này | [CHAT_HANDOVER](CHAT_HANDOVER.md), [CLAUDE.md](../CLAUDE.md) |
| Bán bản thương mại: OTP, key một lần, quản lý thiết bị và triển khai website | [ACCOUNTS](ACCOUNTS.md) |
| Ôn tập bằng AI, tải tài liệu, cấu trúc thư mục tổng hợp | [STUDY](STUDY.md) |
| Dùng, nâng cấp từ 1.x hoặc build `CunZoom.exe` | [WINDOWS](WINDOWS.md) |
| Cài Docker, SDK và mở giao diện | [INSTALL](INSTALL.md) |
| Cấp quyền Zoom và nối Google Calendar | [ZOOM_AND_CALENDAR](ZOOM_AND_CALENDAR.md) |
| Đọc luồng hoạt động từng bước | [WORKFLOW](WORKFLOW.md), [graph nghiệp vụ](../.ua/domain-graph.json) |
| Hiểu các thành phần mã và cách chúng nối nhau | [DEVELOPMENT](DEVELOPMENT.md), [graph cấp file](../.ua/knowledge-graph.json) |
| Sử dụng, sao lưu, khôi phục, cập nhật, xử lý lỗi | [OPERATIONS](OPERATIONS.md) |
| Xem đã kiểm tra gì và chưa kiểm tra gì | [VALIDATION](VALIDATION.md) |
| Xem bản phát hành | [Releases](https://github.com/Thequancute215-sys/cun-zoom/releases), [release notes](RELEASE_NOTES.md) |
| Xem quy tắc bảo trì bản đồ | [AGENTS](../AGENTS.md), [công cụ được ghim](../.ua/tooling.json) |
| Cài lại hoặc dùng skill `/workflow` | [SKILL.md](../skills/workflow/SKILL.md), [hướng dẫn riêng cho dự án](../skills/workflow/references/cun-zoom.md) |

## Mã nguồn và kiểm tra

- [src/](../src/): API, OAuth, vault, lịch, quản lý worker, chép lời và thư viện.
- [native/](../native/): mã worker; `linux_bot.cpp` là bộ ghi Linux, `bot.cpp` là nhánh desktop Windows.
- [web/](../web/): toàn bộ giao diện, font và tài nguyên local.
- [scripts/](../scripts/): biên dịch, khởi động container, kiểm tra nguồn, kiểm tra bản đồ và smoke test.
- [tests/](../tests/): kiểm tra tự động; [workflow CI](../.github/workflows/docker-release.yml) chạy kiểm tra trước build/phát hành.
- [Dockerfile](../Dockerfile), [Compose](../compose.yaml), các `requirements*.txt`: công thức build/chạy và phụ thuộc.

Luồng chính: trình duyệt → API có xác thực → cấu hình mã hóa/nguồn lịch/worker theo chức năng. Worker gửi trạng thái và dữ liệu thực nhận; buổi có âm thanh mới kích hoạt chép lời. Frontend đọc trạng thái và thư viện qua API. Chi tiết điều kiện vào phòng, quyền ghi, dừng và lỗi có trong WORKFLOW và mã liên kết.

Đọc nguồn và chạy `python scripts/workflow_map.py check` trước khi dựa vào graph. Khi sửa, dùng Understand Anything để rà lại graph, tài liệu và snapshot; không chỉ đổi snapshot cho qua CI. `/workflow` đóng gói quy tắc này thành skill, không thay thế ba skill nền của Understand Anything và không tự tạo tác vụ AI chạy nền.

## Những thứ được giữ ngoài repo công khai

Archive SDK Zoom (điều khoản riêng), thông tin đăng nhập, nguồn iCal riêng tư, khóa mã hóa, dữ liệu volume, file âm thanh và slide của buổi học không được đưa lên GitHub. Không bản phát hành nào chứa Zoom SDK: người dùng Windows tự tải SDK Windows và cài bằng nút **Cài Zoom SDK (.zip)** trong ứng dụng; người dùng Docker tự đặt SDK Linux vào `vendor/zoom-linux`. CI chỉ dùng SDK từ kho riêng tư để biên dịch và tự kiểm tra. Mỗi người tự cấu hình ứng dụng Zoom của mình. Repo Windows cũ `AI-Zoom` được giữ làm kho lưu trữ (lịch sử 1.x) và kho SDK cho CI; cần đặt ở chế độ riêng tư. Mã Windows hiện hành nằm ở repo này; lịch sử và cấu hình riêng của `AI-Zoom` không được chép sang.

Graph mô tả cơ chế đã thấy trong nguồn, không phải bằng chứng ghi thành công. Bản Windows đã kiểm tra tests và self-test gói exe (SDK nạp được); bản Docker đã kiểm tra source/HTTP/container và khởi tạo SDK. OAuth/OBF và ghi phòng thật của 2.x còn cần thử trong phòng được phép. Kết quả và phiên bản SDK cụ thể nằm trong VALIDATION.
