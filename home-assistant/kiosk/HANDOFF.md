# Handoff: kiosco MRTN-HUB (Home Assistant)

Estado al 2026-10-15. Para retomar en otra sesión. El usuario habla en español.

## Qué es

- **Kiosco:** Raspberry Pi 5 `MRTN-HUB` + Touch Display 2 con **TouchKio**, mostrando el dashboard
  de HA `dashboard-kiosk`. Pantalla 720×1280 usada **horizontal a 1280×720** (zoom de TouchKio
  100 %). Probar todo en **1280×720**.
- **Server:** `MRTN-SERVER` (Windows 11, Docker Desktop), IP LAN `192.168.0.100`, Tailscale
  `100.87.30.117`. HA Container en `docker-images/home-assistant/docker-compose.yml`.
- **Diseño:** clon pixel a pixel de ha-fusion (tema "muted"): sidebar a la izquierda (hora, fecha,
  pronóstico de 6 días, gráfico de temperatura) y pestañas arriba.

## Archivos (repo `docker-images`, remoto `MartinSchubert04/server-images`, rama `main`)

| Archivo                                                  | Qué es                                                                                                                                                                                                                      |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `home-assistant/kiosk/dashboard.yaml`                    | **Fuente del dashboard.** Una vista por pestaña. Templates de button-card al principio.                                                                                                                                     |
| `home-assistant/kiosk/build_dashboard.py`                | Une las vistas en **una sola vista** (path `overview`) con páginas que se muestran/ocultan por `#hash`. Así el sidebar no se redibuja al cambiar de pestaña.                                                                |
| `home-assistant/kiosk/deploy.sh`                         | Corre el build dentro del contenedor y deja el JSON en `/config/www/kiosk/kd.json`.                                                                                                                                         |
| `home-assistant/kiosk/mrtn-kiosk.yaml`                   | Tema "MRTN Kiosk" (se copia a `/config/themes/`). Se aplica por vista (`theme:`), no por usuario.                                                                                                                           |
| `home-assistant/kiosk/kiosk.css`                         | `@font-face` de Inter (recurso de Lovelace `/local/kiosk/kiosk.css`).                                                                                                                                                       |
| `home-assistant/kiosk/map.html`                          | Mapa Leaflet + MapTiler `streets-v2-dark`. En el repo tiene `__MAPTILER_KEY__`; la clave real se inserta solo en la copia de `/config/www/kiosk/map.html` (sale de `ha-fusion/configuration.yaml`, que está en .gitignore). |
| `home-assistant/home-assistant-init/packages/kiosk.yaml` | Automatizaciones y helpers del kiosco y luces. `init.sh` copia `packages/*.yaml` a `/config/packages` al arrancar.                                                                                                          |

En el contenedor (`/config/www/kiosk/`): fondo `muted_background.webp`, fuentes Inter,
íconos `meteocons/`, `map.html` con clave. Backups del dashboard en
`/config/.storage/lovelace.dashboard_kiosk.bak-*`.

## Deploy del dashboard

1. Editar `kiosk/dashboard.yaml` (no pegarlo directo en el editor de HA: primero hay que hacer el build).
2. `sh home-assistant/kiosk/deploy.sh` (Git Bash).
3. Guardar en HA desde un navegador logueado (Claude in Chrome, pestaña en `http://mrtn-server:8123/dashboard-kiosk/overview?disable_km`):
   ```js
   const hass = document.querySelector("home-assistant").hass;
   const cfg = await (await fetch("/local/kiosk/kd.json?" + Date.now())).json();
   await hass.callWS({
     type: "lovelace/config/save",
     url_path: "dashboard-kiosk",
     config: cfg,
   });
   ```
4. Borrar el JSON temporal (lo sirve `/local` sin login): `MSYS_NO_PATHCONV=1 docker exec homeassistant rm -f /config/www/kiosk/kd.json`
5. Recargar el kiosco: `button.touchkio_mrtn_hub_refresh` (recarga la página actual).
6. Probar en un iframe de 1280×720 inyectado en esa pestaña (la ventana de Chrome no se deja achicar).

Si cambia el tema: `docker cp kiosk/mrtn-kiosk.yaml homeassistant:/config/themes/` y servicio `frontend.reload_themes`.
Si cambia `kiosk.yaml`: copiar a `/config/packages/`, `check_config`, y recargar `automation`, `input_number`,
`input_datetime` (no hace falta reiniciar HA).

