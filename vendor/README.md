# SDK riêng của người cài

Docker: tải Zoom Meeting SDK Linux x86-64 chính thức, giải nén nội dung vào vendor/zoom-linux. Xem docs/INSTALL.md. SDK không được commit, đưa vào image hoặc release công khai.

Windows desktop: người phát triển có thể tự cung cấp Windows Meeting SDK và dùng scripts/prepare_sdk.py / scripts/build_native.py. Bản Docker không dùng Windows SDK.