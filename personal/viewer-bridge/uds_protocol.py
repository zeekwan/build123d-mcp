"""Async framing for the build123d-mcp live-viewer UDS protocol.

Vendored (not imported) from examples/live_viewer_client.py's framing logic in
the upstream repo, ported to asyncio.StreamReader. Kept as a standalone copy
so personal/ has zero coupling to examples/ changing shape upstream.

Wire format per frame (see docs/live-viewer.md upstream):
    [u32 BE json_len][utf-8 json header][u32 BE bin_len][binary payload]

Header fields: {type, session_id, seq, name?, units: "mm"}
type in {"HELLO", "UPSERT", "REMOVE", "RESET"}. UPSERT's payload is a
complete, standalone glTF-binary (.glb) blob; the other types carry no
payload (bin_len == 0).
"""

import asyncio
import json
import struct

Header = dict
Frame = tuple[Header, bytes]


async def read_frame(reader: asyncio.StreamReader) -> Frame:
    """Read one length-prefixed frame from an open UDS connection.

    Raises asyncio.IncompleteReadError if the connection closes mid-frame
    (including cleanly at a frame boundary, since readexactly(4) for the next
    header length will fail first).
    """
    (json_len,) = struct.unpack(">I", await reader.readexactly(4))
    header: Header = json.loads((await reader.readexactly(json_len)).decode("utf-8"))
    (bin_len,) = struct.unpack(">I", await reader.readexactly(4))
    payload = await reader.readexactly(bin_len) if bin_len else b""
    return header, payload
