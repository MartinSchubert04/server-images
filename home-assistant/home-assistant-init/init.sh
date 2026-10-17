#!/bin/sh
set -e

mkdir -p /config/www/snapshots

if [ ! -f /config/.ssh/id_ed25519 ]; then
  mkdir -p /config/.ssh
  ssh-keygen -t ed25519 -f /config/.ssh/id_ed25519 -N ""
  echo "=== Clave SSH generada. Clave publica (agregala a authorized_keys en la PC Windows): ==="
  cat /config/.ssh/id_ed25519.pub
else
  echo "La clave SSH ya existe, no se regenera."
fi

cp /init/configuration.yaml /config/configuration.yaml
echo "configuration.yaml sobreescrito desde template."

mkdir -p /config/packages
cp /init/packages/*.yaml /config/packages/
echo "packages sobreescritos desde template."