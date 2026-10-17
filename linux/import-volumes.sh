#!/bin/sh
# Crea los volúmenes de Docker a partir de los .tar.gz de export-volumes.ps1.
#   sh linux/import-volumes.sh [carpeta]    # por defecto /mnt/c/migracion/volumes
# Compose va a avisar que estos volúmenes "ya existen pero no los creó Compose": es solo un aviso.
set -eu
IN="${1:-/mnt/c/migracion/volumes}"

for f in "$IN"/*.tar.gz; do
  [ -e "$f" ] || { echo "No hay .tar.gz en $IN"; exit 1; }
  v=$(basename "$f" .tar.gz)
  if docker volume inspect "$v" >/dev/null 2>&1 && \
     [ -n "$(docker run --rm -v "$v:/v:ro" alpine ls -A /v)" ]; then
    echo "$v ya existe y tiene datos: lo salteo (borrarlo a mano si hay que reimportarlo)"
    continue
  fi
  docker volume create "$v" >/dev/null
  docker run --rm -v "$v:/v" -v "$IN:/in:ro" alpine tar xzf "/in/$v.tar.gz" -C /v
  echo "$v ok"
done
