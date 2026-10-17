#!/bin/sh
# Copia el repositorio de Kopia al pendrive. Lo corre kopia-mirror.timer a las 05:00.
# Es la versión de Linux de mirror-backup.ps1. Para cambiar el destino, editar DEST y el punto de
# montaje en /etc/fstab. Cualquier copia de la carpeta más KOPIA_PASSWORD alcanza para restaurar.
SRC=/srv/backups/kopia/
MNT=/mnt/pendrive
DEST="$MNT/kopia-backups/"
LOG="$(dirname "$0")/mirror.log"

log() { echo "$(date '+%F %T')  $1" >> "$LOG"; }

if ! mountpoint -q "$MNT"; then
  log "ERROR pendrive no montado en $MNT"
  exit 1
fi

mkdir -p "$DEST"
# -rt y no -a: el pendrive es NTFS y no guarda dueños ni permisos de Linux
rsync -rt --delete "$SRC" "$DEST"
code=$?
if [ "$code" -ne 0 ]; then
  log "ERROR rsync código $code"
  exit 1
fi

log "OK copia en $DEST ($(du -sm "$DEST" | cut -f1) MB)"
