# Migración de mrtn-server a Linux

Plan para pasar `mrtn-server` de Windows 11 + Docker Desktop (WSL2) a **Debian 13 sin escritorio**
con Docker nativo, sin perder nada y con vuelta atrás en cada paso.

La idea general: todo se prepara y se prueba **en paralelo** mientras Windows sigue siendo el server.
Primero en una VM, después en dual boot. El cambio final es un reinicio, y volver a Windows es otro.

## Índice

1. [Decisiones](#1-decisiones)
2. [Inventario de lo que hay hoy](#2-inventario-de-lo-que-hay-hoy)
3. [Qué cambia en Linux](#3-qué-cambia-en-linux)
4. [Fase 0: preparativos en Windows](#4-fase-0-preparativos-en-windows)
5. [Fase 1: preparar el repo](#5-fase-1-preparar-el-repo)
6. [Fase 2: ensayo en una VM de Hyper-V](#6-fase-2-ensayo-en-una-vm-de-hyper-v)
7. [Fase 3: instalar Debian en dual boot](#7-fase-3-instalar-debian-en-dual-boot)
8. [Fase 4: configurar el sistema](#8-fase-4-configurar-el-sistema)
9. [Fase 5: prueba con GPU](#9-fase-5-prueba-con-gpu)
10. [Fase 6: el día del cambio](#10-fase-6-el-día-del-cambio)
11. [Verificación](#11-verificación)
12. [Vuelta atrás](#12-vuelta-atrás)
13. [Después del cambio](#13-después-del-cambio)
14. [Riesgos y cosas a confirmar](#14-riesgos-y-cosas-a-confirmar)
15. [Apéndice: equivalencias y comandos](#15-apéndice-equivalencias-y-comandos)

---

## 1. Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Distro | Debian 13 (trixie), netinst, sin escritorio | La más liviana de las que tienen buen soporte de NVIDIA y Docker. 150-250 MB de RAM en reposo |
| Plan B de distro | Ubuntu Server 26.04 LTS | Si los drivers de NVIDIA o el Wi-Fi dan pelea en Debian: kernel más nuevo y `ubuntu-drivers` |
| Docker | Docker Engine del repo oficial (`download.docker.com`), no Docker Desktop | Sin VM en el medio |
| Instalación | Dual boot en el mismo NVMe, achicando C: | Hay 733 GB libres, BitLocker apagado, Secure Boot apagado |
| Red | **Cable Ethernet** (placa Realtek integrada) | El adaptador Wi-Fi USB necesita un kernel más nuevo que el de Debian 13 (ver [riesgos](#14-riesgos-y-cosas-a-confirmar)) |
| Ruta del repo | `/home/tincho/Projects/docker-images` | Misma estructura que en Windows, los otros proyectos al lado |
| Cambios al repo | Una cosa a la vez: primero migrar tal cual, después mejorar (red host, MTU, etc.) | Si algo falla, se sabe por qué |

## 2. Inventario de lo que hay hoy

### Medición (17/10/2026, con Frigate, n8n y WAHA parados)

| | RAM |
|---|---|
| Windows sin Docker Desktop | 3,5 GB en uso |
| Windows con Docker Desktop | 13,4 GB en uso (78 %) |
| Lo que usan los 13 contenedores prendidos | 1,8 GB |
| Lo que tiene tomado la VM de WSL | 7,9 GB (5,1 GB de caché que Windows no recupera) |

Además, Docker Desktop **solo corre con una sesión de Windows iniciada**: si el server se reinicia y
nadie entra, no levanta ningún contenedor. Docker Engine en Linux arranca con el sistema.

### Hardware

| | |
|---|---|
| Placa | Gigabyte H510M H (chip de sensores ITE IT8689E) |
| CPU | Intel Core i5-10400F, 6 núcleos / 12 hilos |
| RAM | 16 GB |
| GPU | NVIDIA RTX 2060 Super, 8 GB, driver 610.88 |
| Disco | ADATA LEGEND 900 1 TB (NVMe). C: 953 GB, 733 GB libres. ESP de 100 MB |
| Pendrive | Kingston DataTraveler 64 GB, `D:`, NTFS (espejo de Kopia) |
| Red | Wi-Fi: TP-Link Archer T2U Nano USB (`2357:011e`, chip RTL8811AU), IP `192.168.0.100`. Ethernet Realtek desconectada (MAC `D8-5E-D3-2E-D6-9F`) |
| BIOS | UEFI, Secure Boot apagado |

### Contenedores (este repo)

| Stack | Contenedores | Puertos | GPU |
|---|---|---|---|
| `home-assistant` | homeassistant, esphome, mosquitto, frigate, whisper, piper (+ hacs-installer y ssh-key-init de una pasada) | 8123, 6052, 1883, 5000, 8554, 8555, 10300, 10200 | frigate, whisper |
| `adguard` | adguardhome | 53 (en `192.168.0.100`), 3000 | |
| `n8n` | n8n | 5678 | |
| `waha` | waha | 3001 | |
| `dashy` | dashy | 4000 | |
| `kopia` | kopia | 51515 | |
| `monitoring` | dozzle, beszel, beszel-agent, socket-proxy | 8080, 8090 | |

### Contenedores de otros proyectos

| Proyecto | Contenedores | Puertos | Notas |
|---|---|---|---|
| `Job-autoapply` | autoapply, docker-proxy, ollama | 127.0.0.1:4517, 127.0.0.1:6080 | ollama usa la GPU. Prende y apaga WAHA |
| `RuView` | sensing-server | 3080 (por Tailscale), 5005/udp | En Linux se arregla el problema de UDP con varios ESP32 que tiene Docker Desktop |

### Volúmenes de Docker (viven dentro de la VM de Docker Desktop, 77 GB en total)

| Volumen | Qué tiene | ¿Migrar? |
|---|---|---|
| `home-assistant_homeassistant_data` | Toda la config, historial, `.storage`, clave SSH | **Sí** |
| `home-assistant_esphome_data` | Configs de los ESP | **Sí** |
| `home-assistant_whisper_data` | Modelo de Whisper (todavía no existe: Whisper no se levantó nunca) | No, se vuelve a bajar |
| `home-assistant_piper_data` | Voz de Piper (ídem) | No, se vuelve a bajar |
| `home-assistant_swag_config` | Resto de un SWAG viejo, nada lo usa | No |
| `n8n_n8n_data` | Workflows, credenciales, clave de cifrado | **Sí** |
| `waha_waha_sessions` | Sesión de WhatsApp | **Sí** (puede pedir QR igual) |
| `kopia_kopia_config` | Config del server de Kopia | **Sí** |
| `kopia_kopia_cache`, `kopia_kopia_logs` | Caché y logs | No |
| `job-autoapply_auth` | Sesión del navegador de autoapply | **Sí** |
| `job-autoapply_ollama` | Modelos (qwen3:8b, unos 5 GB) | Opcional: se puede volver a bajar |
| `ruview-cargo`, `ruview-target` | Caché de compilación de RuView | No |
| Unos 25 volúmenes anónimos (hash) | Restos de contenedores viejos | No |

### Datos en carpetas del repo (no versionados, hay que copiarlos)

- Todos los `.env` (`home-assistant/.env` tiene también `HA_TOKEN`).
- `adguard/conf/` y `adguard/work/`.
- `home-assistant/mosquitto/config/passwd` y `home-assistant/mosquitto/data/`.
- `home-assistant/frigate/config/` (bases, `model_cache/`, `go2rtc_homekit.yml`).
- `home-assistant/frigate/media/` (grabaciones, 7 días de retención: opcional).
- `monitoring/dozzle/` y `monitoring/beszel_data/`.
- `Job-autoapply/config/` y `Job-autoapply/data/`.
- `consumo-pc/data/` (histórico en SQLite), `config.json`, `tuya.json`, `tarifa.json`.

### Lo que corre en Windows por fuera de Docker

| Cosa | Para qué | Destino en Linux |
|---|---|---|
| Servicio `consumo-pc` (Go, puerto 8787) | Consumo eléctrico y recursos del server | Portar a Linux (ver [3.4](#34-consumo-pc)) |
| LibreHardwareMonitor (tarea al iniciar sesión, web en 8085) | Sensores que lee Home Assistant por REST | Lo reemplaza Glances (ver [3.2](#32-sensores-del-server-en-home-assistant)) |
| Glances (tarea al iniciar sesión, puerto 61208) | Uso de CPU, RAM y disco | Servicio de systemd |
| FanControl | Curvas de ventiladores | Curvas en la BIOS (Smart Fan) o CoolerControl |
| MSI Afterburner + RTSS | Perfil de la GPU | `nvidia-smi` (límite de potencia) en un servicio |
| Tarea `Kopia mirror a pendrive` (05:00) | `robocopy` del repositorio de Kopia a `D:` | `rsync` con un timer de systemd |
| `home-assistant/scripts/wake_on_lan.ps1` | Despertar a mrtn-main por SSH desde HA | `wakeonlan` |
| OpenSSH Server | HA entra para el WoL; acceso remoto | `openssh-server` |
| Tailscale + `tailscale serve` | Acceso remoto. Publica 3080, 4517, 6080, 8787 y el servicio `svc:consumo` | Tailscale para Linux, mismas reglas |
| RustDesk | Escritorio remoto | No hace falta (SSH) |
| Gaming Services, NVIDIA App, ShadowPlay, OneDrive, Copilot, Skillbrains Updater | Nada útil en un server | Desaparecen |
| ICS (`SharedAccess`) | Lo usa la Default Switch de Hyper-V/WSL y ocupa el `0.0.0.0:53` | Desaparece. AdGuard puede escuchar en todas las IPs |
| VS Build Tools, Go, Rust, Node, Python, OpenJDK | Compilar proyectos | Paquetes de Debian o instaladores oficiales, según haga falta |

### Accesos que dependen del server

- **mrtn-main** (`192.168.0.10`): HA la apaga por SSH (`apagar_pc`) y la prende con WoL (`wake_pc`).
- **Raspberry Pi** (satélite de voz): le habla a HA por IP. No cambia.
- **mrtn-hub** (kiosco): le habla a HA. No cambia.
- **Enchufes Tuya** (`192.168.0.50`, `.51`): los leen HA y `consumo-pc`. No cambian.
- **La red entera** usa AdGuard como DNS: **mientras el server esté apagado o en Linux sin AdGuard, la LAN se queda sin DNS** (ver [Fase 0](#4-fase-0-preparativos-en-windows)).
- **Dashy** apunta a `mrtn-server.tailbce521.ts.net`: el nodo de Linux tiene que terminar con ese mismo nombre.

## 3. Qué cambia en Linux

### 3.1 Cambios al repo

**Sirven en los dos sistemas: se commitean ya (Fase 1).**

- `home-assistant/docker-compose.yml`: agregar a `homeassistant`

  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```

  En Docker Desktop ese nombre ya existe y esto no cambia nada. En Linux no existe sin esta línea.
- `home-assistant/scripts/wake_on_lan.sh` (nuevo, al lado del `.ps1`):

  ```sh
  #!/bin/sh
  # Despierta a mrtn-main. HA lo corre por SSH: ver wake_pc en configuration.yaml
  MAC="${1:-58:11:22:4d:ef:8a}"
  wakeonlan -i 192.168.0.255 "$MAC"
  ```

  Nota: el `.ps1` actual manda el paquete a `192.168.1.255`, que es la red vieja. Conviene corregirlo
  también en Windows mientras tanto.
- `kopia/mirror-backup.sh` (nuevo, al lado del `.ps1`):

  ```sh
  #!/bin/sh
  # Copia el repositorio de Kopia al pendrive. Lo corre kopia-mirror.timer a las 05:00.
  SRC=/srv/backups/kopia/
  DEST=/mnt/pendrive/kopia-backups/
  LOG="$(dirname "$0")/mirror.log"
  log() { echo "$(date '+%F %T')  $1" >> "$LOG"; }

  if ! mountpoint -q /mnt/pendrive; then log "ERROR pendrive no montado"; exit 1; fi
  mkdir -p "$DEST"
  # -rt y no -a: el pendrive es NTFS y no guarda dueños ni permisos de Linux
  if rsync -rt --delete "$SRC" "$DEST"; then
    log "OK copia en $DEST ($(du -sm "$DEST" | cut -f1) MB)"
  else
    log "ERROR rsync código $?"; exit 1
  fi
  ```

- Carpeta `linux/` con lo que se instala en el sistema (ver [Fase 4](#8-fase-4-configurar-el-sistema)):
  `bootstrap.sh`, `daemon.json` y las unidades de systemd (`glances.service`, `kopia-mirror.service`,
  `kopia-mirror.timer`, `gpu-power.service`).

**Solo sirven en Linux: se aplican el día del cambio.**

- `configuration.yaml`: `wake_pc` pasa a `sh /home/tincho/Projects/docker-images/home-assistant/scripts/wake_on_lan.sh`.
- `configuration.yaml`: los sensores REST de LibreHardwareMonitor pasan a Glances ([3.2](#32-sensores-del-server-en-home-assistant)).
- `frigate/config/config.yaml`: decodificar la cámara con la GPU ([3.3](#33-frigate)).
- `kopia/.env`: `BACKUP_DEST=/srv/backups/kopia`.
- Borrar `kopia/mirror-backup.ps1` y `home-assistant/scripts/wake_on_lan.ps1`.
- README:
  - sacar "CPU, RAM y disco son los de la VM de WSL";
  - cambiar la sección de backups (timer en vez de tarea de Windows);
  - agregar cómo instalar en Linux.
- Comentarios desactualizados:
  - `adguard/docker-compose.yml`: el de ICS;
  - `monitoring/docker-compose.yml`: los de la VM de WSL;
  - `home-assistant/kiosk/deploy.sh`: "Run from Git Bash".

**Mejoras para después, una por vez ([sección 13](#13-después-del-cambio)).**

- Home Assistant con `network_mode: host`.
- Sacar el `mtu: 1200` de la red `home`.
- `beszel-agent` con red host y la imagen con GPU.
- AdGuard escuchando también en la IP de Tailscale.

### 3.2 Sensores del server en Home Assistant

Hoy `configuration.yaml` lee `http://host.docker.internal:8085/data.json` de LibreHardwareMonitor, con
rutas por índice (`Children[0][1][3]...`). En Linux eso no existe. Lo reemplaza la API de Glances, con
**los mismos nombres de sensor**, así las entidades (`sensor.cpu_temperatura`, etc.) y los dashboards
no cambian.

Reemplazo del bloque `rest` de LibreHardwareMonitor (verificar los `label` con
`curl localhost:61208/api/4/sensors` antes de aplicarlo):

```yaml
  - resource: http://host.docker.internal:61208/api/4/sensors
    scan_interval: 30
    sensor:
      - name: "CPU Temperatura"
        value_template: >-
          {{ (value_json | selectattr('label', 'eq', 'Package id 0') | first).value | float(0) }}
        unit_of_measurement: "°C"
        device_class: temperature

  - resource: http://host.docker.internal:61208/api/4/cpu
    scan_interval: 30
    sensor:
      - name: "CPU Uso Porcentaje"
        value_template: "{{ value_json.total | float(0) }}"
        unit_of_measurement: "%"

  - resource: http://host.docker.internal:61208/api/4/gpu
    scan_interval: 30
    sensor:
      - name: "GPU Temperatura"
        value_template: "{{ value_json[0].temperature | float(0) }}"
        unit_of_measurement: "°C"
        device_class: temperature

  - resource: http://host.docker.internal:61208/api/4/fs
    scan_interval: 60
    sensor:
      - name: "Disco Espacio Libre"
        value_template: >-
          {{ ((value_json | selectattr('mnt_point', 'eq', '/') | first).free / 1024**3) | round(1) }}
        unit_of_measurement: "GB"
        device_class: data_size
      - name: "Disco Espacio Total"
        value_template: >-
          {{ ((value_json | selectattr('mnt_point', 'eq', '/') | first).size / 1024**3) | round(1) }}
        unit_of_measurement: "GB"
        device_class: data_size
      - name: "Disco Uso Porcentaje"
        value_template: "{{ (value_json | selectattr('mnt_point', 'eq', '/') | first).percent }}"
        unit_of_measurement: "%"

  - resource: http://host.docker.internal:61208/api/4/mem
    scan_interval: 30
    sensor:
      - name: "RAM Uso Porcentaje"
        value_template: "{{ value_json.percent }}"
        unit_of_measurement: "%"
      - name: "RAM Usada"
        value_template: "{{ (value_json.used / 1024**3) | round(2) }}"
        unit_of_measurement: "GB"
        device_class: data_size
      - name: "RAM Disponible"
        value_template: "{{ (value_json.available / 1024**3) | round(2) }}"
        unit_of_measurement: "GB"
        device_class: data_size
```

El sensor `GPU Uso Frigate` (`http://frigate:5000/api/stats`) sigue igual. Revisar que la clave
`gpu_usages['NVIDIA GeForce RTX 2060 SUPER']` tenga el mismo nombre en Linux.

Ojo: `host.docker.internal` en Linux apunta a la IP del host en la red de Docker (`172.17.0.1` o la del
bridge `home`). Glances escucha en `0.0.0.0` y llega. `consumo-pc`, que hoy escucha solo en
`127.0.0.1`, no llega: ver [3.4](#34-consumo-pc).

### 3.3 Frigate

- La imagen `stable-tensorrt` y el detector `onnx` en GPU siguen igual.
- Hoy la cámara se decodifica con la CPU (no hay `hwaccel_args`). En Linux se puede pasar a la GPU:

  ```yaml
  ffmpeg:
    hwaccel_args: preset-nvidia
  ```

  La cámara es un stream HTTP (`http://192.168.1.39:8080`, probablemente MJPEG de una app de celular).
  Si es MJPEG, la decodificación con NVDEC puede no aplicar: probar y mirar el uso de CPU de ffmpeg en
  la página de sistema de Frigate. Si falla, sacar la línea.
- **Revisar la IP de la cámara:** `192.168.1.39` es de la red vieja; la LAN ahora es `192.168.0.x`.
- Driver: Frigate 0.17 con TensorRT pide un driver NVIDIA reciente. Confirmar la versión mínima en la
  doc de Frigate contra la que trae Debian 13 (ver [Fase 4](#84-driver-de-nvidia)).

### 3.4 consumo-pc

Es lo único que hay que reescribir. Es un proyecto aparte (`Projects/consumo-pc`), no de este repo.

| Archivo | Qué hace | En Linux |
|---|---|---|
| `tuya.go`, `tarifa.go`, `store.go`, `sqlite.go`, `web.go` | Enchufes, tarifa, histórico, dashboard | Portables tal cual (si el driver de SQLite es Go puro; si usa cgo, compilar con `gcc`) |
| `nvml.go` | GPU por `nvml.dll` | `libnvidia-ml.so.1` (por ejemplo con `github.com/NVIDIA/go-nvml`) |
| `sensors.go` (PawnIO) | Temperatura y W de la CPU, ventilador | Temperatura: `/sys/class/hwmon` (`coretemp`). Potencia: RAPL en `/sys/class/powercap/intel-rapl:0/energy_uj`. Ventilador: driver `it87` (ver [8.8](#88-ventiladores)) |
| `winapi.go` | CPU, RAM, red, discos, procesos | `/proc` o `github.com/shirou/gopsutil` |
| `service.go`, `install.ps1` | Servicio de Windows | Unidad de systemd |

Además:
- Escuchar también en la IP del bridge de Docker (o en `0.0.0.0` con `hosts_permitidos`), así HA lo
  alcanza por `host.docker.internal`.
- Copiar `data/` (histórico), `config.json`, `tuya.json` y `tarifa.json`.
- Volver a publicarlo por Tailscale: `tailscale serve --bg --tcp 8787 tcp://127.0.0.1:8787` y el
  servicio `svc:consumo` (ver [8.6](#86-tailscale)).

Si no está listo para el día del cambio, no bloquea: HA ya calcula energía y costo por su cuenta
(`packages/consumo.yaml`), y Beszel/Glances muestran los recursos. Solo se pierde por un tiempo el
dashboard de consumo-pc.

## 4. Fase 0: preparativos en Windows

Nada de esto cambia el funcionamiento del server.

- [ ] **Backup completo:** correr un snapshot manual en Kopia (UI en `:51515`) y el espejo al
      pendrive. Además, copiar el repositorio de Kopia a otro lado (otra PC o un disco externo).
- [ ] **Guardar `KOPIA_PASSWORD`** fuera del server, si no está ya.
- [ ] **Probar una restauración** de Kopia (se hace en la [Fase 2](#6-fase-2-ensayo-en-una-vm-de-hyper-v)).
- [ ] **Anotar las curvas de FanControl** (captura de cada curva y qué sensor usa).
- [ ] **Anotar el perfil de MSI Afterburner:** límite de potencia, límite de temperatura, curva de
      ventilador y si hay undervolt.
- [ ] **Guardar la config de Tailscale:**
      `tailscale serve status --json > C:\migracion\tailscale-serve.json`. Anotar cómo está definido
      `svc:consumo` en el admin (Services).
- [ ] **Copiar las claves autorizadas de SSH**:
      `C:\ProgramData\ssh\administrators_authorized_keys` (si `tincho` es admin) o
      `C:\Users\tincho\.ssh\authorized_keys`. Ahí está la clave de HA para `wake_pc`.
- [ ] **Listar los volúmenes reales:** `docker volume ls` con Docker Desktop prendido. Completar la
      tabla de la [sección 2](#volúmenes-de-docker-viven-dentro-de-la-vm-de-docker-desktop-77-gb-en-total).
- [ ] **Apagar el inicio rápido y la hibernación** de Windows (si no, Linux no puede montar C: sin
      riesgo):

      ```powershell
      powercfg /h off
      ```

- [ ] **Pasar un cable Ethernet** del router al server. Si se puede, que quede así para siempre.
      Actualizar la reserva de DHCP del router: la placa Ethernet tiene otra MAC (`D8-5E-D3-2E-D6-9F`).
      Si se sigue con Wi-Fi, ver [riesgos](#14-riesgos-y-cosas-a-confirmar).
- [ ] **DNS de respaldo en el router:** agregar un DNS secundario (por ejemplo `1.1.1.1`) para que la
      LAN no se quede sin internet mientras el server está en otra cosa. Se saca al final si querés que
      todo pase sí o sí por AdGuard.
- [ ] **BIOS:** confirmar "Restore on AC Power Loss" en On y que el arranque sea UEFI.
- [ ] **Bajar el ISO:** `debian-13.x.x-amd64-netinst.iso` de debian.org, a un pendrive con Rufus o
      Ventoy. **Usar otro pendrive, no el `D:` del espejo de Kopia.**

## 5. Fase 1: preparar el repo

Todo se commitea a `main` y no rompe Windows.

- [x] `extra_hosts` en `homeassistant` ([3.1](#31-cambios-al-repo)).
- [x] `home-assistant/scripts/wake_on_lan.sh`.
- [x] Corregir el broadcast de `wake_on_lan.ps1` a `192.168.0.255`. Ojo: `wake_pc` corre
      `powershell wake_on_lan.ps1` en la carpeta de inicio de `tincho` y ahí no hay ningún
      `wake_on_lan.ps1`, así que hoy probablemente falla igual. En Linux usa la ruta completa.
- [x] `kopia/mirror-backup.sh`.
- [x] `linux/bootstrap.sh`: los pasos de la [Fase 4](#8-fase-4-configurar-el-sistema) en un script,
      con una opción `--sin-gpu` para la VM.
- [x] `linux/daemon.json`, `linux/systemd/*.service` y `*.timer`.
- [x] `linux/export-volumes.ps1`, `linux/import-volumes.sh` y `linux/copy-untracked.sh`
      ([sección 10](#10-fase-6-el-día-del-cambio)).
- [x] `linux/ha-sensores-glances.yaml`: el bloque de Glances para `configuration.yaml`, para pegarlo el
      día del cambio. Los campos se probaron contra el Glances de Windows; falta confirmar en Linux el
      label de la temperatura de la CPU (en Windows el plugin `sensors` no existe).
- [x] `.gitattributes`: los `.sh` y las unidades de systemd siempre con LF, también en Windows.
- [ ] Revisar los puertos de RuView: el compose de ejemplo publica `127.0.0.1:3000` y `3001`, que
      chocan con AdGuard (3000) y WAHA (3001). En el server se usa 3080 y hoy no hay ningún
      contenedor de RuView: confirmar cómo se levanta.

## 6. Fase 2: ensayo en una VM de Hyper-V

> **Hecho el 17/10/2026, pero en WSL y no en Hyper-V** (Hyper-V no deja crear VMs en esta build de
> Windows). Resultados, cambios obligatorios y bugs encontrados en [linux/ENSAYO.md](linux/ENSAYO.md).
> Lo de abajo queda como referencia por si se repite en una VM.

Sirve para probar la instalación, el script y la restauración de backups sin tocar el disco.
No se prueba la GPU.

### Crear la VM

1. Hyper-V Manager → New → Virtual Machine.
   - Generation 2.
   - 6 GB de RAM (sin memoria dinámica).
   - 4 vCPU.
   - Disco de 80 GB.
   - Red: **Default Switch** por ahora.
2. Settings → Security: destildar Secure Boot (o elegir la plantilla "Microsoft UEFI Certificate
   Authority").
3. Montar el ISO de Debian y arrancar.

### Instalar y configurar

1. Instalar igual que en la [Fase 3](#7-fase-3-instalar-debian-en-dual-boot) (sin escritorio, con SSH).
2. Correr `linux/bootstrap.sh --sin-gpu`.
3. Clonar el repo en `~/Projects/docker-images`.

### Restaurar desde Kopia

**Antes de restaurar, aislar la VM:** pasar su adaptador a un switch **Private** (Virtual Switch
Manager → New → Private). Si no, HA en la VM va a manejar los dispositivos reales (enchufes, ESP,
`apagar_pc`), y n8n va a correr sus workflows (mails, WhatsApp).

1. Copiar a la VM una copia del repositorio de Kopia (por ejemplo, el del pendrive, con `scp` antes de
   aislarla, o con un disco virtual extra).
2. Levantar Kopia apuntando a esa copia (`BACKUP_DEST` en `kopia/.env`) y restaurar:

   ```sh
   docker compose -f kopia/docker-compose.yml run --rm kopia snapshot list
   docker compose -f kopia/docker-compose.yml run --rm kopia snapshot restore <id> /tmp/restore
   ```

   Para restaurar dentro de los volúmenes, montarlos con escritura en un contenedor temporal de Kopia.
   La idea es comprobar que **el backup sirve**: que HA levanta con su config e historial y que n8n
   tiene sus workflows.
3. Levantar solo lo que no usa GPU ni sesiones:

   ```sh
   cd ~/Projects/docker-images/home-assistant
   docker compose up -d mosquitto homeassistant esphome piper
   ```

   - No levantar `waha`: si la sesión se abre en dos lugares, WhatsApp puede cerrarla.
   - `adguard` está atado a `192.168.0.100`, que no existe en la VM. Si se quiere probar, publicar
     `53:53` en un override local.

### Qué validar

- [ ] `bootstrap.sh` corre de punta a punta sin errores. Si falla en algún paso, corregirlo en el repo.
- [ ] La restauración de Kopia funciona y los datos están completos.
- [ ] HA, ESPHome, Mosquitto, n8n, Dashy, Dozzle, Beszel y Kopia levantan.
- [ ] Glances corre como servicio y la API responde (`curl localhost:61208/api/4/mem`).
- [ ] Los sensores nuevos de Glances aparecen en HA.
- [ ] El timer del espejo de Kopia corre (con un pendrive virtual o una carpeta).

Cuando todo está bien, borrar la VM.

## 7. Fase 3: instalar Debian en dual boot

### Hacer lugar

1. Windows → Administración de discos → C: → Reducir volumen → **300 GB** (307200 MB). Alcanza para
   Docker (77 GB hoy, con margen para modelos y grabaciones).

   Si Windows no deja achicar tanto por archivos inamovibles: desactivar el archivo de paginación y
   los puntos de restauración, reiniciar, achicar y volver a activarlos.
2. No crear ninguna partición en el espacio libre: lo hace el instalador.

### Instalar

1. Arrancar del pendrive (F12 en Gigabyte para el menú de arranque). Elegir la entrada **UEFI**.
2. "Install" (el instalador de texto alcanza).
3. Idioma y teclado: español, Latinoamericano. Zona: Argentina.
4. Red: con el cable conectado, la toma sola.
5. Hostname: `mrtn-server`. Dominio: vacío.
6. Contraseña de root: **dejarla vacía** (así el usuario queda con `sudo`). Usuario: `tincho`.
7. Particionado:
   - "Guiado: utilizar el espacio libre contiguo más grande".
   - "Todos los ficheros en una partición".
   - Debe detectar la ESP de Windows y usarla como `/boot/efi` **sin formatearla**. Revisarlo antes
     de confirmar.
   - **No tocar** las particiones de Windows.
8. Mirror: Argentina, `deb.debian.org`.
9. Software: destildar todo lo de escritorio. Dejar solo **"servidor SSH"** y **"utilidades estándar
   del sistema"**.
10. GRUB: instalarlo en el disco. Si no aparece Windows en el menú al reiniciar:

    ```sh
    echo 'GRUB_DISABLE_OS_PROBER=false' | sudo tee -a /etc/default/grub
    sudo apt install os-prober && sudo update-grub
    ```

### Dejar el arranque controlable desde lejos

Mientras dure el dual boot, **Windows queda como arranque por defecto** (sigue siendo el server).

```sh
# En Linux: que GRUB recuerde la elección y arranque Windows por defecto
sudo sed -i 's/^GRUB_DEFAULT=.*/GRUB_DEFAULT=saved/' /etc/default/grub
echo 'GRUB_SAVEDEFAULT=false' | sudo tee -a /etc/default/grub
sudo update-grub
sudo grub-set-default "Windows Boot Manager (on /dev/nvme0n1p1)"   # el nombre exacto sale de: grep menuentry /boot/grub/grub.cfg

# Para volver a Windows desde Linux, por SSH:
sudo grub-reboot "Windows Boot Manager (on /dev/nvme0n1p1)" && sudo reboot
```

```powershell
# En Windows: entrar a Linux una sola vez, por SSH (consola de admin)
bcdedit /enum firmware            # buscar la entrada "debian" y copiar su {GUID}
bcdedit /set "{fwbootmgr}" bootsequence "{GUID-de-debian}"
shutdown /r /t 0
```

Si `bootsequence` manda a GRUB y GRUB arranca Windows igual (porque es el default guardado), usar en
cambio `grub-reboot` desde Linux, o dejar Linux por defecto en GRUB y que Windows use `bootsequence`
hacia su propio gestor. Probarlo una vez con acceso físico antes de depender de esto.

### Reloj

Windows guarda la hora local en el reloj de la placa; Linux guarda UTC. Para que no se pisen:

```sh
sudo timedatectl set-local-rtc 1
```

(Cuando Windows ya no esté, volver a `0`.)

## 8. Fase 4: configurar el sistema

Todo esto va en `linux/bootstrap.sh`, que ya se probó en limpio (ver [linux/ENSAYO.md](linux/ENSAYO.md)).
Debian netinst no trae git, así que primero:

```sh
sudo apt install -y git
mkdir -p ~/Projects && cd ~/Projects && git clone <url>/docker-images.git
cd docker-images && sudo sh linux/bootstrap.sh
```

Acá está desglosado lo que hace.

### 8.1 Base

```sh
sudo apt update && sudo apt full-upgrade -y

# Repos con contrib y non-free (drivers de NVIDIA)
sudo sed -i 's/^Components: .*/Components: main contrib non-free non-free-firmware/' \
  /etc/apt/sources.list.d/debian.sources
sudo apt update

sudo apt install -y curl git rsync htop btop ncdu jq unzip wakeonlan lm-sensors \
  ntfs-3g dos2unix unattended-upgrades apt-listchanges

sudo timedatectl set-timezone America/Argentina/Buenos_Aires
sudo dpkg-reconfigure -plow unattended-upgrades   # solo parches de seguridad automáticos
```

### 8.2 Que nunca se duerma

```sh
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

### 8.3 Red

- **Con cable:** el instalador ya dejó la interfaz configurada en `/etc/network/interfaces` por DHCP.
  La IP fija sale de la reserva del router (`192.168.0.100`).
- **Con Wi-Fi:** instalar NetworkManager (`sudo apt install network-manager`) y conectar con
  `nmtui`. Antes, ver si el adaptador funciona: [riesgos](#14-riesgos-y-cosas-a-confirmar).
- Debian 13 no usa `systemd-resolved`, así que el puerto 53 queda libre para AdGuard. (En Ubuntu habría
  que desactivar el stub listener.)

### 8.4 Driver de NVIDIA

```sh
sudo apt install -y linux-headers-amd64 nvidia-kernel-dkms nvidia-driver firmware-misc-nonfree \
  nvidia-persistenced
sudo reboot
nvidia-smi    # tiene que mostrar la 2060 Super
```

- Anotar la versión del driver y compararla con la mínima de Frigate 0.17 TensorRT.
- Si no alcanza: driver del repo CUDA de NVIDIA para Debian 13 (seguir la guía oficial de
  "CUDA Toolkit → Linux → Debian"), o pasarse a Ubuntu Server 26.04.
- Secure Boot está apagado, así que no hay que firmar el módulo.

### 8.5 Docker y NVIDIA Container Toolkit

```sh
# Docker Engine
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian trixie stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker tincho     # cerrar sesión y volver a entrar

# Rotación de logs (Docker Desktop no la tenía configurada)
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF

# NVIDIA Container Toolkit (escribe el runtime "nvidia" en daemon.json, respetando lo de arriba)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Prueba
docker run --rm --gpus all ubuntu nvidia-smi
```

### 8.6 Tailscale

```sh
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

- Mientras conviva con Windows, el nodo de Linux va a quedar como `mrtn-server-1` (el nombre ya lo
  tiene Windows). El día del cambio se renombra ([sección 10](#10-fase-6-el-día-del-cambio)).
- Las reglas de `tailscale serve` se cargan el día del cambio, no antes. Si no, el nodo de prueba
  publica servicios que todavía no tiene:

  ```sh
  sudo tailscale serve --bg --tcp 3080 tcp://127.0.0.1:3080   # RuView
  sudo tailscale serve --bg --tcp 4517 tcp://127.0.0.1:4517   # Job Autoapply
  sudo tailscale serve --bg --tcp 6080 tcp://127.0.0.1:6080   # Autoapply noVNC
  sudo tailscale serve --bg --tcp 8787 tcp://127.0.0.1:8787   # consumo-pc
  ```

- `svc:consumo` (`https://consumo.tailbce521.ts.net`) es un Tailscale Service con IP virtual propia.
  Hay que volver a publicarlo desde el nodo Linux con la misma definición que tiene hoy (ver lo que se
  guardó en la Fase 0) y aprobarlo en el admin si lo pide.

### 8.7 SSH

```sh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
# pegar en ~/.ssh/authorized_keys las claves copiadas de Windows (incluida la de Home Assistant)
chmod 600 ~/.ssh/authorized_keys

# Solo con clave
sudo tee /etc/ssh/sshd_config.d/10-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
PermitRootLogin no
EOF
sudo systemctl reload ssh
```

Probar desde otra terminal que se puede entrar **antes** de cerrar la sesión actual.

### 8.8 Ventiladores

Opción simple (recomendada): pasar las curvas de FanControl a la BIOS (Smart Fan 6 de Gigabyte), con
las capturas de la Fase 0. Así no dependen de ningún programa.

Si se quiere controlarlas desde Linux o que `consumo-pc` lea el ventilador:
- La placa usa el chip **IT8689E**, que el kernel no soporta de serie. Hace falta el driver `it87`
  fuera del árbol (`github.com/frankcrawford/it87`, instalable por DKMS).
- Después: `sudo sensors-detect`, `sensors`, y CoolerControl o `fancontrol` para las curvas.

Ventilador de la GPU: sin escritorio no se puede manejar la curva con `nvidia-settings`. Queda la curva
automática del driver, que en reposo alcanza.

### 8.9 Límite de potencia de la GPU

Replica lo que hacía Afterburner (ajustar el valor a lo anotado en la Fase 0; la 2060 Super viene con
175 W):

```ini
# /etc/systemd/system/gpu-power.service
[Unit]
Description=Límite de potencia de la GPU
After=nvidia-persistenced.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nvidia-smi -pl 150

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl enable --now nvidia-persistenced gpu-power
```

### 8.10 Glances

```sh
sudo apt install -y pipx
pipx install "glances[web,gpu]"
```

```ini
# /etc/systemd/system/glances.service
[Unit]
Description=Glances
After=network-online.target

[Service]
User=tincho
ExecStart=/home/tincho/.local/bin/glances -w --disable-plugin processlist,programlist,vms
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl enable --now glances
curl -s localhost:61208/api/4/sensors | jq   # anotar el label de la temperatura de la CPU
```

En Windows Glances corría con `sensors` desactivado. Acá queda activo porque HA lo usa.

### 8.11 Pendrive del espejo de Kopia

```sh
sudo mkdir -p /mnt/pendrive /srv/backups/kopia
sudo chown tincho: /srv/backups/kopia
sudo blkid                       # anotar el UUID del pendrive
echo 'UUID=XXXXXXXXXXXXXXXX /mnt/pendrive ntfs3 defaults,nofail,uid=1000,gid=1000 0 0' | sudo tee -a /etc/fstab
sudo mount -a
```

`nofail` evita que el server no arranque si el pendrive no está. Si se reformatea el pendrive a ext4
más adelante, cambiar `ntfs3` por `ext4`, sacar `uid`/`gid` y pasar el script a `rsync -a`.

```ini
# /etc/systemd/system/kopia-mirror.service
[Unit]
Description=Espejo del repositorio de Kopia al pendrive

[Service]
Type=oneshot
# Corre como root: Kopia escribe el repositorio como root dentro del contenedor
ExecStart=/home/tincho/Projects/docker-images/kopia/mirror-backup.sh
```

```ini
# /etc/systemd/system/kopia-mirror.timer
[Unit]
Description=Espejo de Kopia a las 05:00

[Timer]
OnCalendar=*-*-* 05:00
Persistent=true

[Install]
WantedBy=timers.target
```

```sh
sudo systemctl enable --now kopia-mirror.timer
```


### 8.12 Swap y journald

```sh
# Menos swap mientras haya RAM libre
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl --system

# Que los logs del sistema no crezcan sin límite
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=500M\n' | sudo tee /etc/systemd/journald.conf.d/size.conf
sudo systemctl restart systemd-journald
```

### 8.13 Montar C: para copiar datos (solo durante la migración)

```sh
sudo mkdir -p /mnt/c
sudo mount -t ntfs3 -o ro /dev/nvme0n1p3 /mnt/c    # ro: no tocar Windows
```

Si dice que el volumen está sucio, es que Windows no apagó del todo: arrancar Windows y apagarlo con
`shutdown /s /t 0` (con la hibernación ya desactivada en la Fase 0).

## 9. Fase 5: prueba con GPU

Con Linux arrancado en dual boot y **datos de prueba**: no los reales, para no divergir de Windows.
Windows sigue siendo el server; esto se hace en una ventana corta.

- [ ] `nvidia-smi` anda y `docker run --rm --gpus all ubuntu nvidia-smi` también.
- [ ] Frigate levanta con la GPU con un `config.yaml` de prueba. Detecta personas con la cámara real
      y el uso de GPU aparece en su página de sistema. Probar `preset-nvidia`.
- [ ] Whisper levanta con la GPU y baja el modelo `medium-int8`.
- [ ] ollama (Job-autoapply) ve la GPU.
- [ ] `sensors` muestra la temperatura de la CPU y Glances la expone.
- [ ] El pendrive se monta y el timer de espejo corre.
- [ ] Red: la IP es `192.168.0.100` y Tailscale está conectado.
- [ ] Al terminar: `docker compose down` de todo, borrar los datos de prueba y volver a Windows con
      `grub-reboot`.

## 10. Fase 6: el día del cambio

Conviene hacerlo un día tranquilo, con acceso físico al server, y con la [Fase 0](#4-fase-0-preparativos-en-windows)
completa. Calcular entre 2 y 4 horas.

### En Windows

1. Snapshot manual de Kopia y espejo al pendrive.
2. Parar todo, en este orden: Job-autoapply, RuView, n8n, waha, dashy, monitoring, kopia, adguard,
   home-assistant.

   ```powershell
   foreach ($s in 'n8n','waha','dashy','monitoring','kopia','adguard','home-assistant') {
     docker compose -f "C:\Users\tincho\Desktop\Projects\docker-images\$s\docker-compose.yml" stop
   }
   ```

3. **Camino principal:** con todo parado, sacar un snapshot manual de Kopia (`docker start kopia`,
   snapshot desde la UI o `docker exec kopia kopia snapshot create /data`, y `docker stop kopia`).
   En Linux se restaura con `linux/restaurar-kopia.sh` (paso 11), que ya se probó en el ensayo.

   **Plan B**, además o si Kopia falla: exportar los volúmenes (`.\linux\export-volumes.ps1`, que
   además avisa si algún contenedor sigue usándolos):

   ```powershell
   $out = 'C:\migracion\volumes'
   New-Item -ItemType Directory -Force $out | Out-Null
   $vols = 'home-assistant_homeassistant_data','home-assistant_esphome_data','n8n_n8n_data',
           'waha_waha_sessions','kopia_kopia_config','job-autoapply_auth'
           # sumar job-autoapply_ollama si no se quieren volver a bajar los modelos, y los de RuView
   foreach ($v in $vols) {
     docker run --rm -v "${v}:/v:ro" -v "${out}:/out" alpine tar czf "/out/$v.tar.gz" -C /v .
     "{0}: {1:N0} MB" -f $v, ((Get-Item "$out\$v.tar.gz").Length / 1MB)
   }
   ```

4. Parar el servicio `consumo-pc` (`Stop-Service consumo-pc`), para que su SQLite quede cerrado.
5. Copiar el repositorio de Kopia: queda en `C:\Backups\kopia`, se copia desde Linux.
6. Reiniciar a Linux (`bcdedit /set "{fwbootmgr}" bootsequence ...` o desde el menú de GRUB).

### En Linux

7. Montar C: en solo lectura ([8.13](#813-montar-c-para-copiar-datos-solo-durante-la-migración)).
8. Clonar los repos (no copiarlos de Windows: así quedan con finales de línea de Linux; en Windows está
   `core.autocrlf=true`):

   ```sh
   mkdir -p ~/Projects && cd ~/Projects
   git clone <url>/docker-images.git
   git clone <url>/Job-autoapply.git
   git clone <url>/RuView.git
   git clone <url>/consumo-pc.git
   ```

9. Copiar lo no versionado de cada repo (los archivos ignorados por git). Los pasos 9 y 10 los hace
   `sh linux/copy-untracked.sh` (con `--sin-grabaciones` para no copiar las de Frigate):

   ```sh
   W=/mnt/c/Users/tincho/Desktop/Projects
   for p in docker-images Job-autoapply RuView consumo-pc; do
     git -C "$W/$p" ls-files --others --ignored --exclude-standard -z \
       | grep -zv -e '^node_modules/' -e '/node_modules/' -e '\.exe$' \
       | sudo rsync -a --from0 --files-from=- "$W/$p/" "$HOME/Projects/$p/"
   done
   sudo chown -R tincho: ~/Projects
   ```

   Si no se quieren las grabaciones de Frigate, sumar `-e '^home-assistant/frigate/media/'` al
   `grep`.

10. Finales de línea y permisos:

    ```sh
    cd ~/Projects/docker-images
    find . -name '.env' -exec dos2unix {} +
    dos2unix home-assistant/mosquitto/config/passwd
    sudo chown -R 1883:1883 home-assistant/mosquitto     # mosquitto corre con uid 1883
    sudo chmod 0700 home-assistant/mosquitto/config/passwd
    ```

11. Recuperar los volúmenes. **Camino principal**, con el repositorio de Kopia ya copiado (paso 12;
    hacerlo antes que este):

    ```sh
    sh linux/restaurar-kopia.sh                       # último snapshot
    WIN=/srv/restore REPOS=docker-images sh linux/copy-untracked.sh
    ```

    El snapshot no tiene lo de Job-autoapply (`config/`, `data/`), consumo-pc ni RuView: eso sale
    igual de C: con `copy-untracked.sh` (paso 9).

    **Plan B**, desde los `.tar.gz` (`sh linux/import-volumes.sh`):

    ```sh
    IN=/mnt/c/migracion/volumes
    for f in "$IN"/*.tar.gz; do
      v=$(basename "$f" .tar.gz)
      docker volume create "$v"
      docker run --rm -v "$v:/v" -v "$IN:/in:ro" alpine tar xzf "/in/$v.tar.gz" -C /v
      echo "$v ok"
    done
    ```

    Compose va a avisar que esos volúmenes "ya existen pero no los creó Compose". Es un aviso, funcionan
    igual.

12. Copiar el repositorio de Kopia y ajustar el `.env`:

    ```sh
    rsync -a /mnt/c/Backups/kopia/ /srv/backups/kopia/
    sed -i 's#^BACKUP_DEST=.*#BACKUP_DEST=/srv/backups/kopia#' kopia/.env
    ```

13. Aplicar los cambios que solo sirven en Linux, **antes** de levantar HA (`ssh-key-init` copia
    `configuration.yaml` del repo en cada `up`):

    ```sh
    git apply linux/cambios-linux.patch    # sensores de Glances y wake_pc (probado en el ensayo)
    ```

    Después, a mano: `hwaccel` de Frigate y la IP de la cámara si hace falta ([3.3](#33-frigate)).
    Commitear y pushear.

14. Tailscale:
    1. En el admin de Tailscale, borrar el nodo viejo `mrtn-server` (Windows).
    2. Renombrar `mrtn-server-1` a `mrtn-server`.
    3. Cambiarle la IPv4 a `100.87.30.117` (Edit machine IPv4), así no cambia nada que la tenga anotada
       (por ejemplo `hosts_permitidos` de consumo-pc).
    4. Cargar las reglas de `tailscale serve` ([8.6](#86-tailscale)) y el servicio `svc:consumo`.

15. Levantar, en orden:

    ```sh
    cd ~/Projects/docker-images
    (cd home-assistant && docker compose up -d)      # crea la red "home"
    (cd adguard && docker compose up -d)
    docker network create n8n_net
    (cd n8n && docker compose up -d)
    (cd waha && docker compose up -d)                # entrar al dashboard y escanear el QR si lo pide
    (cd monitoring && docker compose up -d)
    (cd dashy && docker compose up -d)
    (cd kopia && docker compose up -d)
    (cd ~/Projects/Job-autoapply && docker compose up -d --build)
    (cd ~/Projects/RuView/docker && docker compose up -d --build)
    ```

    Si `hacs-installer` falla por la red, no frena nada: HACS ya está instalado en el volumen.

16. consumo-pc: si ya está portado, compilar e instalar su unidad de systemd. Si no, los
    `sensor.server_*` del kiosco y del dashboard Home quedan no disponibles hasta portarlo.

16b. **Kopia: reconectarlo a su repositorio.** Su config no está en el snapshot; sin esto no hay
    backups:

    ```sh
    docker exec kopia kopia repository connect filesystem --path=/repository       --override-hostname=mrtn-server --override-username=root
    docker exec kopia kopia snapshot list --all      # tiene que mostrar el historial
    ```

16c. **Kiosco:** en HA → Ajustes → Entidades, buscar `host_docker_internal` y ver con qué nombres
    quedaron el disco `/`, el pendrive y la placa de red. Actualizar `kiosk/dashboard.yaml` (hoy usa
    `c_disk_usage`, `d_disk_usage`, `wi_fi_rx` y `wi_fi_tx`) y correr `kiosk/deploy.sh`. O renombrar
    las entidades nuevas a los IDs viejos.

17. GRUB: Linux pasa a ser el arranque por defecto.

    ```sh
    sudo grub-set-default 0 && sudo update-grub
    ```

18. Recorrer la [verificación](#11-verificación).

19. Desmontar C: (`sudo umount /mnt/c`) y sacar el DNS secundario del router si se quiere.

## 11. Verificación

### Sistema

- [ ] `free -h`: anotar la RAM en uso con todo levantado, para comparar con Windows.
- [ ] `nvidia-smi`: Frigate, Whisper y (al usarse) ollama en la lista de procesos. La GPU baja a P8 en
      reposo.
- [ ] El enchufe Tuya del server marca menos W en reposo que con Windows (comparar en HA).
- [ ] `docker ps`: todo `Up` y nada reiniciándose (`docker ps --filter status=restarting`).
- [ ] `systemctl --failed`: vacío.
- [ ] Reiniciar el server una vez y comprobar que todo vuelve solo.

### Por servicio

- [ ] **Home Assistant:**
  - entra y conserva dashboards, historial y usuarios;
  - el kiosco (mrtn-hub) carga;
  - las integraciones no muestran errores: MQTT, Frigate, Wyoming (Whisper y Piper), Tuya, ESPHome,
    AdGuard;
  - los sensores de CPU, RAM, disco y GPU tienen valores.
- [ ] **wake_pc y apagar_pc:** prender y apagar mrtn-main desde HA.
- [ ] **Voz:** decirle algo al satélite de la Pi y que responda.
- [ ] **ESPHome:** los dispositivos aparecen online.
- [ ] **Mosquitto:** Frigate publica eventos (en HA, `binary_sensor` de persona).
- [ ] **Frigate:** se ve la cámara, detecta, graba. Uso de CPU de ffmpeg más bajo que antes.
- [ ] **AdGuard:** desde otra PC, `nslookup google.com 192.168.0.100` responde; las consultas aparecen
      en el log.
- [ ] **n8n:** los workflows están y las credenciales andan (si n8n no puede descifrarlas, falta la
      clave de cifrado del volumen).
- [ ] **WAHA:** sesión conectada; mandar un mensaje de prueba desde n8n.
- [ ] **Dashy:** todos los links en verde.
- [ ] **Dozzle:** se ven los logs.
- [ ] **Beszel:** muestra el server. Ahora son las métricas del host, no las de una VM.
- [ ] **Kopia:** la UI entra, ve los snapshots viejos y un snapshot manual funciona. Al otro día,
      comprobar el de las 04:00 y el espejo de las 05:00 (`kopia/mirror.log`).
- [ ] **Job-autoapply:** la UI en 4517 por Tailscale y el noVNC en 6080; la sesión sigue iniciada.
- [ ] **RuView:** la UI en 3080 por Tailscale; recibe datos de los ESP32.
- [ ] **consumo-pc** (si ya se portó): dashboard en `https://consumo.tailbce521.ts.net` con el
      histórico viejo.
- [ ] **Tailscale:** desde el celular, entrar a `mrtn-server.tailbce521.ts.net:8123`.

## 12. Vuelta atrás

Windows queda intacto, con sus volúmenes de Docker Desktop, hasta que se borre a propósito.

1. En Linux: `docker compose stop` de todo (para que no queden dos AdGuard ni dos HA si después se
   prende alguno).
2. `sudo grub-reboot "Windows Boot Manager (on /dev/nvme0n1p1)" && sudo reboot`.
3. En Windows, Docker Desktop arranca y levanta los contenedores como estaban.
4. Tailscale: si se borró el nodo de Windows en el admin, volver a loguearlo y renombrarlo a
   `mrtn-server`.
5. WAHA puede pedir el QR de nuevo.

Lo que haya cambiado mientras estuvo Linux (historial de HA, ejecuciones de n8n, grabaciones) no está
en Windows. Si hace falta, exportar esos volúmenes desde Linux con el mismo `tar` e importarlos en
Windows.

## 13. Después del cambio

Una mejora por vez, con unos días de por medio para ver que todo sigue bien.

1. **Una o dos semanas de observación.** Windows sigue ahí por las dudas.
2. **Home Assistant con red host** (`network_mode: host`). Habilita el descubrimiento (mDNS, SSDP,
   HomeKit, DLNA) y simplifica el WoL. A cambio, HA deja de resolver los otros contenedores por
   nombre:
   - sacar `ports` y `networks` del servicio `homeassistant`;
   - en `configuration.yaml`: `http://frigate:5000` → `http://127.0.0.1:5000`;
   - `host.docker.internal` → `127.0.0.1`, y sacar `trusted_proxies` si no hay proxy;
   - en la UI de HA, cambiar el host de MQTT (`mosquitto` → `127.0.0.1`), Wyoming (`whisper`,
     `piper` → `127.0.0.1`), Frigate y AdGuard;
   - Frigate y los demás siguen en la red `home`, con los puertos publicados.
3. **Sacar el `mtu: 1200`** de la red `home`, que probablemente venía de WSL. Probar Frigate y HA
   después.
4. **Beszel con GPU:** `beszel-agent` con `network_mode: host` (ve las interfaces reales) y la imagen
   `henrygd/beszel-agent-nvidia` con la reserva de GPU.
5. **AdGuard** también en la IP de Tailscale, para tener DNS con bloqueo fuera de casa.
6. **Borrar Windows:**
   1. Último backup.
   2. Borrar sus particiones desde Linux (`sudo cfdisk /dev/nvme0n1`).
   3. Extender la de Linux (`growpart` + `resize2fs`).
   4. Sacar la entrada de Windows de GRUB.
   5. `sudo timedatectl set-local-rtc 0`.
7. **Limpiar el repo:**
   - borrar `kopia/mirror-backup.ps1`, `home-assistant/scripts/wake_on_lan.ps1` y los
     `MSYS_NO_PATHCONV` de `deploy.sh`;
   - actualizar el README;
   - borrar este plan o moverlo a `linux/`.

## 14. Riesgos y cosas a confirmar

| Riesgo | Qué pasa | Qué hacer |
|---|---|---|
| **Wi-Fi USB (`2357:011e`, RTL8811AU)** | El soporte en el kernel (`rtw88_8821au`) llegó alrededor de la versión 6.13. Debian 13 trae la 6.12, así que probablemente no lo reconozca | **Cable**, recomendado. Si no: kernel de `trixie-backports`, el driver DKMS `morrownr/8821au`, o Ubuntu 26.04. Probar antes con el live USB de Debian y `lsusb` / `ip link` |
| Driver NVIDIA de Debian viejo para Frigate | Frigate TensorRT no arranca | Repo CUDA de NVIDIA o Ubuntu 26.04 |
| Kernel de backports + driver NVIDIA | Si se usa un kernel nuevo por el Wi-Fi, el DKMS de NVIDIA puede no compilar | Otra razón para usar cable |
| LAN sin DNS mientras el server no tiene AdGuard | Nadie navega | DNS secundario en el router durante la migración |
| WAHA pierde la sesión | Hay que escanear el QR de nuevo | Tener el celular a mano el día del cambio |
| n8n no descifra las credenciales | La clave de cifrado vive en `n8n_n8n_data` | Migrar el volumen entero, no solo la base |
| HA en la VM o en las pruebas maneja dispositivos reales | Se prenden/apagan cosas, se apaga mrtn-main | Switch Private en la VM; datos de prueba en la Fase 5 |
| Dos `mrtn-server` en Tailscale | Dashy y los links apuntan al equivocado | Renombrar el día del cambio, no antes |
| Archivos con CRLF copiados de Windows | `.env` con `\r` al final de cada valor | `dos2unix` ([paso 10](#10-fase-6-el-día-del-cambio)) |
| Permisos de los bind mounts | Mosquitto (uid 1883) no puede escribir | `chown` del paso 10; mirar `docker logs` de cada uno |
| ESP de 100 MB | GRUB no entra | Debian usa unos pocos MB; revisar el espacio libre antes de instalar |
| `consumo-pc` sin portar | Sin su dashboard un tiempo | No bloquea; HA ya calcula consumo y costo |
| IPs de la red vieja (`192.168.1.x`) | La cámara de Frigate y el broadcast del WoL apuntan a `192.168.1.x` | Corregirlas (puede que ya esté fallando hoy) |
| Puertos de RuView | El compose de ejemplo choca con AdGuard (3000) y WAHA (3001) | Confirmar la config real (3080) antes de levantarlo |

## 15. Apéndice: equivalencias y comandos

| En Windows | En Linux |
|---|---|
| Docker Desktop | `docker` y `docker compose` (Engine nativo) |
| `Get-Service` / `services.msc` | `systemctl status <servicio>`, `systemctl --failed` |
| Tareas programadas | Timers de systemd (`systemctl list-timers`) |
| Visor de eventos | `journalctl -u <servicio> -f`, `journalctl -b -p err` |
| Administrador de tareas | `btop`, `htop` |
| `robocopy /MIR` | `rsync -a --delete` |
| `nvidia-smi` / Afterburner | `nvidia-smi`, `nvidia-smi -pl <W>` |
| LibreHardwareMonitor | `sensors`, Glances |
| FanControl | BIOS Smart Fan, CoolerControl, `fancontrol` |
| `shutdown /r /t 0` | `sudo reboot` |
| Arrancar el otro sistema | Desde Windows: `bcdedit /set "{fwbootmgr}" bootsequence {GUID}`. Desde Linux: `sudo grub-reboot "<entrada>"` |
| Uso de disco | `df -h`, `ncdu /`, `docker system df` |
| Actualizar | `sudo apt update && sudo apt full-upgrade`; imágenes: `docker compose pull && docker compose up -d` |
