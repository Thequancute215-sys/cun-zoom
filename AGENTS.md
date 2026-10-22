# Cún Zoom — quy tắc duy trì bản đồ dự án

Áp dụng cho mọi thay đổi trong repository này. Đây là yêu cầu lâu dài của chủ dự án.

1. Trước khi sửa, đọc `docs/WORKFLOW.md`, `.ua/domain-graph.json` và các file thực hiện luồng liên quan. Không suy ra chức năng từ tên file hoặc sơ đồ cũ.
2. Dùng skill **understand-domain** và **understand-dashboard** từ https://github.com/Thequancute215-sys/understand-anything để hệ thống hóa mọi bản cập nhật. Phiên bản đã kiểm tra được ghim trong `.ua/tooling.json`. Không thay bằng một sơ đồ tự vẽ không đối chiếu nguồn.
   Skill **workflow** tại `skills/workflow/SKILL.md` đóng gói quy tắc này để dùng lại; áp dụng cùng hai skill nền trên. Mục lục tài liệu bàn giao là `docs/HANDOVER.md`.
3. Sau thay đổi, gọi skill `understand-domain --full` (quét mới thay vì suy ra từ graph cũ): chạy bộ trích ngữ cảnh theo hướng dẫn của skill, giao phân tích domain theo `agents/domain-analyzer.md`, rồi đọc lại các file bị ảnh hưởng. Giữ graph ở tiếng Việt, ID ASCII, đường dẫn tương đối và số dòng thật.
4. Lưu kết quả phân tích đã rà vào `.ua/intermediate/domain-analysis.json`. Chạy lệnh `refresh` trong `docs/WORKFLOW.md`: công cụ dùng validator thật của Understand Anything, tái tạo bản đồ file và trang workflow, rồi ghi dấu vân tay nguồn. Không chỉ cập nhật dấu vân tay để làm CI xanh khi chưa rà graph.
5. Chạy `python scripts/workflow_map.py check` cùng các kiểm tra phù hợp thay đổi. Commit/publish graph và nguồn trong cùng lần bàn giao. CI từ chối bản đồ thiếu hoặc lệch nội dung nguồn; không tắt kiểm tra này để bỏ qua lỗi.
6. Dùng dashboard để kiểm tra luồng chính và mở phần chi tiết ít nhất một bước. `docs/WORKFLOW.md` là bản đọc nhanh trên GitHub; hai graph JSON là dữ liệu dùng chung cho dashboard và bản đọc nhanh.
7. Không đưa SDK, mật khẩu, iCal riêng tư, token, log, nội dung buổi học hoặc đường dẫn cá nhân vào graph, ảnh chụp công khai hay Git. `.ua/intermediate/` chỉ là dữ liệu tạm, không commit.
8. Sơ đồ phải phân biệt đúng trạng thái: Calendar chỉ nhắc/mở link qua giao diện; ghi cần thao tác và quyền Zoom/host. SDK Init thành công không chứng minh vào phòng/ghi thành công. RTMS chưa có. Bản Windows (trước ở repo `AI-Zoom`) đã được gộp vào repo này từ 2.1.0; `AI-Zoom` chỉ còn là kho lưu trữ và kho SDK riêng tư. Không nhập lịch sử, cấu hình, SDK hay header SDK của nó vào repo công khai này.

Đây là quy trình cho tác nhân và người bảo trì, kèm chốt kiểm tra CI. `autoUpdate: true` không tự tạo một tiến trình AI chạy nền trong Codex.
