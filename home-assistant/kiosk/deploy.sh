#!/bin/sh
# Build del dashboard del kiosco y, si hay HA_TOKEN en home-assistant/.env, lo guarda en
# HA y recarga el kiosco. Sin token deja /local/kiosk/kd.json para guardarlo a mano
# (ver HANDOFF.md, "Deploy") y hay que borrarlo despues.
# Run from Git Bash on MRTN-SERVER.
set -e
cd "$(dirname "$0")"
MSYS_NO_PATHCONV=1 docker cp dashboard.yaml homeassistant:/tmp/kd.yaml
MSYS_NO_PATHCONV=1 docker cp build_dashboard.py homeassistant:/tmp/build_dashboard.py
MSYS_NO_PATHCONV=1 docker exec homeassistant python3 /tmp/build_dashboard.py /tmp/kd.yaml /config/www/kiosk/kd.json
MSYS_NO_PATHCONV=1 docker exec homeassistant rm /tmp/kd.yaml /tmp/build_dashboard.py

TOKEN=$(grep '^HA_TOKEN=' ../.env 2>/dev/null | cut -d= -f2- || true)
if [ -z "$TOKEN" ]; then
  echo "Sin HA_TOKEN en home-assistant/.env: kd.json quedó en /config/www/kiosk/ para guardarlo a mano."
  exit 0
fi
MSYS_NO_PATHCONV=1 docker cp save_dashboard.py homeassistant:/tmp/save_dashboard.py
# El token va por variable de entorno, no como argumento.
MSYS_NO_PATHCONV=1 docker exec -e HA_TOKEN="$TOKEN" homeassistant python3 /tmp/save_dashboard.py /config/www/kiosk/kd.json
# kd.json lo sirve /local sin login: no se deja ahí.
MSYS_NO_PATHCONV=1 docker exec homeassistant rm -f /tmp/save_dashboard.py /config/www/kiosk/kd.json
