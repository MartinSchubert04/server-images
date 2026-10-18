"""Guarda kd.json como config de un dashboard y, si se pide, recarga TouchKio.

    python3 save_dashboard.py kd.json <url_path> [<boton de refresh>]

Corre dentro del contenedor de HA (usa su aiohttp). El token llega por la variable
HA_TOKEN, nunca por argumentos, para que no quede en la lista de procesos.
"""
import asyncio
import json
import os
import sys

import aiohttp

URL = "ws://localhost:8123/api/websocket"


async def main(path: str, url_path: str, refresh: str | None) -> None:
    config = json.load(open(path, encoding="utf-8"))
    async with aiohttp.ClientSession() as session, session.ws_connect(URL) as ws:
        await ws.receive_json()  # auth_required
        await ws.send_json({"type": "auth", "access_token": os.environ["HA_TOKEN"]})
        if (await ws.receive_json())["type"] != "auth_ok":
            sys.exit("Token rechazado: revisá HA_TOKEN en home-assistant/.env")
        msgs = [{"type": "lovelace/config/save", "url_path": url_path, "config": config}]
        if refresh:
            msgs.append({"type": "call_service", "domain": "button", "service": "press",
                         "target": {"entity_id": refresh}})
        for i, msg in enumerate(msgs, start=1):
            await ws.send_json({"id": i, **msg})
            res = await ws.receive_json()
            if not res.get("success"):
                sys.exit(f"Falló {msg['type']}: {res.get('error')}")
    print(f"Dashboard {url_path} guardado" + (" y kiosco recargado." if refresh else "."))


asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
