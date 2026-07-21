from __future__ import annotations

import asyncio
import os
from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.runtime import WorkerRuntime


def _live_model() -> dict[str, object] | None:
    provider = os.getenv("INQUIRA_E2E_PROVIDER", "").strip().lower()
    model = os.getenv("INQUIRA_E2E_MODEL", "").strip()
    api_key = os.getenv("INQUIRA_E2E_API_KEY", "")
    if not provider or not model or (provider != "ollama" and not api_key.strip()):
        return None
    default_urls = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "anthropic": "",
        "ollama": "http://localhost:11434",
    }
    return {
        "provider": provider,
        "model": model,
        "lite_model": os.getenv("INQUIRA_E2E_LITE_MODEL", model).strip() or model,
        "coding_model": os.getenv("INQUIRA_E2E_CODING_MODEL", model).strip() or model,
        "api_key": api_key,
        "base_url": os.getenv("INQUIRA_E2E_BASE_URL", default_urls.get(provider, "")).strip(),
        "temperature": 0,
        "max_tokens": 2048,
        "top_p": 1,
        "allow_data_samples": False,
    }


@pytest.mark.skipif(_live_model() is None, reason="live provider credentials are not configured")
def test_live_provider_runs_through_langgraph_worker(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        connection = duckdb.connect(str(catalog))
        connection.close()
        runtime = WorkerRuntime()
        events: list[dict] = []
        try:
            response = await runtime.handle({
                "id": "live-provider",
                "method": "agent_analyze",
                "params": {
                    "workspace_id": "workspace-live",
                    "database_path": str(catalog),
                    "question": "Reply with a short greeting. Do not analyze data.",
                    "run_id": "live-provider",
                    "artifact_dir": str((tmp_path / "artifacts").resolve()),
                    "timeout_seconds": 120,
                    "model": _live_model(),
                    "schema": {"context": "", "tables": []},
                    "context": {"turns": []},
                },
            }, events.append)
        finally:
            await runtime.shutdown()
        assert response["error"] is None, response
        assert response["result"]["success"] is True, response
        assert response["result"]["answer"].strip()
        assert any(event.get("type") == "agent_status" for event in events)

    asyncio.run(scenario())
