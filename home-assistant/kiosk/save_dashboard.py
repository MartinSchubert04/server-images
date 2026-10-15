"""Guarda kd.json como config del dashboard del kiosco y recarga TouchKio.

Corre dentro del contenedor de HA (usa su aiohttp). El token llega por la variable
HA_TOKEN, nunca por argumentos, para que no quede en la lista de procesos.
"""
import asyncio
import json
import os
import sys

import aiohttp

URL = "ws://localhost:8123/api/websocket"


async def main(path: str) -> None:
    config = json.load(open(path, encoding="utf-8"))
    async with aiohttp.ClientSession() as session, session.ws_connect(URL) as ws:
        await ws.receive_json()  # auth_required
        await ws.send_json({"type": "auth", "access_token": os.environ["HA_TOKEN"]})
        if (await ws.receive_json())["type"] != "auth_ok":
            sys.exit("Token rechazado: revisá HA_TOKEN en home-assistant/.env")
        msgs = [
            {"type": "lovelace/config/save", "url_path": "dashboard-kiosk", "config": config},
            {"type": "call_service", "domain": "button", "service": "press",
             "target": {"entity_id": "button.touchkio_mrtn_hub_refresh"}},
        ]
        for i, msg in enumerate(msgs, start=1):
            await ws.send_json({"id": i, **msg})
            res = await ws.receive_json()
            if not res.get("success"):
                sys.exit(f"Falló {msg['type']}: {res.get('error')}")
    print("Dashboard guardado y kiosco recargado.")


asyncio.run(main(sys.argv[1]))