**Con token (lo normal):** si `home-assistant/.env` tiene `HA_TOKEN=` (token de larga duración de HA), `deploy.sh` hace
todo solo: build, guardado por WebSocket (`save_dashboard.py`), borra `kd.json` y recarga el kiosco. Los pasos 3 a 5
solo hacen falta sin token.

## Home de escritorio (home.yaml → dashboard-home)

El Home (panel por defecto de HA) usa el mismo estilo fusion que el kiosco, en grande para un monitor
(probado a 1920×1080 y 1366×768). Reemplazó al Home de Athanor (la lámina de Doré del `athanor-hero-card`).

- Fuente: `kiosk/home.yaml`. Deploy: `sh kiosk/deploy.sh home` (usa `dashboard.yaml` como base de plantillas:
  `build_dashboard.py` agrega sus `button_card_templates` y las de `home.yaml` pisan por nombre).
- Plantillas propias: `desk_tile` (76 px de alto, llena la celda), `desk_slider`, `desk_info` (solo lectura),
  `desk_stat` (número grande + historial de 24 h con min/max, caché en `window.__deskSpark`), `desk_media`,
  `desk_tabs`, `desk_panel` (superficie para tarjetas hechas a mano: discos, procesos, núcleos, dispositivos).
- Sidebar de 400 px `position: fixed` sin `left` (queda al lado del menú de HA); debajo de 1100 px pasa arriba.
- Pestañas: Overview, Server, Network, Weather, Traffic, Energy, Lights, Automations; subpáginas `map` y `sun`.
- kiosk-mode oculta el header (en ventanas de menos de 900 px vuelve). Editar con `?disable_km`.
- Ojo con button-card: si una tarjeta tiene `width` propio le pone `max-width: fit-content` al host; por eso
  las desk_* llevan `:host { max-width: none !important }`. Las listas en `variables` se mezclan ítem por ítem
  con las de la plantilla padre: la lista de pestañas va como plantilla `[[[ return [...] ]]]`.
- `extra_styles` de una plantilla hija se suma a la del padre (no la reemplaza).
- `athanor/build_home_dashboard.py` ya no escribe `dashboard_home`. Backup del Home anterior:
  `/config/.storage/lovelace.dashboard_home.bak-202610181559`.

## Pestañas (dashboard.yaml)

Overview, HUB, Network, Weather, Server, Energy, Automations. Subpáginas: `map` (tocar Martin),
`sun` (tocar Sun), `stopwatch` (tocar Stopwatch). Para sumar una pestaña: agregar `[path, Title]` en
`fusion_tabs.variables.tabs` y una vista con ese `path` cuyo primer card sea `template: fusion_tabs`.
La barra se desliza de costado si no entran.

Templates útiles: `fusion_tile` (botón 192×61), `fusion_slider` (brillo: tocar el ícono = toggle,
tocar/arrastrar el resto = brillo; `variables.iw` = ancho de la columna del ícono, 61), `fusion_time`, `fusion_uptime`, `fusion_title`, `fusion_title_next`,
`sw_engine` (cronómetro global en `window.__sw`, guardado en localStorage). Layouts: `*tiles_layout`,
`*charts_layout`, `*columns_layout` (1 columna por debajo de 1200 px).

## Automatizaciones (packages/kiosk.yaml)

- Brillo de la pantalla de noche y de día (`input_datetime.kiosk_noche_inicio`/`kiosk_dia_inicio`, `input_number.kiosk_brillo_*`).
- Volver a Overview tras `input_number.kiosk_inactividad_min` sin tocar: escribe `…/dashboard-kiosk/overview#overview`
  en `text.touchkio_mrtn_hub_page_url` (el botón refresh de TouchKio NO vuelve al inicio).
- Luces con la **etiqueta "Auto lights"** (`auto_lights`): atenuar desde `luces_atenuar_hora` a `luces_atenuar_brillo`,
  apagar a `luces_apagar_hora`. Luces nuevas: solo ponerles la etiqueta.
- Los valores se editan desde la pestaña Automations del kiosco (tocando cada valor).

## Preferencias y reglas del usuario

- **Los enchufes (plugs) nunca se pueden apagar desde el kiosco:** tiles de solo lectura, sin tap ni more-info.
  `switch.bedroom_plug_server_socket_1` alimenta el server donde corre HA.
