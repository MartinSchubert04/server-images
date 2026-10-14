"""Builds the dashboards that are generated rather than drawn by hand:

- "Home": the general overviews as tabs (Overview, Weather, Traffic, Network, Lights, Energy, Security).
- One dashboard per sector (Bedroom, Living, Kitchen), filled by Home Assistant from the area.

Dashboards made in the UI are left untouched. Home Assistant keeps storage dashboards in memory, so
run this on a copy of /config/.storage taken while the container is stopped:

    python build_home_dashboard.py <.storage dir>
"""

import json
import sys
import uuid
from pathlib import Path

storage = Path(sys.argv[1])


def entry(dash_id: str, title: str, icon: str) -> dict:
    return {
        "id": dash_id,
        "show_in_sidebar": True,
        "icon": icon,
        "title": title,
        "require_admin": False,
        "mode": "storage",
        "url_path": dash_id.replace("_", "-"),
    }


def write(dash_id: str, config: dict) -> None:
    (storage / f"lovelace.{dash_id}").write_text(
        json.dumps({"version": 1, "minor_version": 1, "key": f"lovelace.{dash_id}", "data": {"config": config}}, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )


def heading(text: str, style: str = "title") -> dict:
    return {"type": "heading", "heading": text, "heading_style": style}


def tile(entity: str, name: str, columns: int = 6, **extra) -> dict:
    return {"type": "tile", "entity": entity, "name": name, "grid_options": {"columns": columns}, **extra}


def section(*cards: dict, span: int = 1) -> dict:
    return {"type": "grid", "column_span": span, "cards": list(cards)}


# ----- Energy: what Projects/consumo-pc shows, from the sensors of packages/consumo.yaml
EQUIPOS = [("server", "Server", "sensor.bedroom_plug_server_power"), ("pc_main", "PC main", "sensor.bedroom_plug_pc_main_power"), ("ac", "AC", "sensor.bedroom_plug_ac_power")]


def equipo(key: str, nombre: str, power: str) -> dict:
    cards = [
        heading(nombre),
        tile(power, "Consumo ahora", 12, icon="mdi:flash", features=[{"type": "trend-graph", "hours_to_show": 24}]),
        tile(f"sensor.{key}_costo_por_hora", "Costo por hora"),
        tile(f"sensor.{key}_horas_hoy", "Encendido hoy", icon="mdi:timer-outline"),
        tile(f"sensor.{key}_costo_hoy", "Hoy"),
        tile(f"sensor.{key}_energia_hoy", "Energía hoy", icon="mdi:lightning-bolt"),
        tile(f"sensor.{key}_costo_mes", "Este mes"),
        tile(f"sensor.{key}_proyeccion_mes", "Proyección del mes"),
    ]
    if key == "server":
        # Only the PC that runs consumo-pc knows how its total splits
        cards += [
            heading("Desglose", "subtitle"),
            tile("sensor.server_cpu_potencia", "CPU", 4, icon="mdi:cpu-64-bit"),
            tile("sensor.server_gpu_potencia", "GPU", 4, icon="mdi:expansion-card"),
            tile("sensor.server_resto_potencia", "Resto", 4, icon="mdi:power-plug"),
        ]
    cards.append({"type": "statistics-graph", "title": "Energía por día", "entities": [f"sensor.{key}_energia"], "chart_type": "bar", "period": "day", "days_to_show": 30, "stat_types": ["change"]})
    return section(*cards)


NUCLEOS = """{% set n = state_attr('sensor.server_cpu_nucleos', 'nucleos') or [] %}
{{ state_attr('sensor.server_cpu_nucleos', 'nombre') }}

`{% for v in n %}{{ '▁▂▃▄▅▆▇█'[(v / 100 * 7) | round | int] }}{% endfor %}` uso por núcleo lógico"""

PROCESOS = """| Proceso | CPU | Memoria |
|:--|--:|--:|
{% for p in state_attr('sensor.server_procesos', 'procs') or [] -%}
| {{ p.nombre }}{{ ' ×%d' % p.n if p.n > 1 else '' }} | {{ p.cpu }} % | {{ (p.mem / 1048576) | round | int }} MB |
{% endfor %}"""

energy = {
    "title": "Energy",
    "path": "energy",
    "type": "sections",
    "max_columns": 4,
    "sections": [
        *(equipo(*e) for e in EQUIPOS),
        section(
            heading("Recursos"),
            {"type": "gauge", "entity": "sensor.server_cpu_uso", "name": "CPU", "min": 0, "max": 100, "grid_options": {"columns": 4}},
            {"type": "gauge", "entity": "sensor.server_gpu_uso", "name": "GPU", "min": 0, "max": 100, "grid_options": {"columns": 4}},
            {"type": "gauge", "entity": "sensor.server_ram_uso", "name": "Memoria", "min": 0, "max": 100, "grid_options": {"columns": 4}},
            {"type": "markdown", "content": NUCLEOS},
            tile("sensor.server_gpu_temperatura", "Temperatura GPU"),
            tile("sensor.server_vram_uso", "VRAM"),
            tile("sensor.server_ram_usada", "Memoria en uso"),
            tile("sensor.server_disco_c_uso", "Disco C"),
            tile("sensor.server_red_bajada", "Bajada"),
            tile("sensor.server_red_subida", "Subida"),
        ),
        section(
            heading("Procesos"),
            {"type": "markdown", "content": PROCESOS},
            heading("Tarifa"),
            tile("input_number.tarifa_precio_kwh", "Precio por kWh", 12, features=[{"type": "numeric-input", "style": "buttons"}]),
            tile("input_number.tarifa_impuestos_pct", "Impuestos", 12, features=[{"type": "numeric-input", "style": "buttons"}]),
            tile("sensor.tarifa_precio_final", "Precio final", 12),
            {"type": "markdown", "content": "Edenor, T1 - R1. El costo es el de los kWh que suma cada equipo; el cargo fijo no se incluye porque se paga igual."},
        ),
        section(
            heading("Histórico"),
            {"type": "statistics-graph", "title": "Potencia (24 h)", "entities": [e[2] for e in EQUIPOS], "chart_type": "line", "period": "5minute", "days_to_show": 1, "stat_types": ["mean"]},
            {"type": "statistics-graph", "title": "Energía por mes", "entities": [f"sensor.{e[0]}_energia" for e in EQUIPOS], "chart_type": "bar", "period": "month", "days_to_show": 365, "stat_types": ["change"]},
            span=2,
        ),
    ],
}

# ----- Weather: Open-Meteo through packages/clima.yaml, plus the BMP280 on the desk
# The two cards are not from HACS: download them into /config/www/weather-cards from
#   https://github.com/troinine/ha-weather-forecast-card/releases/latest/download/weather-forecast-card.js
#   https://github.com/timmaurice/lovelace-windy-card/releases/latest/download/windy-card.js
WEATHER_CARDS = ["weather-forecast-card.js", "windy-card.js"]


def windy(overlay: str, **extra) -> dict:
    return {"type": "custom:windy-card", "location": "zone.home", "overlay": overlay, "zoom": 7, "height": 420, "metric_wind": "km/h", "show_marker": True, "hide_message": True, "grid_options": {"columns": "full"}, **extra}


weather = {
    "title": "Weather",
    "path": "weather",
    "type": "sections",
    "max_columns": 4,
    "sections": [
        section(
            heading("Now"),
            {
                "type": "custom:weather-forecast-card",
                "entity": "weather.clima",
                "show_condition_effects": True,
                "default_forecast": "hourly",
                "forecast": {"mode": "chart", "extra_attribute": "precipitation_probability", "show_attribute_selector": True},
                "grid_options": {"columns": "full", "rows": "auto"},
            },
            span=2,
        ),
        section(
            heading("Conditions"),
            tile("sensor.clima_sensacion_termica", "Sensación térmica", icon="mdi:thermometer-lines"),
            tile("sensor.clima_humedad", "Humedad"),
            tile("sensor.clima_viento", "Viento", icon="mdi:weather-windy"),
            tile("sensor.clima_rafagas", "Ráfagas", icon="mdi:weather-windy-variant"),
            tile("sensor.clima_precipitacion", "Lluvia ahora", icon="mdi:weather-pouring"),
            tile("sensor.clima_nubosidad", "Nubosidad"),
            tile("sensor.clima_indice_uv", "Índice UV"),
            tile("sensor.clima_visibilidad", "Visibilidad", icon="mdi:eye-outline"),
            tile("sensor.clima_punto_de_rocio", "Punto de rocío", icon="mdi:water-thermometer-outline"),
            tile("sensor.clima_presion", "Presión", icon="mdi:gauge"),
        ),
        section(
            heading("Air & Sun"),
            tile("sensor.clima_calidad_del_aire", "Calidad del aire", 12, icon="mdi:air-filter"),
            tile("sensor.clima_pm2_5", "PM2.5"),
            tile("sensor.clima_pm10", "PM10"),
            tile("sensor.sun_next_rising", "Amanecer", icon="mdi:weather-sunset-up"),
            tile("sensor.sun_next_setting", "Atardecer", icon="mdi:weather-sunset-down"),
            heading("Station", "subtitle"),
            tile("sensor.bmp280_esp32_c3_temperatura", "Adentro", features=[{"type": "trend-graph", "hours_to_show": 24}]),
            tile("sensor.bmp280_esp32_c3_presion", "Barómetro", features=[{"type": "trend-graph", "hours_to_show": 24}]),
        ),
        section(heading("Radar"), windy("radar"), span=2),
        section(heading("Wind"), windy("wind", show_pressure=True), span=2),
        section(
            heading("Week"),
            {
                "type": "custom:weather-forecast-card",
                "entity": "weather.clima",
                "show_current": False,
                "forecast_types": "daily",
                "forecast": {"extra_attribute": "precipitation_probability"},
                "grid_options": {"columns": "full", "rows": "auto"},
            },
            span=2,
        ),
        section(
            heading("Trends"),
            {"type": "history-graph", "title": "Temperatura (48 h)", "hours_to_show": 48, "entities": [{"entity": "sensor.clima_temperatura", "name": "Afuera"}, {"entity": "sensor.clima_sensacion_termica", "name": "Sensación"}, {"entity": "sensor.bmp280_esp32_c3_temperatura", "name": "Adentro"}]},
            {"type": "history-graph", "title": "Presión (48 h)", "hours_to_show": 48, "entities": [{"entity": "sensor.bmp280_esp32_c3_presion", "name": "Barómetro"}, {"entity": "sensor.clima_presion", "name": "Nivel del mar"}]},
            span=2,
        ),
    ],
}
# ----- Traffic: Waze's live map (jams, accidents, closures), the default route of packages/ruta.yaml
# (TomTom, by motorcycle, with live traffic) and what the weather does to the road
# The maps are centred on the house, rounded to about a kilometre: the address is not Waze's business
home = json.loads((storage / "core.config").read_text(encoding="utf-8"))["data"]
CASA = (round(home["latitude"], 2), round(home["longitude"], 2))
CENTRO = (-34.6037, -58.3816)  # Obelisco


def waze_map(rows: int, zoom: int = 12, centre: tuple[float, float] = CASA) -> dict:
    url = f"https://embed.waze.com/iframe?zoom={zoom}&lat={centre[0]}&lon={centre[1]}&ct=livemap"
    return {"type": "iframe", "url": url, "aspect_ratio": "60%", "grid_options": {"columns": "full", "rows": rows}}


ROAD = [
    tile("sensor.clima_precipitacion", "Lluvia ahora", icon="mdi:weather-pouring"),
    tile("sensor.clima_visibilidad", "Visibilidad", icon="mdi:eye-outline"),
    tile("sensor.clima_viento", "Viento", icon="mdi:weather-windy"),
    tile("sensor.clima_rafagas", "Ráfagas", icon="mdi:weather-windy-variant"),
]

RUTA = [
    tile("sensor.ruta_tiempo", "Ruta en moto", icon="mdi:motorbike", features=[{"type": "trend-graph", "hours_to_show": 24}]),
    tile("sensor.ruta_demora", "Demora por tráfico", icon="mdi:car-brake-alert", features=[{"type": "trend-graph", "hours_to_show": 24}]),
    tile("sensor.ruta_distancia", "Distancia", 12, icon="mdi:map-marker-distance"),
    tile("sensor.ruta_en_moto", "Para salir en moto", 12, state_content=["state", "motivo"]),
]
# Where the two addresses landed, and the same trip in the maps that do know the traffic
RUTA_LINKS = """{% set o = states('input_text.ruta_origen') %}{% set d = states('input_text.ruta_destino') %}{% set ll = states('sensor.ruta_destino').split(',') -%}
**{{ o }}** → **{{ d }}**

Abrir en [Google Maps](https://www.google.com/maps/dir/?api=1&origin={{ o | urlencode }}&destination={{ d | urlencode }}&travelmode=driving){% if ll | count == 2 %} · [Waze](https://www.waze.com/ul?ll={{ ll[0] }}%2C{{ ll[1] }}&navigate=yes){% endif %}"""
RUTA_GEO = """Origen: {{ state_attr('sensor.ruta_origen', 'display_name') or 'dirección no encontrada' }}

Destino: {{ state_attr('sensor.ruta_destino', 'display_name') or 'dirección no encontrada' }}"""

traffic = {
    "title": "Traffic",
    "path": "traffic",
    "type": "sections",
    "max_columns": 4,
    "sections": [
        section(heading("Live map"), waze_map(9), span=3),
        section(
            heading("Route"),
            *RUTA,
            {"type": "markdown", "content": RUTA_LINKS},
            heading("Addresses", "subtitle"),
            {"type": "entities", "entities": ["input_text.ruta_origen", "input_text.ruta_destino"]},
            {"type": "markdown", "content": RUTA_GEO},
        ),
        section(heading("On the road"), *ROAD, tile("sensor.sun_next_setting", "Atardecer", 12, icon="mdi:weather-sunset-down")),
        section(heading("Neighbourhood"), waze_map(7, zoom=14), span=2),
        section(heading("City"), waze_map(7, centre=CENTRO), span=2),
    ],
}

# ----- Home
registry_path = storage / "lovelace_dashboards"
registry = json.loads(registry_path.read_text(encoding="utf-8"))


def first_view(dash_id: str) -> dict | None:
    source = storage / f"lovelace.{dash_id}"
    if not source.exists():
        return None
    views = (json.loads(source.read_text(encoding="utf-8"))["data"].get("config") or {}).get("views", [])
    return dict(views[0]) if views else None


# The general panel: a masthead (plate, name, almanac) and the handful of things worth a glance
views = [{
    "title": "Overview",
    "path": "overview",
    "type": "sections",
    "max_columns": 4,
    "sections": [
        section({"type": "custom:athanor-hero-card", "compact": True, "host": False, "prompt": False, "grid_options": {"columns": "full"}}, span=2),
        section(
            heading("House"),
            tile("sensor.system_monitor_uptime", "Uptime", 12, icon="mdi:timer-sand"),
            tile("sensor.server_cpu_uso", "CPU", icon="mdi:cpu-64-bit"),
            tile("sensor.server_ram_uso", "Memoria"),
            tile("sensor.server_gpu_temperatura", "GPU"),
            tile("sensor.server_disco_c_uso", "Disco C"),
            heading("Lights"),
            tile("light.cla60_smart_wifi", "Bedroom", 12, features=[{"type": "light-brightness"}]),
        ),
        section(
            heading("Network"),
            tile("switch.adguard_home_protection", "AdGuard", 12, icon="mdi:shield-check"),
            tile("sensor.adguard_home_dns_queries", "Consultas DNS", icon="mdi:dns"),
            tile("sensor.adguard_home_dns_queries_blocked_ratio", "Bloqueadas", icon="mdi:shield-off"),
            heading("Energy"),
            tile("sensor.bedroom_plug_server_power", "Server", icon="mdi:flash"),
            tile("sensor.bedroom_plug_pc_main_power", "PC main", icon="mdi:flash"),
            tile("sensor.server_costo_mes", "Server, mes"),
            tile("sensor.pc_main_costo_mes", "PC main, mes"),
        ),
        section(
            heading("Weather"),
            {
                "type": "custom:weather-forecast-card",
                "entity": "weather.clima",
                "forecast_types": "daily",
                "forecast": {"daily_slots": 5, "extra_attribute": "precipitation_probability"},
                "grid_options": {"columns": "full", "rows": "auto"},
            },
            tile("sensor.clima_sensacion_termica", "Sensación térmica", 4, icon="mdi:thermometer-lines"),
            tile("sensor.clima_viento", "Viento", 4, icon="mdi:weather-windy"),
            tile("sensor.clima_indice_uv", "Índice UV", 4),
            span=2,
        ),
        section(heading("Traffic"), *RUTA, {"type": "markdown", "content": RUTA_LINKS, "grid_options": {"columns": "full"}}, waze_map(5), *ROAD[:2], span=2),
    ],
}]
# Network is the view drawn by hand in the Network dashboard (AdGuard), shown here as a copy.
# No icon on any tab: a tab with an icon hides its title, and the top bar is a row of words
network = first_view("dashboard_network")
if network:
    network.pop("icon", None)
    views.append({**network, "title": "Network", "path": "network"})
views[1:1] = [weather, traffic]
views += [
    # Filled by Home Assistant: every light, and every camera, lock and alarm, as they are added
    {"title": "Lights", "path": "lights", "strategy": {"type": "light"}},
    energy,
    {"title": "Security", "path": "security", "strategy": {"type": "security"}},
]

generated = [entry("dashboard_home", "Home", "mdi:home")]
write("dashboard_home", {"views": views})

# ----- Sectors: one dashboard each in the sidebar, filled from the area's devices
for area, title, icon in [("bedroom", "Bedroom", "mdi:bed"), ("living_room", "Living", "mdi:sofa"), ("kitchen", "Kitchen", "mdi:silverware-fork-knife")]:
    dash_id = f"dashboard_{area.split('_')[0]}"
    generated.append(entry(dash_id, title, icon))
    write(dash_id, {"views": [{"title": title, "path": area.split("_")[0], "strategy": {"type": "area", "area": area}}]})

resources_path = storage / "lovelace_resources"
resources = json.loads(resources_path.read_text(encoding="utf-8"))
for name in WEATHER_CARDS:
    url = f"/local/weather-cards/{name}"
    if not any(r["url"].split("?")[0] == url for r in resources["data"]["items"]):
        resources["data"]["items"].append({"id": uuid.uuid4().hex, "url": url, "type": "module"})
resources_path.write_text(json.dumps(resources, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

ids = {g["id"] for g in generated}
registry["data"]["items"] = [i for i in registry["data"]["items"] if i["id"] not in ids] + generated
registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

print("Home:", [v["title"] for v in views])
print("Sidebar:", [(i["url_path"], i["title"]) for i in registry["data"]["items"]])
