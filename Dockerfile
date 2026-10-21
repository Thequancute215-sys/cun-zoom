FROM ubuntu:22.04
LABEL org.opencontainers.image.source="https://github.com/Thequancute215-sys/cun-zoom" \
      org.opencontainers.image.title="Cun Zoom" \
      org.opencontainers.image.licenses="MIT"
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    CUN_ZOOM_CONTAINER=1 CUN_ZOOM_DATA_DIR=/data CUN_ZOOM_RECORDINGS_DIR=/data/lessons \
    CUN_ZOOM_SDK_DIR=/opt/zoom-sdk CUN_ZOOM_WORKER=/data/native/CunZoomBot \
    HOME=/data/home TZ=Asia/Bangkok DISPLAY=:99 XDG_RUNTIME_DIR=/data/runtime \
    PULSE_SERVER=unix:/data/runtime/pulse/native \
    LD_LIBRARY_PATH=/data/native/runtime:/opt/zoom-sdk:/opt/zoom-sdk/qt_libs:/opt/zoom-sdk/qt_libs/Qt/lib
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv tini ca-certificates tzdata \
    g++ pkg-config libglib2.0-dev libjpeg-dev xvfb pulseaudio pulseaudio-utils \
    libx11-xcb1 libxcb-xfixes0 libxcb-shape0 libxcb-shm0 libxcb-randr0 \
    libxcb-image0 libxcb-keysyms1 libxcb-xtest0 libdbus-1-3 libgbm1 libxfixes3 \
    libgl1 libdrm2 libgssapi-krb5-2 libcurl4 libegl-mesa0 libsdl2-2.0-0 \
    libasound2 libnss3 libgtk-3-0 libxkbcommon-x11-0 libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-transcription.txt ./
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements-transcription.txt
ENV PATH="/opt/venv/bin:$PATH"
COPY src/ src/
COPY web/ web/
COPY native/linux_bot.cpp native/linux_bot.cpp
COPY scripts/build_linux.py scripts/container_entry.py scripts/
COPY LICENSE THIRD_PARTY_NOTICES.md ./
RUN useradd --uid 10001 --home-dir /data/home --no-create-home cunzoom \
    && mkdir -p /data /opt/zoom-sdk && chown 10001:10001 /data
USER 10001:10001
EXPOSE 18766
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18766/health',timeout=3).read()"
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "/app/scripts/container_entry.py"]
