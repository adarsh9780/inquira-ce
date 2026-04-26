from __future__ import annotations

import json
from pathlib import Path


def test_agent_manifest_does_not_expose_pip_install_tool() -> None:
    manifest_path = Path(__file__).resolve().parents[1] / "agent_v2" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "pip_install" not in manifest.get("tools", [])


def test_agent_runtime_has_no_pip_install_tool_module() -> None:
    tool_path = Path(__file__).resolve().parents[1] / "agent_v2" / "tools" / "pip_install.py"

    assert not tool_path.exists()
