from app.services import workspace_resource_monitor as monitor


def test_resource_recommendation_prompts_for_idle_workspaces_under_memory_pressure(monkeypatch):
    monkeypatch.setattr(
        monitor,
        "get_memory_snapshot",
        lambda: monitor.MemorySnapshot(
            available_bytes=512 * 1024 * 1024,
            total_bytes=8 * 1024 * 1024 * 1024,
            available_percent=6.25,
        ),
    )

    payload = monitor.build_workspace_resource_recommendation(
        runtime_snapshots=[
            {
                "workspace_id": "ws-idle",
                "status": "ready",
                "idle_seconds": 45 * 60,
                "last_used_at": "2026-06-21T00:00:00+00:00",
            },
            {
                "workspace_id": "ws-busy",
                "status": "busy",
                "idle_seconds": 45 * 60,
            },
        ],
        workspace_names={"ws-idle": "Idle Workspace", "ws-busy": "Busy Workspace"},
        idle_warning_minutes=20,
        min_available_percent=15.0,
        min_available_bytes=2 * 1024 * 1024 * 1024,
    )

    assert payload["type"] == "workspace_resource_recommendation"
    assert payload["memory_pressure"] is True
    assert [candidate["workspace_id"] for candidate in payload["candidates"]] == ["ws-idle"]
    assert payload["candidates"][0]["workspace_name"] == "Idle Workspace"


def test_resource_recommendation_is_prompt_only_when_memory_is_healthy(monkeypatch):
    monkeypatch.setattr(
        monitor,
        "get_memory_snapshot",
        lambda: monitor.MemorySnapshot(
            available_bytes=6 * 1024 * 1024 * 1024,
            total_bytes=8 * 1024 * 1024 * 1024,
            available_percent=75.0,
        ),
    )

    payload = monitor.build_workspace_resource_recommendation(
        runtime_snapshots=[
            {
                "workspace_id": "ws-idle",
                "status": "ready",
                "idle_seconds": 45 * 60,
            },
        ],
    )

    assert payload["memory_pressure"] is False
    assert payload["candidates"] == []
