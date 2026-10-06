"""The connection to Home Assistant.

Inside Home Assistant the Supervisor proxies the API and hands the app SUPERVISOR_TOKEN;
nobody creates a token. On a computer the URL comes from HTD_HA_URL and the token from
the keychain (standalone/connect.py puts it there).

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import aiohttp

import credentials


@dataclass(frozen=True)
class Connection:
    rest: str        # ends with /api
    websocket: str
    token: str

    def __repr__(self) -> str:  # never print the token
        return "Connection(rest=%r)" % self.rest


def websocket_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base[len("https://"):] + "/api/websocket"
    if base.startswith("http://"):
        return "ws://" + base[len("http://"):] + "/api/websocket"
    raise ValueError("Home Assistant URL must start with http:// or https://")


def connection_from_environment(env=None, store=None) -> Connection:
    env = os.environ if env is None else env
    token = env.get("SUPERVISOR_TOKEN", "")
    if token:
        return Connection("http://supervisor/core/api", "ws://supervisor/core/websocket", token)
    url = env.get("HTD_HA_URL", "").rstrip("/")
    secret = store.get(credentials.HOME_ASSISTANT_TOKEN) if store else ""
    if url and secret:
        return Connection(url + "/api", websocket_url(url), secret)
    raise RuntimeError("No connection to Home Assistant configured. On a computer, run "
                       "standalone/connect.py first.")


class Socket:
    """Home Assistant's WebSocket API: states, events, actions."""

    def __init__(self, ws):
        self.ws = ws
        self._next_id = 1

    @classmethod
    async def connect(cls, connection: Connection, connect=None):
        if connect is None:
            import websockets
            connect = websockets.connect
        ws = await connect(connection.websocket, max_size=None, ping_interval=30)
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": connection.token}))
        answer = json.loads(await ws.recv())
        if answer.get("type") != "auth_ok":
            await ws.close()
            raise RuntimeError("Home Assistant refused the token (%s)" % answer.get("type"))
        return cls(ws)

    async def request(self, message: dict) -> dict:
        """Sends a command and waits for its result; events that arrive meanwhile are dropped."""
        message_id = self._send_id()
        await self.ws.send(json.dumps(dict(message, id=message_id)))
        while True:
            data = json.loads(await self.ws.recv())
            if data.get("id") == message_id and data.get("type") == "result":
                return data

    def _send_id(self) -> int:
        self._next_id += 1
        return self._next_id

    async def states(self) -> dict:
        result = await self.request({"type": "get_states"})
        return {item["entity_id"]: item for item in result.get("result") or []}

    async def language(self) -> str:
        result = await self.request({"type": "get_config"})
        return (result.get("result") or {}).get("language", "")

    async def subscribe_state_changes(self) -> None:
        await self.request({"type": "subscribe_events", "event_type": "state_changed"})

    async def call_action(self, action: str, data: dict) -> None:
        domain, name = action.split(".", 1)
        await self.ws.send(json.dumps({"id": self._send_id(), "type": "call_service",
                                       "domain": domain, "service": name, "service_data": data}))

    async def receive(self):
        return json.loads(await self.ws.recv())


async def fetch_json(connection: Connection, path: str, timeout: float = 10):
    """GET <rest>/<path> with the token; None if Home Assistant is not reachable."""
    headers = {"Authorization": "Bearer " + connection.token}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(connection.rest + path, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.json()
    except (aiohttp.ClientError, OSError, ValueError, TimeoutError):
        pass
    return None
