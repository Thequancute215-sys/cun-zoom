---
name: workflow
description: Dựng và duy trì bản đồ dự án bằng Understand Anything khi người dùng gọi /workflow, yêu cầu hệ thống hóa luồng, hoặc cập nhật dự án đã áp dụng quy tắc này. Giữ graph, giải thích cơ chế, mã nguồn và bàn giao nhất quán.
---

# Workflow

Dùng repo [Thequancute215-sys/understand-anything](https://github.com/Thequancute215-sys/understand-anything) để duy trì bản đồ đọc được và truy được về nguồn. Khi một dự án đã áp dụng quy tắc này, mỗi lần cập nhật dự án phải rà và cập nhật bản đồ trong cùng lần bàn giao.

## Xác định dự án và công cụ

- Xác định repository đích từ yêu cầu, Git remote và AGENTS.md; không mặc định mọi yêu cầu đều thuộc Cún Zoom. Với Cún Zoom, đọc [references/cun-zoom.md](references/cun-zoom.md).
- Đọc AGENTS.md, bản đồ và tài liệu hiện có trước khi sửa. Ưu tiên `.understand-anything/` nếu dự án đã dùng thư mục legacy, nếu không dùng `.ua/`.
- Đọc skill `understand-domain` và `understand-dashboard` đã cài. Khi cần cả kiến trúc/call graph đầy đủ, đọc thêm `understand`. Nếu thiếu, lấy đúng skill từ repo được chỉ định; không tự thay bằng công cụ khác. Đọc hướng dẫn hiện hành trước khi thực thi.
- Tôn trọng phiên bản/commit công cụ trong `.ua/tooling.json` nếu có. Chỉ đổi phiên bản công cụ khi thực sự cần và ghi lại thay đổi; không tải một bản mới mỗi lượt.

## Dựng và cập nhật bản đồ

1. Đọc nguồn, cấu hình, điểm vào và kiểm thử liên quan để hiểu điều kiện, trạng thái, lỗi và dữ liệu đi qua mỗi bước. Phân biệt chức năng có trong mã với chức năng đã kiểm thử thực tế.
2. Dùng `understand-domain --full` khi nguồn thay đổi để quét mới, tránh suy diễn từ graph cũ. Bộ `extract-domain-context.py` chỉ thu nguyên liệu, không phải kết quả phân tích. Thực hiện phân tích domain theo `agents/domain-analyzer.md` của công cụ, gồm việc giao tác nhân phân tích như skill yêu cầu. Không suy ra một HTTP endpoint là không tồn tại chỉ vì bộ dò không nhận ra cách dispatch của dự án.
3. Viết tiếng Việt, ID ASCII ổn định; giữ ba cấp miền → luồng → bước. Ghi trigger, điều kiện/ràng buộc và đường dẫn tương đối tới mã thật. Chỉ thêm luồng có nguồn chứng minh; không áp một số lượng miền/luồng cố định cho mọi dự án.
4. Giữ riêng graph nghiệp vụ và graph kiến trúc. Ghi rõ độ chi tiết của graph kiến trúc: cấp file/import hay toàn bộ hàm/call graph. Không gọi một bản đồ cấp file là đã phân tích toàn bộ mã.
5. Kiểm tra bằng validator thực của Understand Anything, kiểm tra đường dẫn/số dòng, quan hệ cha–con và thứ tự bước. Không chấp nhận việc validator âm thầm loại node/cạnh quan trọng. Mở dashboard, kiểm tra một luồng liên quan thay đổi và phần chi tiết của một bước; sửa bất nhất trước khi bàn giao.

## Đồng bộ tài liệu và GitHub

- Duy trì một trang workflow đọc nhanh trên GitHub, liên kết tới graph và mã thực hiện. Sinh phần liệt kê bước/diagram từ graph nếu có thể; tránh giữ nhiều bản sao thủ công rồi để chúng lệch nhau.
- Tài liệu bàn giao phải chỉ ra nơi tìm mã nguồn, cách cài/chạy/cấu hình, giải thích cơ chế, cách kiểm tra, giới hạn/chưa kiểm chứng, cách cập nhật và khôi phục. Cập nhật tài liệu sẵn có hoặc thêm mục lục khi cần; không tạo một bộ tài liệu trùng lặp ở mỗi lượt.
- Với repo đã có kiểm tra độ mới bản đồ, chạy kiểm tra đó. Với dự án mới cần quy tắc lâu dài, ghi yêu cầu vào AGENTS.md và thêm chốt CI phù hợp. Dấu vân tay phát hiện nguồn thay đổi, không thay thế việc phân tích ý nghĩa. Không chỉ đổi snapshot hoặc ngày phân tích để làm CI đạt.
- Đưa nguồn thay đổi, graph, giải thích cơ chế và tài liệu liên quan lên đúng GitHub repo trong phạm vi người dùng đã yêu cầu/cho phép. Không tự công khai repo riêng, đổi quyền chia sẻ hoặc phát hành một phiên bản phần mềm chỉ vì đang dùng skill.
- Không commit bí mật, URL lịch riêng tư, dữ liệu học/ghi âm, SDK/binary không được phân phối, log hay dữ liệu tạm. Giữ mã nguồn công khai và dữ liệu vận hành riêng biệt. Xóa đúng các tệp intermediate do lượt phân tích tạo ra sau khi đã lưu kết quả hợp lệ.

## Kết quả bàn giao

Nêu ngắn: bản đồ đã đổi gì; link GitHub tới workflow, mục lục bàn giao và nguồn; trạng thái kiểm tra thực tế; phần còn thiếu. Khi dùng dashboard local, chia sẻ URL đầy đủ có token do viewer tạo, giữ token ngoài Git. Không mô tả `autoUpdate: true` là một tiến trình AI tự chạy nền hoặc khẳng định mọi tài liệu đã lên GitHub nếu mới lưu ở máy.
