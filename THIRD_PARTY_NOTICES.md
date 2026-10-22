# Third-party components

The application source is licensed under MIT; see [LICENSE](LICENSE).

## Fonts

Inter, Space Grotesk and JetBrains Mono are bundled under the SIL Open Font License 1.1. Their complete notices are in `web/fonts/`. They are served locally; the UI does not call a remote font CDN.

## Zoom

Zoom Meeting SDK is proprietary and is **not included** in this repository, the source archives, `CunZoom.exe` or the public container image. Each user downloads the official SDK from Zoom Marketplace under the terms applicable to their own account: Windows users install the Windows SDK ZIP from within the app, Docker users mount the Linux SDK at runtime. The maintainers' CI uses a privately stored SDK only to compile and self-test the native worker; it is not redistributed. Our MIT license does not grant any rights to Zoom's SDK, services or trademarks.

The Linux integration was checked against the API usage documented by the official [Zoom raw recording sample](https://github.com/zoom/meetingsdk-linux-raw-recording-sample). No credentials or pre-authorized Zoom application are supplied.

## Dependencies and design references

Python dependencies retain their own licenses, available in the installed packages. `CunZoom.exe` is built with PyInstaller and bundles pywebview, pystray, Pillow, faster-whisper and their dependencies (exact versions in `requirements-windows-lock.txt`) under their respective licenses. Container OS packages retain their Ubuntu/upstream licenses. Faster Whisper uses the separately downloaded model selected by the installer.

Design references: [Nutlope/hallmark](https://github.com/Nutlope/hallmark) and [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill). The UI implementation and design decisions are in this repository; design-tool repositories are not shipped in the container.
