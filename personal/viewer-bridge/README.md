# viewer-bridge

Bridges build123d-mcp's live viewer Unix Domain Socket to a browser, since the
protocol is POSIX/UDS-only (`docs/live-viewer.md` upstream: "A remote or
headless host would need a UDS to WebSocket or TCP bridge, which is not
included here"). Localhost-only by design — see the module docstring in
`bridge.py` for the security rationale.

## Run

1. Start the MCP server with the viewer socket enabled:
   ```
   uv run build123d-mcp --viewer-socket /tmp/b123d.sock
   ```
2. Start the bridge (not a build123d-mcp dependency, so pull `websockets` in ad hoc):
   ```
   uv run --with websockets python personal/viewer-bridge/bridge.py \
       --socket /tmp/b123d.sock --token mysecret
   ```
   Omit `--token` to have one generated and printed for you.
3. Open the URL the bridge logs, e.g. `http://127.0.0.1:8080/viewer.html?token=mysecret`.

Drive the MCP session as usual (`execute()` + `show(shape, name=...)`) and the
browser view updates live. Opening a second tab replays the current full
scene immediately (the bridge keeps its own cache since the UDS side only
sends a full dump once per connection, not once per browser tab).

## Notes

- If the server restarts, the bridge detects the UDS disconnect, broadcasts a
  `RESET` to every connected browser (shown as a "reconnecting" status
  instead of stale geometry), and reconnects automatically once the socket
  reappears.
- Wrong/missing `?token=` is rejected at the WebSocket handshake (close code
  1008) before any relay work happens.
- Default ports: `--ws-port 8765` (the WebSocket relay), `--static-port 8080`
  (serves `static/viewer.html`). If you change `--ws-port`, add `&ws=host:port`
  to the viewer URL to match.
- Not wired into `pyproject.toml` dependencies or CI on purpose — see
  `../MY_CAD_WORKFLOW.md` and the repo root branch-structure notes for why
  fork-only code lives under `personal/`.
