# Ensayo de la migración

Resultado del ensayo de la fase 2 de [MIGRACION-LINUX.md](../MIGRACION-LINUX.md), hecho el 17/10/2026.
Lo que dice acá está probado, no supuesto.

**Resultado:** con los scripts de `linux/` (ya corregidos), un Debian 13 limpio queda configurado, se
restauran los datos desde Kopia y levantan los 14 contenedores que no usan GPU, sin errores propios
de la migración. Después de un reinicio en frío vuelven todos solos, sin iniciar sesión.

## Cómo se hizo

- **Sin VM:** Hyper-V en este Windows (build 26300) no deja administrar máquinas virtuales.
  `Get-VMHost` y `New-VMSwitch` fallan con "no se encontró el objeto", incluso elevados y desde
  Windows PowerShell 5.1. Solo funciona la parte que usa WSL.
- **En su lugar, una distro de WSL aparte (`mrtn-test`)**: Debian 13 limpio (la imagen
  `debian:trixie` exportada), con systemd y su propio Docker Engine. Docker Desktop no se tocó.
  Queda instalada y apagada en `C:\migracion\wsl\`. Se borra con `wsl --unregister mrtn-test`.
- **Aislada:** un servicio de systemd aplica, antes de que arranque Docker, reglas de iptables
  (cadena `DOCKER-USER`) que cortan toda salida de los contenedores fuera de las redes de Docker.
  Se verificó antes y después: sin corte, internet responde. Con el corte quedan bloqueados internet,
  el router, mrtn-main y el enchufe Tuya. El corte sobrevive al reinicio. Así HA no tocó
  dispositivos reales, WAHA no se conectó a WhatsApp y n8n no mandó nada.
- **Sin puertos publicados:** en WSL todas las distros comparten la red con Docker Desktop y los
  puertos reales ya están ocupados. Cada stack se levantó con un override `ports: !reset []` y se
  probó por la IP interna del contenedor. En el server real esto no pasa.
- **Imágenes:** pasadas de Docker Desktop con `docker save | docker load`. Bajarlas dentro de WSL
  fallaba por la red inestable.
- **Datos:** restaurados con `linux/restaurar-kopia.sh` del snapshot del 17/10 17:24, no copiados de
  Windows. Lo de Job-autoapply se copió de C: con `copy-untracked.sh`.

**No se pudo probar acá** (queda para la fase 5, en el server de verdad): drivers de NVIDIA,
Frigate, Whisper, ollama, GRUB y dual boot, la placa de red, los sensores de la placa (en WSL no hay
`coretemp`), el pendrive real, Tailscale y el apagado/encendido de mrtn-main.

## Qué se probó y cómo salió

| Prueba | Resultado |
|---|---|
| `bootstrap.sh --sin-gpu` en un Debian 13 limpio | OK, de punta a punta. Se puede repetir sin romper nada |
| Restaurar desde Kopia (`restaurar-kopia.sh`) | OK: 5 volúmenes y la carpeta del repo. No pisa volúmenes con datos |
| Copiar lo no versionado (`copy-untracked.sh`) | OK: 34 archivos de docker-images y 139 de Job-autoapply |
| Home Assistant | OK: 20 integraciones, 528 entidades, 3 usuarios, 11 dashboards, 194 MB de historial. Ninguna integración falló al arrancar |
| HA → Mosquitto | OK, conecta con el usuario `homeassistant` |
| HA → Glances del host (`host.docker.internal:61208`) | OK |
| Parche `linux/cambios-linux.patch` | Aplica limpio, `check_config` sin errores, desaparecen los errores del puerto 8085 |
| ESPHome, AdGuard, Dashy, Dozzle, Beszel, Kopia | OK (responden; los que piden login devuelven la redirección o el 401) |
| Beszel agente → hub | OK, conecta con la clave restaurada |
| WAHA | OK: carga la sesión "Martin" (y el firewall le impide conectarse) |
| n8n | OK: levanta y lee su base. Ver la nota sobre n8n más abajo |
| Kopia | OK después de reconectarlo al repositorio. Ve todo el historial y conserva el horario de las 04:00 |
| Espejo de Kopia (timer + `mirror-backup.sh`) | OK: sin pendrive falla con un aviso claro; con pendrive copia 602 MB; la segunda vez tarda 0,1 s |
| `wake_on_lan.sh` | OK (probado con una MAC falsa) |
| Job-autoapply (sin ollama) | OK: UI y noVNC responden |
| Reinicio en frío | OK: vuelven los 14 contenedores, el firewall, Glances y el timer. 0 servicios fallados |
| RAM de los 14 contenedores | 2,4 GB (con n8n y WAHA, que en Windows hoy están parados) |

## Cambios obligatorios en Linux, y por qué

| Qué | Por qué | Estado |
|---|---|---|
| `kopia/.env`: `BACKUP_DEST=/srv/backups/kopia` | Dice `C:\Backups\kopia`. En Linux el compose ni siquiera arranca: "invalid volume specification" | **Automático**: lo corrige `copy-untracked.sh` |
| Reconectar Kopia a su repositorio | La config del server de Kopia (`kopia_kopia_config`) no está en el snapshot. Sin esto la UI dice "Repository not configured" y no hay backups | Paso manual: `docker exec kopia kopia repository connect filesystem --path=/repository --override-hostname=mrtn-server --override-username=root` |
| `extra_hosts: host.docker.internal:host-gateway` en `homeassistant` | En Linux ese nombre no existe sin esta línea. HA lo usa para Glances y consumo-pc | **Hecho** |
| Sensores de LibreHardwareMonitor → Glances (`cpu_temperatura`, `ram_uso_porcentaje`, etc.) | LibreHardwareMonitor es de Windows (puerto 8085) | **En el parche** `linux/cambios-linux.patch` |
| `wake_pc` → `sh .../wake_on_lan.sh` | No hay PowerShell. Además hoy busca el `.ps1` en la carpeta de inicio, donde no está | **En el parche** |
| **Sensores `sensor.server_*`** (CPU, GPU, RAM, VRAM, red, disco, procesos, potencias) | Vienen de la API de consumo-pc (`:8787/api/live`). Los usan el kiosco y el dashboard Home. Sin consumo-pc en Linux quedan no disponibles | Portar consumo-pc **manteniendo el mismo formato de `/api/live`**: así HA no cambia nada. Energía, costo y tarifas no se ven afectados (salen del enchufe Tuya) |
| **Entidades de la integración Glances en el kiosco**: `host_docker_internal_c_disk_usage`, `d_disk_usage`, `wi_fi_rx`, `wi_fi_tx` | Son los nombres de Windows (`C:\`, `D:\`, `Wi-Fi`). En Linux Glances informa `/`, `/mnt/pendrive` y la placa con su nombre de Linux (por ejemplo `enp3s0`), así que se crean entidades nuevas y las viejas quedan huérfanas | El día del cambio: ver las entidades nuevas en HA y actualizar `kiosk/dashboard.yaml`. O renombrar las nuevas a los IDs viejos desde la UI |
| Scripts con permiso de ejecución en git | Se commitearon desde Windows sin el bit `+x`. El `chmod` del bootstrap se pierde cuando git toca el archivo, y systemd no podía correr el espejo | **Hecho**: `100755` en git, y el servicio llama a `/bin/sh` |
| Instalar `git` antes de clonar | Debian netinst no lo trae, y `bootstrap.sh` está dentro del repo | En el plan |
| Snapshot de Kopia **con todo parado** | El de hoy se sacó con HA prendido: al restaurar, HA avisa que la base "no se cerró bien". Se recuperó, pero con n8n o Frigate escribiendo puede no tener la misma suerte | En el plan (fase 6, paso 3) |
| `hacs-installer` y `ssh-key-init` necesitan internet en cada `up` | Hacen `apk add` y bajan HACS. Si fallan, `homeassistant` no arranca con `docker compose up` (depende de que terminen bien). Además `ssh-key-init` **sobrescribe `configuration.yaml`** con el del repo | El parche se aplica en el repo **antes** de levantar. Si no hay internet: `up -d --no-deps homeassistant` |

## Bugs encontrados y arreglados en los scripts

| Script | Problema | Arreglo |
|---|---|---|
| `bootstrap.sh` | `pipx install glances` falla con timeouts de pypi y corta todo el script | Hasta 3 intentos con `PIP_DEFAULT_TIMEOUT=60` |
| `copy-untracked.sh` | git se niega a listar un repo de otro dueño ("dubious ownership"). Pasa con C: montado como root y con una restauración | `git -c safe.directory='*'` |
| `copy-untracked.sh` | Si el listado de git fallaba, seguía como si nada | El listado va a un archivo primero; si falla, corta |
| `copy-untracked.sh` | No copiaba `adguard/work/` (estadísticas, log, filtros): es de root con 0700 | El listado corre con `sudo` |
| `copy-untracked.sh` | Origen fijo en `/mnt/c/...` | `WIN`, `LIN` y `REPOS` por variable de entorno |
| `copy-untracked.sh` | Dejaba la ruta de Windows en `kopia/.env` | La pasa sola a `/srv/backups/kopia` |
| `kopia-mirror.service` | No podía ejecutar el script (sin `+x`) | `ExecStart=/bin/sh ...` |
| `ha-sensores-glances.yaml` | Sin el sensor "Package id 0", la plantilla de temperatura daba error en cada lectura | `availability:` → queda "no disponible" |

## Cosas de valor

- **El server estuvo caído casi 16 horas el 17/10.** El último estado que grabó HA antes de hoy es de
  la 01:37, y los contenedores volvieron recién cuando se inició sesión por RDP a las 17:23. Docker
  Desktop solo corre con una sesión de Windows abierta. En Linux, Docker arranca con el sistema: se
  probó con el reinicio en frío.
- **El backup de Kopia sirve** y alcanza para migrar: trae los volúmenes y la carpeta del repo con
  los `.env` y las bases. `export-volumes.ps1` queda como plan B.
- **Lo que Kopia no respalda hoy:** `Job-autoapply/config` y `data` (con `app.db`), los datos de
  consumo-pc (histórico SQLite) y RuView. Para migrar no importa (salen de C:), pero conviene
  sumarlos a Kopia: hoy, si se rompe el disco, eso se pierde.
- **n8n no ejecuta nada desde el 14/08.** Tiene 4 workflows (3 activos) y 4 credenciales, pero la
  última ejecución es del 14/08, y al arrancar dice "0 published workflows". Con n8n 2.x
  probablemente haya que *publicar* los workflows para que corran. Además la base pesa 1,6 GB y
  1,5 GB son datos de solo 112 ejecuciones: borrar ejecuciones viejas y hacer `VACUUM` la achica
  mucho.
- **Frigate está parado desde el 10/10** (lo frenaron, no fue por falta de memoria) y **n8n desde
  el 02/10** en el server actual.
- **Ya tenés las integraciones Glances, System Monitor y Wake on LAN configuradas en HA.** Glances
  apunta a `host.docker.internal:61208` y funciona en Linux sin tocar nada. Los sensores de
  LibreHardwareMonitor no los usa ningún dashboard: el reemplazo por Glances es solo para no dejar
  sensores rotos.
- **El plugin de GPU de Glances funciona** y lee la 2060 Super, así que la plantilla "GPU
  Temperatura" de Glances va a andar.
- **Los `.env` ya están con LF.** El `dos2unix` queda por las dudas.
- **Los bind mounts que vienen de Windows quedan con permisos 777.** Funcionan, pero conviene
  ajustarlos después de migrar (`chmod -R go-w` en las carpetas de datos).
- **El repositorio de Kopia es solo de root**: el espejo tiene que correr como root (ya lo hace).
- **La red de WSL tiene MTU 1360** por pasar por el Wi-Fi, y eso explica los timeouts y las
  descargas que fallan. Probablemente también es el origen del `mtu: 1200` de la red `home`. En
  Linux nativo con cable debería poder volver a 1500.
- **El aviso "volume already exists but was not created by Docker Compose"** aparece con los
  volúmenes restaurados. Es solo un aviso, funcionan igual.
- **Sugerencia:** mover `hacs-installer` a un perfil de Compose (`profiles: [init]`), para que
  levantar HA no dependa de internet ni reinstale HACS en cada `up`.
