#!/bin/sh
# Build de un dashboard y, si hay HA_TOKEN en home-assistant/.env, lo guarda en HA.
#   sh deploy.sh        -> kiosco (dashboard.yaml -> dashboard-kiosk) y recarga TouchKio
#   sh deploy.sh home   -> Home de escritorio (home.yaml -> dashboard-home), con las
#                          plantillas del kiosco de base
# Sin token deja /local/kiosk/kd.json para guardarlo a mano
# y hay que borrarlo despues. Correr en mrtn-server.
set -e
cd "$(dirname "$0")"
if [ "$1" = "home" ]; then
  SRC=home.yaml; URL_PATH=dashboard-home; REFRESH=""; BASE=/tmp/kd_base.yaml
  docker cp dashboard.yaml homeassistant:$BASE
else
  SRC=dashboard.yaml; URL_PATH=dashboard-kiosk; REFRESH=button.touchkio_mrtn_hub_refresh; BASE=""
fi
docker cp "$SRC" homeassistant:/tmp/kd.yaml
docker cp build_dashboard.py homeassistant:/tmp/build_dashboard.py
docker exec homeassistant python3 /tmp/build_dashboard.py /tmp/kd.yaml /config/www/kiosk/kd.json $BASE
docker exec homeassistant rm -f /tmp/kd.yaml /tmp/build_dashboard.py /tmp/kd_base.yaml

TOKEN=$(grep '^HA_TOKEN=' ../.env 2>/dev/null | cut -d= -f2- || true)
if [ -z "$TOKEN" ]; then
  echo "Sin HA_TOKEN en home-assistant/.env: kd.json quedó en /config/www/kiosk/ para guardarlo a mano en $URL_PATH."
  exit 0
fi
docker cp save_dashboard.py homeassistant:/tmp/save_dashboard.py
# El token va por variable de entorno, no como argumento.
docker exec -e HA_TOKEN="$TOKEN" homeassistant python3 /tmp/save_dashboard.py /config/www/kiosk/kd.json $URL_PATH $REFRESH
# kd.json lo sirve /local sin login: no se deja ahí.
docker exec homeassistant rm -f /tmp/save_dashboard.py /config/www/kiosk/kd.json
