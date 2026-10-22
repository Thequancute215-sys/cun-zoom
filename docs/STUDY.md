# Ôn tập bằng AI: hệ thống hoá, đề cương, đề thi thử

Trang **Ôn tập** biến bài giảng (ghi âm, ảnh slide) và tài liệu bạn tải lên thành:

- **Ghi chú từng buổi**: tóm tắt, kiến thức chia nhóm theo chủ đề, thuật ngữ, bài tập/hạn nộp, câu hỏi ôn tập, chỗ cần kiểm tra lại.
- **Hệ thống kiến thức của môn**: gộp mọi buổi, bỏ trùng lặp; mỗi mục có **loại** (khái niệm, công thức/định lý, quy trình, ví dụ, so sánh, ứng dụng, lưu ý), **mức độ liên quan** (cốt lõi → quan trọng → bổ trợ → tham khảo) và **độ khó** (cơ bản → trung bình → nâng cao), được sắp theo thứ tự đó; ghi rõ học ở buổi nào và các liên kết giữa khái niệm.
- **Đề cương ôn tập**: chương, ý trọng tâm (★), câu hỏi tự kiểm tra, trọng tâm thi, kế hoạch ôn.
- **Đề thi thử**: trắc nghiệm 4 lựa chọn có đáp án và giải thích, kèm tự luận có gợi ý chấm; chọn số câu và mức độ (cân bằng / thiên cơ bản / thiên nâng cao). Làm trắc nghiệm ngay trong ứng dụng và xem điểm.

AI chỉ dùng nội dung bạn cung cấp và có thể sai, nhất là khi bản chép lời nghe nhầm. Luôn đối chiếu với slide và giáo trình trước khi học thuộc.

## Mọi thứ tự đồng bộ

Khi bật **Tự đồng bộ** (Cài đặt → AI), mỗi khi có buổi ghi mới hoặc tài liệu mới:

1. Âm thanh/video được chép lời trên máy (mỗi lần một buổi, không chạy khi đang ghi). File bạn tải lên luôn được chép lời; các buổi ghi cũ chưa có bản chép lời chỉ được chép lời khi bật Tự đồng bộ, để máy không bận hàng giờ ngay sau khi nâng cấp.
2. Buổi đó được hệ thống hoá lại.
3. Hệ thống kiến thức của môn và đề cương được cập nhật.

Ứng dụng nhận ra thay đổi theo nội dung file, nên chỉ chạy lại phần thật sự đổi. Nếu một bước lỗi (hết hạn mức, mất mạng…), lỗi hiện ở danh sách môn và bước đó không tự thử lại cho tới khi có file mới hoặc bạn bấm **Đồng bộ lại**. Đề thi thử chỉ tạo khi bạn bấm.

## Thư mục được tạo

Tất cả nằm trong thư mục bài giảng (Cài đặt → Lưu trữ), dạng file thường đọc được bằng mọi trình soạn thảo:

```text
<thư mục bài giảng>/
├── 00_Tong_hop/Muc_luc.md                 mục lục mọi môn
└── <Tên môn>/
    ├── 00_Tong_hop_mon/
    │   ├── he_thong_kien_thuc.md / .json  hệ thống kiến thức của môn
    │   ├── de_cuong.md / .json            đề cương
    │   └── de_thi_thu/<ngày-giờ>.md/.json đề thi thử, đáp án ở cuối file .md
    └── <Buổi học>/
        ├── 01_Tai_lieu_goc/               âm thanh, ảnh slide, tai_lieu/ (file bạn tải lên)
        ├── 02_Tom_tat/he_thong_buoi.md     ghi chú buổi (+ bản chép lời, bản nháp)
        └── 03_Bai_tap_va_on_tap/
```

Các file trong `00_Tong_hop*` và `he_thong_buoi.*` do ứng dụng tạo lại được từ dữ liệu gốc; đừng sửa tay vì lần đồng bộ sau sẽ ghi đè. Muốn ghi chú riêng, tạo file khác trong `03_Bai_tap_va_on_tap/`.

## Tải tài liệu lên

Bấm **Tải tài liệu lên** ở trang Ôn tập, chọn môn (gõ tên mới để tạo môn), chọn **Buổi mới** hoặc một buổi đã có, rồi chọn file. Hỗ trợ:

