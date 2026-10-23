# Cún Zoom 2.2.1 · Sửa lỗi Ôn tập và tăng cường bảo mật

Bản sửa lỗi sau khi chạy thật trang Ôn tập với Ollama (`qwen2.5:3b` và `qwen2.5:7b`) và sau một lượt rà soát bảo mật toàn bộ mã nguồn.

- **Không còn ghi chú bịa:** buổi chỉ có file không đọc được (file hỏng, PDF scan khi dùng Ollama) giờ báo lỗi kèm tên file thay vì để AI tự viết bài từ tên buổi. Buổi chỉ có ảnh mà mô hình Ollama không đọc được ảnh cũng báo lỗi, không đoán.
- **Một buổi lỗi không chặn cả môn:** hệ thống kiến thức và đề cương vẫn cập nhật từ các buổi khác; lỗi của buổi đó vẫn hiện kèm tên buổi cho tới khi bạn sửa file.
- **Đề thi rõ hơn:** câu hỏi luôn có đề bài (trước đây mô hình nhỏ đôi khi chỉ ghi số câu hoặc tên chủ đề); thiếu câu thì tự hỏi AI thêm một lần. Tạo đề không còn thử lại buổi đang lỗi.
- **Mục lục:** link tới ghi chú mở được cả khi tên môn/buổi có dấu cách và dấu tiếng Việt.
- **Không tốn tiền Claude khi đang ghi:** trong lúc bot còn ghi một buổi, Ôn tập chờ buổi kết thúc rồi mới hệ thống hoá môn đó một lần (trước đây mỗi slide mới có thể làm nó chạy lại).
- **Chép lời:** file âm thanh/video im lặng không bị chép lại mãi; tiến trình chép lời bị dừng đột ngột được ghi là lỗi thay vì chờ 6 giờ rồi chạy lại; mỗi file chỉ đọc tối đa 3 giờ âm thanh. Bản Docker chép lời lại được với thư viện `av` mới.
- **Bảo mật:**
  - Word/PowerPoint được đọc theo luồng, có giới hạn tổng dung lượng và số chữ, không nhận DTD. File được dựng để làm đầy bộ nhớ nay chỉ còn là một cảnh báo.
  - Câu trả lời từ Ollama có giới hạn kích thước và thời gian.
  - Bất kỳ lỗi xử lý nào cũng được ghi nhớ, không lặp lại mỗi 30 giây.
  - Ghi chú `.md` không còn để AI chèn ảnh hay HTML tự tải từ web.
  - Link Zoom chứa dấu `\` bị từ chối.
  - Trên Windows, trang ứng dụng chỉ mở từ cửa sổ Cún Zoom, nên tài khoản Windows khác trên cùng máy không đọc được khóa phiên. Cổng ứng dụng không cho tiến trình khác dùng chung.
  - Kết nối HTTP bỏ ngỏ tự đóng sau 60 giây.
  - Lọc thẻ HTML trong mô tả sự kiện lịch nay chạy trong thời gian tuyến tính.
- Hướng dẫn ôn tập ghi rõ: mô hình dưới 7B chỉ nên dùng để thử. Kết quả chạy thật ở [phạm vi kiểm thử](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/VALIDATION.md).

Dữ liệu và cấu hình 2.2.0 dùng tiếp, không cần làm gì thêm.

---

# Cún Zoom 2.2.0 · Ôn tập bằng AI

- **Trang Ôn tập:** hệ thống hoá từng buổi và cả môn, sắp kiến thức theo nhóm chủ đề, mức độ liên quan (cốt lõi → tham khảo) và độ khó (cơ bản → nâng cao); đề cương có ý trọng tâm; đề thi thử trắc nghiệm + tự luận, làm và chấm trắc nghiệm ngay trong app.
- **Tải tài liệu lên:** PDF, Word (.docx), PowerPoint (.pptx), ảnh slide/vở, TXT/MD, âm thanh/video (chép lời trên máy). Vào buổi đã có hoặc tạo buổi mới.
- **Tự đồng bộ:** buổi mới hoặc tài liệu mới → chép lời → ghi chú buổi → hệ thống kiến thức → đề cương. Thư mục tổng `00_Tong_hop` và `00_Tong_hop_mon` trong thư mục bài giảng.
- **Chọn AI:** Claude API bằng khóa của bạn (Opus 5.5 mặc định, Sonnet 5.5, Haiku 5.5) hoặc Ollama chạy trên máy. AI tắt cho tới khi bạn bật; khóa được mã hóa trên máy.
- Release kèm hướng dẫn Windows, Docker và ôn tập (`HUONG-DAN-*.md`).

Kiểm tra trước khi học: AI có thể sai, đặc biệt khi bản chép lời nghe nhầm. Xem [hướng dẫn ôn tập](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/STUDY.md).

---

# Cún Zoom 2.1.0 · Windows + Docker

Gộp bản Windows (repo `AI-Zoom`, 1.0.0 – 1.1.1) vào repo này. Một mã nguồn, một quy trình kiểm tra, một Release gồm `CunZoom.exe` và image Docker.

- **Windows:** `CunZoom.exe` được build lại trên CI từ mã hiện tại (giao diện 1.1 + các sửa lỗi của 2.0.0) và tự kiểm tra trước khi đăng. Đọc [hướng dẫn cài đặt từng bước](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/WINDOWS.md#cài-đặt-từng-bước).
- **Zoom SDK không còn nằm trong exe.** Tải Zoom Meeting SDK Windows 7.2.1.49056 từ Zoom Marketplace và cài một lần trong **Cài đặt → Kết nối → Cài Zoom SDK (.zip)**. Người nâng cấp từ 1.x cũng cần làm bước này.
- **Nâng cấp từ 1.x giữ dữ liệu:** dùng tiếp thư mục dữ liệu và thư mục bài giảng cũ, sao chép (không xóa) `quyen_zoom.dpapi`/`calendar.dpapi` sang tên mới, dùng lại bộ chép lời đã tải.
- Giao diện hiển thị đúng hành vi theo nền tảng: Windows tự mở link lớp và thu gọn xuống khay; Docker chuyển link tới giao diện đang mở.
- Docker không đổi chức năng so với 2.0.0; image `ghcr.io/thequancute215-sys/cun-zoom:2.1.0`.

Chưa kiểm tra OAuth/ghi trong phòng Zoom thật của bản 2.1.0; thử với phòng được phép trước buổi học quan trọng. Xem [phạm vi kiểm thử](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/VALIDATION.md).

---

# Cún Zoom 2.0.0 · Docker Linux

Bản mã nguồn mở MIT, có Docker Linux x86-64 và giao diện tiếng Việt.

Module Meeting SDK cần quyền/phê duyệt phù hợp của Zoom. Tài liệu Zoom hiện hướng bot mới sang RTMS; bản này chưa tích hợp RTMS. Không hứa hỗ trợ mọi tài khoản hoặc tự vào lớp trước người cấp OBF.

- Đọc lịch Google iCal, lọc môn, nhắc lịch, chuẩn bị link phòng.
- Bộ ghi native Linux dùng Zoom Meeting SDK do người cài cung cấp riêng; ghi WAV và ảnh màn hình chia sẻ sau khi Zoom cấp quyền.
- Chép lời local, trích ý dạng nháp, thư viện và tải ZIP từng buổi.
- Đăng nhập local bằng mật khẩu ngẫu nhiên; cấu hình mã hóa, chạy non-root, volume giữ dữ liệu qua cập nhật.
- SDK, Client Secret, token, lịch và bản ghi cá nhân không nằm trong image/source/release.

**Bắt đầu tại [hướng dẫn cài đặt](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/INSTALL.md)**, sau đó làm theo [cấu hình Zoom và Calendar](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/ZOOM_AND_CALENDAR.md).

Image: `ghcr.io/thequancute215-sys/cun-zoom:2.0.0`. Có thể tự build bằng `docker compose up -d --build` từ source công khai.

Đã đạt 20 tests, Docker HTTP smoke/restart và biên dịch + khởi tạo SDK Linux 7.1.5.4432 (`sdk_loaded`, code `0`). Chưa kiểm tra OAuth/ghi trong phòng Zoom thật của bản Docker; cần thử phòng được phép trước khi dùng cho lớp chính thức.

Xem [phạm vi kiểm thử](https://github.com/Thequancute215-sys/cun-zoom/blob/main/docs/VALIDATION.md). Kiểm tra SDK không thay thế thử nghiệm ghi trong phòng thật được phép. Bot cần OBF và quyền host; đóng tab Docker không tự mở Zoom trên host, link nhắc học xuất hiện khi giao diện đang mở.
