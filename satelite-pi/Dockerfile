# wyoming-satellite no publica imagen (el repo upstream está archivado), así que la armamos acá.
# alsa-utils trae arecord y aplay, que usan --mic-command y --snd-command.
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --yes --no-install-recommends alsa-utils git && \
    rm -rf /var/lib/apt/lists/*

# Instalación editable como hace upstream: sin -e no se copia el subpaquete wyoming_satellite.utils.
# webrtc trae --mic-auto-gain y --mic-noise-suppression.
WORKDIR /app
RUN git clone --depth 1 --branch v1.4.1 https://github.com/rhasspy/wyoming-satellite.git . && \
    pip install --no-cache-dir \
    --extra-index-url https://www.piwheels.org/simple \
    -f https://synesthesiam.github.io/prebuilt-apps/ \
    -e ".[webrtc]"

EXPOSE 10700

ENTRYPOINT ["python", "-m", "wyoming_satellite"]
