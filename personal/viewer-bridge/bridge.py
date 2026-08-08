#!/usr/bin/env python3
"""UDS -> WebSocket bridge for the build123d-mcp live viewer.

build123d-mcp streams live glTF scene updates over a Unix Domain Socket
(docs/live-viewer.md upstream), which is POSIX-only and has no browser client.
This bridge makes one UDS connection to the server's --viewer-socket, keeps a
scene cache (since the UDS side only sends a full dump once per connection,
but this process serves many browser tabs), and relays events to any number
of WebSocket-connected browsers running static/viewer.html.

Localhost-only by design: binds 127.0.0.1, plain ws://+http://, auth is a
shared-secret token in the WebSocket URL query string (browsers cannot set
custom headers on a WebSocket handshake). Do not bind beyond loopback without
adding TLS -- the token would otherwise travel in cleartext.

Usage:
    uv run --with websockets python personal/viewer-bridge/bridge.py \\
        --socket /tmp/b123d.sock --token mysecret

Requires the `websockets` package (not a build123d-mcp dependency -- kept out
of pyproject.toml deliberately, see personal/viewer-bridge/README.md).
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import http.server
import json
import logging
import os
import secrets
import threading
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.server import ServerConnection

from uds_protocol import Header, read_frame

logger = logging.getLogger("viewer_bridge")

STATIC_DIR = Path(__file__).parent / "static"
QUEUE_MAXSIZE = 256
RECONNECT_DELAY = 0.5


class SceneCache:
    """Tracks the last-known scene so late-joining browsers can be caught up.

    The UDS server sends a full dump (HELLO + one UPSERT per shape) once per
    *connection*. This bridge makes a single UDS connection but serves many
    browser clients, so it must replay an equivalent dump itself.
    """

    def __init__(self) -> None:
        self.session_id: str | None = None
        self._shapes: dict[str, tuple[Header, bytes]] = {}

    def apply(self, header: Header, payload: bytes) -> None:
        etype = header.get("type")
        if etype == "HELLO":
            self.session_id = header.get("session_id")
            self._shapes.clear()
        elif etype == "UPSERT":
            name = header.get("name", "")
            self._shapes[name] = (header, payload)
        elif etype == "REMOVE":
            self._shapes.pop(header.get("name", ""), None)
        elif etype == "RESET":
            self._shapes.clear()

    def replay(self) -> list[tuple[Header, bytes]]:
        """A synthetic HELLO + one UPSERT per known shape, for a new client."""
        events: list[tuple[Header, bytes]] = []
        if self.session_id is not None:
            events.append(({"type": "HELLO", "session_id": self.session_id, "seq": -1}, b""))
        events.extend(self._shapes.values())
        return events


class BrowserClient:
    """One connected browser tab: a bounded, drop-oldest outgoing queue."""

    def __init__(self, websocket: ServerConnection) -> None:
        self.websocket = websocket
        self.queue: asyncio.Queue[tuple[Header, bytes]] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)

    def enqueue(self, header: Header, payload: bytes) -> None:
        if self.queue.full():
            try:
                self.queue.get_nowait()  # drop oldest to make room
            except asyncio.QueueEmpty:
                pass
        self.queue.put_nowait((header, payload))

    async def sender_loop(self) -> None:
        while True:
            header, payload = await self.queue.get()
            await _send_event(self.websocket, header, payload)


async def _send_event(websocket: ServerConnection, header: Header, payload: bytes) -> None:
    await websocket.send(json.dumps(header))
    if header.get("type") == "UPSERT" and payload:
        await websocket.send(payload)


def _extract_query(websocket: ServerConnection) -> dict[str, list[str]]:
    # websockets' Request object shape has moved across major versions; try
    # the current asyncio-implementation attribute first, then the legacy one,
    # rather than pinning an exact version.
    request = getattr(websocket, "request", None)
    path = request.path if request is not None else getattr(websocket, "path", "")
    return parse_qs(urlparse(path).query)


class Bridge:
    def __init__(self, socket_path: str, token: str) -> None:
        self.socket_path = socket_path
        self.token = token
        self.cache = SceneCache()
        self.clients: set[BrowserClient] = set()

    def _broadcast(self, header: Header, payload: bytes) -> None:
        self.cache.apply(header, payload)
        for client in list(self.clients):
            client.enqueue(header, payload)

    async def _connect_uds(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        announced = False
        while True:
            try:
                return await asyncio.open_unix_connection(self.socket_path)
            except (FileNotFoundError, ConnectionRefusedError):
                if not announced:
                    logger.info("waiting for UDS at %s ...", self.socket_path)
                    announced = True
                await asyncio.sleep(0.2)

    async def uds_reader_loop(self) -> None:
        while True:
            reader, writer = await self._connect_uds()
            logger.info("connected to UDS %s", self.socket_path)
            try:
                while True:
                    header, payload = await read_frame(reader)
                    self._broadcast(header, payload)
            except (asyncio.IncompleteReadError, ConnectionError, OSError) as exc:
                logger.warning("UDS disconnected: %s", exc)
            finally:
                writer.close()

            # Server went away (restart/crash): tell every browser the scene is
            # stale so nothing shows frozen geometry while we reconnect.
            self._broadcast({"type": "RESET", "seq": -1}, b"")
            await asyncio.sleep(RECONNECT_DELAY)

    async def ws_handler(self, websocket: ServerConnection) -> None:
        query = _extract_query(websocket)
        token = (query.get("token") or [None])[0]
        if not token or not hmac.compare_digest(token, self.token):
            logger.warning("rejected WS connection: bad/missing token")
            await websocket.close(code=1008, reason="invalid token")
            return

        client = BrowserClient(websocket)
        self.clients.add(client)
        logger.info("browser connected (%d total)", len(self.clients))
        try:
            for header, payload in self.cache.replay():
                await _send_event(websocket, header, payload)
            await client.sender_loop()
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(client)
            logger.info("browser disconnected (%d total)", len(self.clients))

    async def run(self, ws_host: str, ws_port: int) -> None:
        async with websockets.serve(self.ws_handler, ws_host, ws_port):
            logger.info("WS listening on ws://%s:%d", ws_host, ws_port)
            await self.uds_reader_loop()


def _serve_static(host: str, port: int) -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(STATIC_DIR))
    server = http.server.ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("static files at http://%s:%d/viewer.html", host, port)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--socket",
        default=os.environ.get("BUILD123D_VIEWER_SOCKET"),
        help="path to the build123d-mcp viewer UDS (or BUILD123D_VIEWER_SOCKET)",
    )
    parser.add_argument("--ws-host", default="127.0.0.1")
    parser.add_argument("--ws-port", type=int, default=8765)
    parser.add_argument("--static-host", default="127.0.0.1")
    parser.add_argument("--static-port", type=int, default=8080)
    parser.add_argument(
        "--token",
        default=os.environ.get("VIEWER_BRIDGE_TOKEN"),
        help="shared secret required in ?token= (or VIEWER_BRIDGE_TOKEN); generated if omitted",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.socket:
        parser.error("--socket or BUILD123D_VIEWER_SOCKET is required")

    token = args.token or secrets.token_urlsafe(24)
    if not args.token:
        logger.warning("no --token given; generated one for this run")

    _serve_static(args.static_host, args.static_port)
    url = f"http://{args.static_host}:{args.static_port}/viewer.html?token={token}"
    logger.info("open %s", url)

    bridge = Bridge(args.socket, token)
    try:
        asyncio.run(bridge.run(args.ws_host, args.ws_port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
