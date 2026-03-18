import json
from pathlib import Path


def test_langgraph_config_exposes_agent_v2_only() -> None:
    config_path = Path(__file__).resolve().parents[1] / "langgraph.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))

    graphs = data.get("graphs") if isinstance(data, dict) else {}
    assert isinstance(graphs, dict)
    assert graphs == {"agent_v2": "agent_v2.graph:build_graph"}
