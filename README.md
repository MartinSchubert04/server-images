# docker-images

Stacks de Docker Compose de `mrtn-server` (192.168.1.100). Una carpeta por stack; cada una se
levanta con `docker compose up -d` desde adentro.

## Servicios

| Stack | Servicio | Puerto | Para qué |
|---|---|---|---|
| `home-assistant` | Home Assistant | 8123 | Domótica |
| `home-assistant` | ESPHome | 6052 | Firmware de los ESP |
| `home-assistant` | Mosquitto | 1883 | Broker MQTT |
| `home-assistant` | Frigate | 5000, 8554, 8555 | Cámaras y detección (usa la GPU) |
| `adguard` | AdGuard Home | 53, 3000 | DNS de la red y bloqueo de ads |
| `n8n` | n8n | 5678 | Workflows |
| `waha` | WAHA | 3001 | API de WhatsApp |
| `dashy` | Dashy | 4000 | Portada con links a todo |
| `kopia` | Kopia | 51515 | Backups |

## Levantar desde cero

1. Copiar cada `.env.example` a `.env` y completar los valores.
2. Crear la red que comparten n8n y WAHA: `docker network create n8n_net`.
3. Levantar `home-assistant` primero: crea la red `home`, que `adguard` usa como externa.
4. Levantar el resto en cualquier orden.

## Home Assistant: clima y tráfico

El dashboard Home tiene las pestañas Weather y Traffic, y un resumen de ambas en Overview.

- **Clima:** `home-assistant-init/packages/clima.yaml` consulta Open-Meteo cada 10 minutos y crea
  `weather.clima` y los `sensor.clima_*`. Necesita `clima_latitud` y `clima_longitud` en el
  `secrets.yaml` de Home Assistant.
- **Tráfico:** mapas en vivo de Waze incrustados. Waze bloquea la integración Waze Travel Time
  y las alternativas con tráfico (HERE, TomTom, Google) piden API key.
- **Ruta por defecto:** `home-assistant-init/packages/ruta.yaml` calcula el tiempo en moto con
  tráfico en vivo entre dos direcciones (Nominatim para ubicarlas, TomTom para la ruta). Necesita
  `tomtom_api_key` en el `secrets.yaml` de Home Assistant. Origen y destino se editan en la
  pestaña Traffic (`input_text.ruta_origen` y `input_text.ruta_destino`); no están en el repo.
- **Tarjetas:** `weather-forecast-card.js` y `windy-card.js` van en `/config/www/weather-cards`;
  los links de descarga están en `athanor/build_home_dashboard.py`.
- `athanor/build_home_dashboard.py` se corre con el contenedor de Home Assistant detenido.

## Backups

Kopia respalda todos los días a las 04:00 los volúmenes de Home Assistant, ESPHome, n8n, WAHA y
esta carpeta completa, en `C:\Backups\kopia`. A las 05:00 la tarea programada de Windows
`Kopia mirror a pendrive` corre `kopia/mirror-backup.ps1` y copia el repositorio a `D:\kopia-backups`.

- Para cambiar el destino de la copia, editar `$Dest` en `kopia/mirror-backup.ps1`.
- Para restaurar hace falta una copia del repositorio y `KOPIA_PASSWORD` (está en `kopia/.env`,
  que no se versiona: guardarla también fuera del server).

## Qué no se versiona

Los `.env`, las bases de datos, los logs, los datos de AdGuard y Mosquitto, y todo lo de Frigate
salvo `config.yaml`. Ver `.gitignore`.