| Loại | Đuôi | Cách xử lý |
| --- | --- | --- |
| PDF | .pdf | Claude đọc nguyên trang (cả hình, công thức); Ollama đọc phần chữ. PDF scan không có chữ cần Claude |
| Word, PowerPoint | .docx, .pptx | Đọc chữ, kể cả ghi chú dưới slide. File .doc/.ppt đời cũ: lưu lại thành .docx/.pptx hoặc PDF |
| Ảnh slide, ảnh chụp vở | .jpg, .png, .webp, .gif | Claude đọc ảnh (tối đa 5 MB mỗi ảnh); mô hình Ollama chỉ chữ sẽ bỏ qua ảnh |
| Chữ | .txt, .md | Đọc trực tiếp |
| Âm thanh, video | .mp3, .m4a, .wav, .mp4, .mkv, .mov, .webm… | Chép lời trên máy rồi hệ thống hoá. Cần tải bộ chép lời một lần (Cài đặt → Lưu trữ) |

Tối đa 2 GB mỗi file. File được lưu nguyên vẹn trong `01_Tai_lieu_goc/tai_lieu/` của buổi; ứng dụng không chạy hay mở nội dung file.

## Chọn bộ AI

Vào **Cài đặt → AI**.

### Claude API (chất lượng tốt nhất)

1. Tạo tài khoản tại [console.anthropic.com](https://console.anthropic.com/), nạp tiền (trả theo lượng dùng).
2. **API Keys → Create Key**, sao chép khóa (bắt đầu bằng `sk-ant-`).
3. Trong Cún Zoom: Bộ AI = **Claude API**, dán khóa, chọn mô hình, bấm **Lưu cấu hình AI** rồi **Kiểm tra AI**.

Khóa được mã hóa trên máy, không bao giờ hiển thị lại. Nội dung bài giảng được gửi tới Anthropic để xử lý.

| Mô hình | Khi nào dùng | Chi phí ước tính mỗi buổi 90 phút* |
| --- | --- | --- |
| Claude Opus 5.5 (mặc định) | Chất lượng cao nhất, đọc slide/PDF tốt | khoảng 0,5–1 USD |
| Claude Sonnet 5.5 | Cân bằng | khoảng 0,25–0,5 USD |
| Claude Haiku 5.5 | Rẻ nhất, phù hợp ôn nhanh | dưới 0,05 USD |

\*Gồm ghi chú buổi, cập nhật hệ thống kiến thức và đề cương; đề thi tính thêm khi tạo. Chỉ là ước tính; xem chi phí thật trong console của Anthropic. Muốn tiết kiệm: tắt Tự đồng bộ và bấm **Đồng bộ lại** khi cần, hoặc dùng Sonnet/Haiku.

### Ollama (miễn phí, chạy trên máy)

1. Cài Ollama từ [ollama.com](https://ollama.com/download).
2. Tải mô hình hỗ trợ tiếng Việt, ví dụ `ollama pull qwen2.5:14b` (cần khoảng 16 GB RAM; máy yếu hơn thử `qwen2.5:7b`).
3. Trong Cún Zoom: Bộ AI = **Ollama**, tên mô hình như trên, bấm **Kiểm tra AI**.

Với bản Docker, đặt địa chỉ `http://host.docker.internal:11434` (mặc định sẵn) và cho Ollama nhận kết nối từ container: đặt biến môi trường `OLLAMA_HOST=0.0.0.0` cho Ollama rồi khởi động lại nó. Chỉ làm vậy trên máy không mở cổng 11434 ra Internet.

Mô hình chạy trên máy cho kết quả kém hơn Claude, không đọc được ảnh slide nếu không phải mô hình thị giác, và bài dài được chia nhỏ rồi gộp lại nên chậm hơn.

## Xử lý lỗi

| Hiện tượng | Cách xử lý |
| --- | --- |
| "Chưa bật AI" | Cài đặt → AI, chọn Claude hoặc Ollama |
| "Khóa API Claude không hợp lệ" | Tạo khóa mới trong console, dán lại |
| "Claude đang giới hạn tốc độ hoặc đã hết hạn mức" | Nạp thêm tiền hoặc chờ vài phút rồi bấm Đồng bộ lại |
| "Claude không xử lý nội dung này" | Bộ lọc an toàn từ chối; thử bớt tài liệu của buổi đó hoặc đổi mô hình |
| "Không kết nối được Ollama" | Mở Ollama; với Docker kiểm tra `OLLAMA_HOST=0.0.0.0` |
| "Ollama chưa có mô hình" | Chạy lệnh `ollama pull <tên mô hình>` được hiển thị |
| Buổi "Đang chờ chép lời" lâu | Bộ chép lời chạy trên CPU, khoảng bằng độ dài bản ghi; không chạy khi bot đang ghi |
| Ghi chú báo "Chưa có bộ chép lời" | Cài đặt → Lưu trữ → Tải bộ chép lời; ghi chú tự cập nhật sau đó |
