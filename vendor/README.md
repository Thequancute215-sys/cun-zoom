# SDK riêng của người cài

Docker: tải Zoom Meeting SDK Linux x86-64 chính thức, giải nén nội dung vào vendor/zoom-linux. Xem docs/INSTALL.md. SDK không được commit, đưa vào image hoặc release công khai.

Windows desktop: người dùng cài SDK Windows của mình trong ứng dụng (Cài đặt → Kết nối → Cài Zoom SDK); CunZoom.exe không kèm SDK. CI lấy Windows Meeting SDK từ kho SDK riêng tư chỉ để biên dịch và tự kiểm tra (xem docs/WINDOWS.md). Build trên máy: scripts/prepare_sdk.py <archive.zip> rồi scripts/build_native.py, scripts/build.py; SDK được giải nén vào build/ và vendor/zoom, không commit. Bản Docker không dùng Windows SDK.