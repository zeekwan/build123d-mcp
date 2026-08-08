# My CAD workflow (build123d-mcp)

Personal notes on how I actually use this server day to day. Not upstream documentation — lives on the `mine` branch only.

## Loop

1. **Sketch with measurements** — rough sketch on paper/tablet with real dimensions, not just a shape idea.
2. **Build incrementally** — Claude drives `execute()` against a persistent session, building the part up in stages rather than one big script.
3. **Validate numerically** — volume, bounding box, topology, watertightness checks via the server's own tools (`measure`, `validate`, `design_audit`). Deliberately **no rendered previews** during this loop: they cost tokens and aren't useful context since I review the actual file myself, not a screenshot.
4. **Export** — STEP (for future edits/interop) + 3MF (for Bambu Studio).
5. **Review locally** — open the exported files myself, outside the agent loop.
6. **Approve → slice → print.**

## Why no render step

Rendered previews add token spend for a signal I don't need — I'm going to open the real file anyway before printing. The numeric checks (volume/bbox/topology/watertightness) catch the failure modes that actually matter (non-manifold geometry, wrong dimensions, disconnected solids) without needing a picture.

## Output files

Finished parts land in `personal/output/<project-name>/` (STEP + 3MF), committed to the `mine` branch so `git fetch && git reset --hard origin/mine` on another machine gets them too. See the repo root `README`-equivalent (this fork's own docs) for the branch/rebase setup — `mine` tracks `main`, `main` mirrors `pzfreo/build123d-mcp` upstream.

## Live viewer (in progress)

Working on a browser-based live viewer: `build123d-mcp` already streams glTF updates over a Unix Domain Socket for local clients; `personal/viewer-bridge/` adds a small WebSocket bridge + three.js page so the model can be watched updating live from a browser instead of a local pyvista client. See `personal/viewer-bridge/README.md`.
