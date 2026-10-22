# Áp dụng cho Cún Zoom

- Repo công khai hiện hành: https://github.com/Thequancute215-sys/cun-zoom
- Mục lục bàn giao: `docs/HANDOVER.md`; bản đọc nhanh: `docs/WORKFLOW.md`.
- Quy tắc: `AGENTS.md`. Provenance công cụ: `.ua/tooling.json`.
- Graph nghiệp vụ: `.ua/domain-graph.json`; kiến trúc cấp file/import: `.ua/knowledge-graph.json`.
- Chốt nội dung: `.ua/source-snapshot.json` và bước kiểm tra trong `.github/workflows/docker-release.yml`.

## Quy trình đã có

Chạy bộ trích ngữ cảnh và phân tích mới theo skill `understand-domain --full`, lưu kết quả đã rà vào `.ua/intermediate/domain-analysis.json`. Sau đó, từ root của repo:

```text
python scripts/workflow_map.py refresh --plugin-root <checkout-understand-anything>/understand-anything-plugin --domain-graph .ua/intermediate/domain-analysis.json --review-note "Thay doi luong va cac nguon da doi chieu"
python scripts/workflow_map.py check
```

`refresh` kiểm tra checkout công cụ có đúng commit ghim, gọi validator upstream, sinh graph cấp file, trang workflow và snapshot. `check` chạy trong CI không cần mô hình AI hoặc dependency Node của plugin. Đọc `docs/DEVELOPMENT.md` để chạy kiểm tra phù hợp; dùng `understand-dashboard` để xác minh trực quan. Xóa dữ liệu intermediate theo skill sau khi lưu graph thành công.

## Điều phải giữ đúng

- Docker Calendar đọc iCal, nhắc và chuyển link tới giao diện đang mở; không tự vào phòng hay tự bắt đầu ghi.
- Ghi cần xác nhận của người dùng, kiểm tra SDK và quyền Zoom/OBF/host tương ứng. Đọc giới hạn hiện hành trong `docs/ZOOM_AND_CALENDAR.md` và `docs/VALIDATION.md`; không coi InitSDK thành công là đã ghi được phòng thật.
- Bản đồ hiện tại là phân tích domain cùng overview cấp file, không phải call graph của mọi hàm. RTMS chưa được triển khai ở mốc tạo skill; kiểm tra mã hiện tại trước khi nhắc lại giới hạn này ở các lần sau.
- Repo Windows cũ `Thequancute215-sys/AI-Zoom` là riêng tư, tách với repo Docker công khai. Không nhập lịch sử/cấu hình/SDK của nó sang repo công khai, không dừng ứng dụng đang chạy để mở dashboard.
- Khi thêm file nguồn hoặc tài liệu có vai trò mới, cập nhật mô tả/lớp kiến trúc trong `scripts/workflow_map.py` nếu cần; đừng để mô tả mặc định sai loại file. Nội dung graph không chứa dữ liệu buổi học, khóa hoặc đường dẫn cá nhân.

## Cài lại skill

Skill được lưu tại `skills/workflow/` trong repo công khai. Sao chép nguyên thư mục này vào thư mục skills của Codex, thường là `~/.codex/skills/workflow/`; không sao chép SDK, cấu hình hay toàn bộ repo vào thư mục skill. Ba skill nền `understand`, `understand-domain`, `understand-dashboard` lấy từ repo Understand Anything được chỉ định, theo hướng dẫn cài của nó.
