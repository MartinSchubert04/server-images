#!/bin/sh
# Deja un Debian 13 recién instalado listo para levantar los stacks de este repo.
# Se puede correr más de una vez.
#
#   sudo sh linux/bootstrap.sh            # server real, con la GPU
#   sudo sh linux/bootstrap.sh --sin-gpu  # VM de prueba: sin drivers de NVIDIA
#
# No toca la red, no hace "tailscale up" ni monta el pendrive: eso va a mano (lo avisa al final).
set -eu

GPU=1
[ "${1:-}" = "--sin-gpu" ] && GPU=0

if [ "$(id -u)" -ne 0 ] || [ -z "${SUDO_USER:-}" ]; then
  echo "Correrlo con sudo desde el usuario normal: sudo sh linux/bootstrap.sh"
  exit 1
fi
USUARIO="$SUDO_USER"
HOME_USUARIO="$(getent passwd "$USUARIO" | cut -d: -f6)"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
. /etc/os-release
CODENAME="$VERSION_CODENAME"

paso() { printf '\n==> %s\n' "$1"; }

paso "Repos con contrib y non-free"
if [ -f /etc/apt/sources.list.d/debian.sources ]; then
  sed -i 's/^Components: .*/Components: main contrib non-free non-free-firmware/' \
    /etc/apt/sources.list.d/debian.sources
fi
# El instalador a veces deja el formato viejo (sources.list) en vez de debian.sources
if [ -f /etc/apt/sources.list ]; then
  sed -i -E '/^deb(-src)? .*debian/ s/ main( .*)?$/ main contrib non-free non-free-firmware/' \
    /etc/apt/sources.list
fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y

paso "Paquetes base"
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl gnupg git rsync htop btop ncdu jq unzip wakeonlan lm-sensors \
  ntfs-3g dos2unix pipx unattended-upgrades apt-listchanges

paso "Zona horaria y parches de seguridad automáticos"
timedatectl set-timezone America/Argentina/Buenos_Aires
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

paso "Que nunca se suspenda"
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

paso "Swap y logs del sistema"
echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
sysctl --system >/dev/null
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=500M\n' > /etc/systemd/journald.conf.d/size.conf
systemctl restart systemd-journald

if [ "$GPU" -eq 1 ]; then
  paso "Driver de NVIDIA"
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    linux-headers-amd64 nvidia-kernel-dkms nvidia-driver firmware-misc-nonfree nvidia-persistenced
fi

paso "Docker Engine"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $CODENAME stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
mkdir -p /etc/docker
# Solo si no existe: nvidia-ctk le agrega su runtime y no hay que pisarlo
[ -f /etc/docker/daemon.json ] || cp "$REPO/linux/daemon.json" /etc/docker/daemon.json
usermod -aG docker "$USUARIO"

if [ "$GPU" -eq 1 ]; then
  paso "NVIDIA Container Toolkit"
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
fi
systemctl restart docker

paso "Tailscale"
command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh

paso "SSH solo con clave"
if [ -s "$HOME_USUARIO/.ssh/authorized_keys" ]; then
  cat > /etc/ssh/sshd_config.d/10-hardening.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin no
EOF
  systemctl reload ssh
else
  echo "No hay claves en $HOME_USUARIO/.ssh/authorized_keys: dejo la contraseña habilitada para no quedar afuera."
fi

paso "Glances"
# pypi a veces tarda: hasta tres intentos con timeout largo
n=0
until sudo -u "$USUARIO" -H env PIP_DEFAULT_TIMEOUT=60 pipx install --force "glances[web,gpu]"; do
  n=$((n + 1))
  [ "$n" -ge 3 ] && { echo "No se pudo instalar Glances"; exit 1; }
  echo "Reintento $n de Glances..."; sleep 10
done
install -m 0644 "$REPO/linux/systemd/glances.service" /etc/systemd/system/

paso "Espejo de Kopia al pendrive"
mkdir -p /srv/backups/kopia /mnt/pendrive
chown "$USUARIO": /srv/backups/kopia
install -m 0644 "$REPO/linux/systemd/kopia-mirror.service" "$REPO/linux/systemd/kopia-mirror.timer" \
  /etc/systemd/system/
chmod +x "$REPO/kopia/mirror-backup.sh" "$REPO/home-assistant/scripts/wake_on_lan.sh"

if [ "$GPU" -eq 1 ]; then
  install -m 0644 "$REPO/linux/systemd/gpu-power.service" /etc/systemd/system/
fi

systemctl daemon-reload
systemctl enable --now glances
systemctl enable kopia-mirror.timer
if [ "$GPU" -eq 1 ]; then
  systemctl enable nvidia-persistenced gpu-power
fi

cat <<EOF

Listo. Falta a mano:
  1. Reiniciar (driver de NVIDIA y grupo docker): sudo reboot
  2. Probar la GPU:       docker run --rm --gpus all ubuntu nvidia-smi
  3. Tailscale:           sudo tailscale up
  4. Pendrive del espejo: sudo blkid, agregar a /etc/fstab
       UUID=<uuid> /mnt/pendrive ntfs3 defaults,nofail,uid=1000,gid=1000 0 0
     y después: sudo mount -a && sudo systemctl start kopia-mirror.timer
  5. Revisar el límite de potencia en /etc/systemd/system/gpu-power.service
  6. Sensores de la CPU: sudo sensors-detect --auto && sensors
EOF
