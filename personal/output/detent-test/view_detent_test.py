"""Open this file in VS Code and Run Without Debugging (Ctrl+F5) to push
detent_test into the OCP CAD Viewer panel.

build_detent_test.py is written for build123d-mcp's execute() sandbox, which
injects its own show(shape, name=None) into the namespace before running the
script (see session.py). This runs that same, unmodified file standalone by
injecting a matching show() that forwards to ocp_vscode instead -- so the one
script still works for both "paste into execute()" and "run in VS Code".

Having `import ocp_vscode` here also satisfies OCP CAD Viewer's default
autostartTriggers, so just opening this file starts the viewer panel if it
isn't already running.
"""

import runpy
from pathlib import Path

import ocp_vscode


def _show(shape, name: str | None = None) -> None:
    ocp_vscode.show(shape, names=[name or "shape"])


runpy.run_path(
    str(Path(__file__).parent / "build_detent_test.py"),
    init_globals={"show": _show},
    run_name="build_detent_test",
)