- La PC se prende por Wake on LAN (`button.encender_pc`); antes era manteniendo presionado (se sacó con la sección Devices).
- Avisar antes de reiniciar HA. No mostrar contraseñas en el chat.
- Commits **sin** línea de Co-Authored-By. Pidió commit + push directo a `main`.
- Todo cohesivo con el estilo fusion; touch targets ≥ 44 px.

## Pendiente / conocido

- **Media = Haze** (reproductor de escritorio, repo `MartinSchubert04/Haze`, local en `Projects/Haze`):
  publica por MQTT (usuario `haze`, clave `MQTT_HAZE_PASSWORD` en `.env`) y crea por discovery el
  dispositivo "Haze PC": `sensor.haze_mrtn_main_estado` (atributos title, artist, context, volume...),
  `sensor.haze_mrtn_main_cancion`, `sensor.haze_mrtn_main_artista`, `image.haze_mrtn_main_caratula`,
  `button.haze_mrtn_main_anterior|play_pausa|siguiente`, `number.haze_mrtn_main_volumen`, `switch.haze_mrtn_main_aleatorio`,
  `select.haze_mrtn_main_repetir`, `select.haze_mrtn_main_reproducir_carpeta`, `sensor.haze_mrtn_main_cola` (la cola: atributos `songs` con hasta 400 temas, `current`, `offset`, `jump_topic`; se salta a uno publicando su uid en `haze/<pc>/jump/set`; excluido del recorder). En el dashboard: template `fusion_media`
  (tapa de fondo que se funde hacia abajo, título y controles: aleatorio, anterior, play, siguiente y carpeta, que abre `window.__hazeList`: diálogo propio con el desplegable de carpeta y la lista de canciones; tamaño ancho × alto en tiles con `input_number.kiosk_media_ancho|alto`, desde los tres puntos) en la sección Media de Overview.
  El `media_player` universal de HA no sirve acá: no deja sobrescribir título ni artista.
- **AdGuard marca 0 consultas:** el contenedor no publica el puerto 53; nadie lo usa como DNS.
- **Wi-Fi del server en perfil "Público":** Docker Desktop bloquea las entradas en redes públicas, así que `192.168.0.100`
  no respondía desde la LAN (por Tailscale sí). Se le sugirió pasar la red a Privada; no se confirmó.
- **BMP280 (ESP32)** no disponible; `sensor.bedroom_plug_pc_main_power` no existe (los datos de la PC en Energy dan 0).
- REST `host.docker.internal:8085/data.json` (temperaturas del server, probablemente LibreHardwareMonitor) falla.
- El contenedor **ha-fusion** sigue corriendo en el puerto 5050; se puede apagar cuando el usuario lo confirme.
- **Clave de MapTiler** expuesta sin login en `/local/kiosk/map.html` (se sugirió restringirla por dominio en MapTiler).

## Cosas aprendidas (para no repetir errores)

- layout-card: `card_margin: 0` se ignora en la vista; el margen sale de `--masonry-view-card-margin` (puesto en 0 en el tema).
- button-card evalúa los `[[[ ]]]` de las tarjetas anidadas en `custom_fields.card` con el contexto del padre: no anidar
  cards con plantillas dentro de un button-card.
- En plantillas de button-card no usar los nombres de variable `html` (choca con lit) ni `hass` (ya existe en el contexto). El código va antes del `return`.
- Las `variables` de button-card se evalúan antes que los `custom_fields`.
- button-card pone `pointer-events: none` en los custom fields: hay que habilitarlo. En touch cancela el `click`:
  usar `onpointerup` y cortar la propagación.
- La tarjeta de mapa nativa de HA pide API key de CARTO: por eso se usa `map.html`.
- Glances corre como tarea programada de Windows "Glances" con
  `-w --disable-plugin processlist,programlist,sensors,vms` (antes tardaba 3,7 s y HA cortaba).
- `docker pull` desde esta sesión falla (Credential Manager de Windows): el usuario corre los pulls en su terminal.
- Git Bash: usar `MSYS_NO_PATHCONV=1` con rutas de contenedor.
- Credenciales de MQTT en `home-assistant/.env` (`MQTT_TOUCHKIO_PASSWORD`, `MQTT_HOMEASSISTANT_PASSWORD`, `FRIGATE_MQTT_PASSWORD`).
  El `passwd` de Mosquitto tiene que ser del uid 1883.
