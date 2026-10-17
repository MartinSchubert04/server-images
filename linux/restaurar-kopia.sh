#!/bin/sh
# Restaura un snapshot de Kopia en los volúmenes de Docker y la carpeta del repo en DEST/docker-images.
# Es el camino principal del día del cambio (ver MIGRACION-LINUX.md, fase 6); export-volumes.ps1
# queda como plan B.
#
#   sh linux/restaurar-kopia.sh                 # el último snapshot
#   sh linux/restaurar-kopia.sh k315614c...     # uno en particular (kopia snapshot list)
#
# Después, para pasar los .env, bases y configs al clon del repo:
#   WIN=/srv/restore REPOS=docker-images sh linux/copy-untracked.sh
#
# Necesita el repositorio de Kopia en REPO (por defecto /srv/backups/kopia) y KOPIA_PASSWORD en el
# entorno o en kopia/.env. No pisa volúmenes que ya tengan datos.
set -eu
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KREPO="${REPO:-/srv/backups/kopia}"
DEST="${DEST:-/srv/restore}"
SNAP="${1:-}"

if [ -z "${KOPIA_PASSWORD:-}" ]; then
  KOPIA_PASSWORD=$(grep '^KOPIA_PASSWORD=' "$REPO_DIR/kopia/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r')
fi
[ -n "$KOPIA_PASSWORD" ] || { echo "Falta KOPIA_PASSWORD (entorno o kopia/.env)"; exit 1; }
[ -d "$KREPO" ] || { echo "No está el repositorio de Kopia en $KREPO"; exit 1; }

# Volumen:ruta dentro del snapshot. Tiene que coincidir con kopia/docker-compose.yml
VOLS="home-assistant_homeassistant_data:/data/homeassistant
home-assistant_esphome_data:/data/esphome
n8n_n8n_data:/data/n8n
waha_waha_sessions:/data/waha
job-autoapply_auth:/data/autoapply-auth"

MOUNTS=""
for m in $VOLS; do
  v=${m%%:*}
  if docker volume inspect "$v" >/dev/null 2>&1 && \
     [ -n "$(docker run --rm -v "$v:/v:ro" alpine ls -A /v)" ]; then
    echo "$v ya tiene datos: no lo piso (borrarlo con docker volume rm para restaurarlo)"
    exit 1
  fi
  docker volume create "$v" >/dev/null
  MOUNTS="$MOUNTS -v $m"
done

sudo mkdir -p "$DEST/docker-images"
docker volume create kopia-restore-config >/dev/null
k() {
  # shellcheck disable=SC2086
  docker run --rm -e KOPIA_PASSWORD="$KOPIA_PASSWORD" -v kopia-restore-config:/app/config \
    -v "$KREPO:/repository" $MOUNTS -v "$DEST/docker-images:/data/compose" kopia/kopia:latest "$@"
}

k repository connect filesystem --path=/repository \
  --override-hostname=mrtn-server --override-username=root >/dev/null
if [ -z "$SNAP" ]; then
  SNAP=$(k snapshot list root@mrtn-server:/data --json | grep -o '"id": *"[^"]*"' | tail -1 | cut -d'"' -f4)
fi
echo "Restaurando $SNAP"
k snapshot restore "$SNAP" /data
docker volume rm kopia-restore-config >/dev/null

for m in $VOLS; do
  v=${m%%:*}
  echo "$v: $(docker run --rm -v "$v:/v:ro" alpine du -sh /v | cut -f1)"
done
echo "repo en $DEST/docker-images: $(sudo du -sh "$DEST/docker-images" | cut -f1)"
