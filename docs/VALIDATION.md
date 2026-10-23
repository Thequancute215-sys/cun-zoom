# Kiểm thử và giới hạn xác nhận

Các mức kiểm tra được phân biệt rõ:

1. **Source/unit/integration**: parser link, lịch định kỳ/hủy/múi giờ, mã hóa và lỗi khóa, HTTP Basic Auth, Host/Origin/token, tải ZIP đúng phạm vi.
2. **Docker smoke**: build Ubuntu x86-64, chạy non-root, giao diện thật, từ chối truy cập không đăng nhập, giữ cấu hình qua restart.
3. **Native SDK**: biên dịch với SDK Linux chính thức được cung cấp riêng và khởi tạo SDK không vào phòng.
4. **Phòng thật**: xác thực/OAuth/OBF, host nhận bot, cho quyền ghi, nói thử/chia sẻ slide, tải và nghe/xem file thực tế.

CI kiểm tra mức 1–2 trên Linux và Windows. Với Windows, CI còn kiểm tra mức 3 ở dạng nạp SDK (`--self-test` của gói exe) bằng SDK lấy từ kho riêng tư; archive SDK không được đăng công khai. Mức 3 của SDK Linux được kiểm tra riêng khi có gói SDK hợp lệ; chỉ ghi đạt khi có log biên dịch và init trả thành công. Mức 4 phải thử với phòng được phép của người cài; không suy từ SDK init hay thời gian đã chờ.

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

## Kết quả bản 2.1.0 (gộp Windows + Docker) — 22/10/2026 (Asia/Bangkok)

| Mức | Kết quả thực tế |
| --- | --- |
| Source/unit/integration | Đạt 30 tests trên Linux và cùng bộ tests trên Windows (`requirements-windows-lock.txt`); kiểm tra nguồn, bản đồ workflow và JavaScript đạt |
| Windows | Biên dịch `CunZoomBot.exe` với Windows Meeting SDK **7.2.1.49056** (SHA-256 archive `67ba466b38bdaa61df95b892398996d2a1c6db328b19a42ad814ec32d91dcb83`), đóng gói `CunZoom.exe` **không kèm SDK**; `--self-test` với SDK đặt ngoài exe đạt: `sdk_loadable`, `encryption_roundtrip`, `https_context`, `web_resources`, `native_status_consistent` đều `true`, `sdk_bundled` là `false` |
| Cài SDK trong ứng dụng | Với chính archive 7.2.1.49056 ở trên: chỉ chép `x64\bin` (155 tệp) vào thư mục `zoom-sdk`, trùng từng byte với runtime dùng khi build; cài lại thay bản cũ không để sót tệp. Tests tự động: từ chối gói không phải Windows x64 và đường dẫn ZIP không an toàn mà không đổi bản đã cài |
| Nâng cấp từ 1.x | Tests tự động: sao chép `.dpapi` sang tên mới, giữ nguyên file nguồn, không ghi đè kho 2.x, giữ thư mục bài giảng 1.x. Chưa thử trên máy Windows thật có dữ liệu 1.x |
| Docker | Build và smoke HTTP thật đạt trên CI và khi build lại cục bộ (non-root, đăng nhập, CSRF, mã hóa, dữ liệu qua restart) |
| SDK OAuth / phòng thật | **Chưa kiểm tra** trong 2.1.0 |

CI: [lần chạy kiểm tra](https://github.com/Thequancute215-sys/cun-zoom/actions/runs/39751797754) trên commit `13c8fd445cbd7c6ac195b630f9f30071ec6b0615`.

## Kết quả bản 2.2.0 (Ôn tập bằng AI) — 22/10/2026 (Asia/Bangkok)

| Mức | Kết quả thực tế |
| --- | --- |
| Source/unit/integration | Đạt 54 tests trên Linux. Gồm: SDK `anthropic` thật gửi tới server giả lập (kiểm tra `output_config.format`, `fallbacks: "default"` + beta header cho Opus/Sonnet, không fallback cho Haiku, cache, khối PDF/ảnh, báo lỗi từ chối/quá dài/khóa sai); Ollama giả lập (schema, thử lại không ảnh, mất kết nối); đọc DOCX/PPTX/TXT/PDF; pipeline buổi → môn → đề cương → đề thi → mục lục với AI giả lập; bộ đồng bộ chạy đúng thứ tự, không lặp việc lỗi, một lượt chép lời mỗi lúc; tải file lên (tạo buổi, thêm vào buổi, chặn loại file/tên môn/thiếu token) |
| Giao diện | Chạy thật trong Chromium: trang Ôn tập (hệ thống kiến thức, theo buổi, đề cương, đề thi có chấm trắc nghiệm), form tải lên, Cài đặt → AI, màn hình điện thoại |
| Docker | Build và smoke HTTP thật đạt khi build cục bộ; container nạp được `anthropic`, `pypdf` và module ôn tập |
| Gọi AI thật | **Chưa kiểm tra** với khóa Claude hay Ollama thật trong lần phát hành này; chất lượng ghi chú/đề phụ thuộc mô hình và bản chép lời |

### Chạy thật với Ollama sau phát hành 2.2.0 — 22/10/2026

Ollama 0.40.8 trên máy ảo Linux 4 nhân CPU, 15 GB RAM, không GPU; chạy qua HTTP API của ứng dụng (lưu cấu hình AI, Kiểm tra AI, tải tài liệu, đồng bộ tự động, tạo đề).

| Mô hình | Kết quả |
| --- | --- |
| `qwen2.5:3b` | Đi hết luồng: Kiểm tra AI (24 giây), tải TXT + DOCX, ghi chú 2 buổi, hệ thống kiến thức, đề cương, đề thi, mục lục; khoảng 12 phút. Nội dung chung chung, nhãn và nguồn hay sai: chỉ hợp để thử |
| `qwen2.5:7b` | Ghi chú buổi đúng và bám tài liệu (công thức, phân loại, ví dụ); 2 buổi + hệ thống kiến thức + đề cương khoảng 20 phút, đề thi khoảng 5–6 phút. Nhãn độ khó/loại ít phân biệt; đề thi có câu sai đáp án, cần đối chiếu |

Lỗi tìm ra và đã sửa: buổi chỉ có file không đọc được bị AI bịa nội dung từ tên buổi; một buổi lỗi chặn cập nhật hệ thống kiến thức và đề cương của cả môn; câu hỏi đề thi chỉ ghi số hoặc tên chủ đề, mô hình nhỏ soạn thiếu câu; link mục lục hỏng khi tên thư mục có dấu cách/dấu tiếng Việt. Chưa thử Claude API với khóa thật.
