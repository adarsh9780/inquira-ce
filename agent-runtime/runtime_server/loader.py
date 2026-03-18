from __future__ import annotations

import importlib
from typing import Any


def load_agent_graph(agent_name: str) -> Any:
    module_name = f"{agent_name}.graph"
    mod = importlib.import_module(module_name)
    build_graph = getattr(mod, "build_graph", None)
    if not callable(build_graph):
        raise RuntimeError(f"Agent profile '{agent_name}' does not expose build_graph")
    return build_graph()
