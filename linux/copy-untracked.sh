#!/bin/sh
# Copia lo que git no versiona (.env, bases, configs con claves) de los repos en Windows a los clones
# de Linux. C: tiene que estar montado: sudo mount -t ntfs3 -o ro /dev/nvme0n1p3 /mnt/c
#   sh linux/copy-untracked.sh [--sin-grabaciones]
# Origen, destino y repos se pueden cambiar, por ejemplo para copiar desde una restauración de Kopia:
#   WIN=/tmp/restore REPOS=docker-images sh linux/copy-untracked.sh
set -eu
WIN="${WIN:-/mnt/c/Users/tincho/Desktop/Projects}"
LIN="${LIN:-$HOME/Projects}"
REPOS="${REPOS:-docker-images Job-autoapply RuView consumo-pc}"

FILTRO='^$'
[ "${1:-}" = "--sin-grabaciones" ] && FILTRO='^home-assistant/frigate/media/'

for p in $REPOS; do
  [ -d "$WIN/$p" ] || { echo "No está $WIN/$p, lo salteo"; continue; }
  [ -d "$LIN/$p" ] || { echo "Falta clonar $p en $LIN"; exit 1; }
  echo "==> $p"
  # safe.directory: C: montado o una restauración son de root, y git se niega a leer repos ajenos
  LISTA=$(mktemp)
  git -c safe.directory='*' -C "$WIN/$p" ls-files --others --ignored --exclude-standard -z > "$LISTA"
  grep -zv -e 'node_modules/' -e '\.exe$' -e '\.log$' -e "$FILTRO" "$LISTA" \
    | sudo rsync -a --from0 --files-from=- "$WIN/$p/" "$LIN/$p/"
  echo "$(tr -cd '\0' < "$LISTA" | wc -c) archivos no versionados"
  rm -f "$LISTA"
done
sudo chown -R "$(id -u):$(id -g)" "$LIN"

# Windows deja CRLF en los archivos que no pasan por git
find "$LIN" -name '.env' -not -path '*/node_modules/*' -exec dos2unix -q {} +

# Mosquitto corre con uid 1883 y se queja si el passwd lo puede leer cualquiera
M="$LIN/docker-images/home-assistant/mosquitto"
if [ -d "$M" ]; then
  dos2unix -q "$M/config/passwd" 2>/dev/null || true
  sudo chown -R 1883:1883 "$M"
  sudo chmod 0700 "$M/config/passwd"
fi
echo "Listo"
