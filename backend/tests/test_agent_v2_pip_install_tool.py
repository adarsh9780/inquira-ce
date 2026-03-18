from types import SimpleNamespace

import pytest

from app.agent_v2.events import reset_agent_event_emitter, set_agent_event_emitter
from app.agent_v2.tools.pip_install import pip_install


class _FakeBroker:
    async def create_request(self, **kwargs):
        return SimpleNamespace(
            id="int-1",
            prompt=kwargs["prompt"],
            options=list(kwargs["options"]),
            multi_select=kwargs["multi_select"],
            timeout_sec=kwargs["timeout_sec"],
        )

    async def await_response(self, **_kwargs):
        return {"selected": ["statsmodels"], "timed_out": False, "status": "submitted"}


@pytest.mark.asyncio
async def test_pip_install_uses_intervention_and_emits_events(monkeypatch):
    events: list[tuple[str, dict]] = []

    def _emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    emitter_token = set_agent_event_emitter(_emit)
    calls = {"installed": [], "reset": 0, "bootstrap": 0}

    def fake_install_runner_package(*args, **kwargs):
        _ = args
        calls["installed"].append(kwargs.get("package_spec") or (args[1] if len(args) > 1 else ""))
        return SimpleNamespace(stdout="Installed statsmodels", stderr="")

    async def fake_reset_workspace_kernel(_workspace_id: str):
        calls["reset"] += 1
        return True

    async def fake_bootstrap_workspace_runtime(*, workspace_id: str, workspace_duckdb_path: str, progress_callback=None):
        _ = workspace_id, workspace_duckdb_path, progress_callback
        calls["bootstrap"] += 1
        return True

    monkeypatch.setattr("app.agent_v2.tools.pip_install.get_agent_intervention_service", lambda: _FakeBroker())
    monkeypatch.setattr("app.agent_v2.tools.pip_install.install_runner_package", fake_install_runner_package)
    monkeypatch.setattr("app.agent_v2.tools.pip_install.reset_workspace_kernel", fake_reset_workspace_kernel)
    monkeypatch.setattr("app.agent_v2.tools.pip_install.bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    result = await pip_install(
        user_id="user-1",
        workspace_id="ws-1",
        data_path="/tmp/ws.duckdb",
        packages=["statsmodels"],
    )

    reset_agent_event_emitter(emitter_token)

    assert result["installed"] == ["statsmodels"]
    assert calls["installed"] == ["statsmodels"]
    assert calls["reset"] == 1
    assert calls["bootstrap"] == 1
    assert any(event == "intervention_request" for event, _ in events)
    assert any(event == "tool_progress" for event, _ in events)
    assert any(event == "tool_result" and payload.get("status") == "success" for event, payload in events)
