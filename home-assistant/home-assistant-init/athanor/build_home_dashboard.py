"""Builds the dashboards that are generated rather than drawn by hand:

- "Home": the general overviews as tabs (Scriptorium, Network, Lights, Energy, Security).
- One dashboard per sector (Bedroom, Living, Kitchen), filled by Home Assistant from the area.

Dashboards made in the UI are left untouched. Home Assistant keeps storage dashboards in memory, so
run this on a copy of /config/.storage taken while the container is stopped:

    python build_home_dashboard.py <.storage dir>
"""

import json
import sys
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

# ----- Home
registry_path = storage / "lovelace_dashboards"
registry = json.loads(registry_path.read_text(encoding="utf-8"))


def first_view(dash_id: str) -> dict | None:
    source = storage / f"lovelace.{dash_id}"
    if not source.exists():
        return None
    views = (json.loads(source.read_text(encoding="utf-8"))["data"].get("config") or {}).get("views", [])
    return dict(views[0]) if views else None


# The first room: a masthead (plate, name, almanac) and the handful of things worth a glance
views = [{
    "title": "Scriptorium",
    "path": "scriptorium",
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
    ],
}]
# Network is the view drawn by hand in the Network dashboard (AdGuard), shown here as a copy.
# No icon on any tab: a tab with an icon hides its title, and the top bar is a row of words
network = first_view("dashboard_network")
if network:
    network.pop("icon", None)
    views.append({**network, "title": "Network", "path": "network"})
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

ids = {g["id"] for g in generated}
registry["data"]["items"] = [i for i in registry["data"]["items"] if i["id"] not in ids] + generated
registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

print("Home:", [v["title"] for v in views])
print("Sidebar:", [(i["url_path"], i["title"]) for i in registry["data"]["items"]])
