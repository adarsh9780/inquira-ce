from types import SimpleNamespace
from pathlib import Path

import pytest

from app.services.execution_config import load_execution_runtime_config
from app.v1.api import runtime as runtime_api


@pytest.fixture(autouse=True)
def _force_local_jupyter_provider(monkeypatch):
    load_execution_runtime_config.cache_clear()
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_jupyter")
    monkeypatch.setenv("INQUIRA_TERMINAL_ENABLE", "true")
    yield
    load_execution_runtime_config.cache_clear()


@pytest.mark.asyncio
async def test_execute_workspace_code_passes_workspace_context(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws1"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return workspace

    captured = {}

    async def fake_execute_code_with_workspace(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        captured["code"] = code
        captured["timeout"] = timeout
        captured["working_dir"] = working_dir
        captured["workspace_id"] = workspace_id
        captured["workspace_duckdb_path"] = workspace_duckdb_path
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code_with_workspace)

    payload = runtime_api.ExecuteRequest(code="result = conn.sql('select 1').fetchall()", timeout=30)
    current_user = SimpleNamespace(id="user-1")

    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-1",
        payload=payload,
        session=object(),
        current_user=current_user,
    )

    assert response.success is True
    assert "set_active_run('" in captured["code"]
    assert "artifact_dir=None" in captured["code"]
    assert "result = conn.sql('select 1').fetchall()" in captured["code"]
    assert "export_dataframe" not in captured["code"]
    assert captured["working_dir"] == str(Path(duckdb_path).parent)
    assert captured["workspace_id"] == "ws-1"
    assert captured["workspace_duckdb_path"] == str(duckdb_path)
    assert isinstance(response.run_id, str)
    assert response.artifacts == []


@pytest.mark.asyncio
async def test_execute_workspace_code_defaults_artifact_dir_for_turn_rerun(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-turn-rerun"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    captured = {}

    async def fake_execute_code_with_workspace(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        captured["code"] = code
        _ = (timeout, working_dir, workspace_id, workspace_duckdb_path)
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
            "artifacts": [],
        }

    async def fake_persist_runtime_execution_to_turn(**kwargs):
        captured["persist"] = kwargs

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code_with_workspace)
    monkeypatch.setattr(runtime_api, "_persist_runtime_execution_to_turn", fake_persist_runtime_execution_to_turn)

    payload = runtime_api.ExecuteRequest(
        code="result_df = conn.sql('select 1 as a').df()",
        timeout=30,
        conversation_id="conv-1",
        turn_id="turn-1",
    )
    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-1",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1", username="alice"),
    )

    assert response.success is True
    wrapped = str(captured["code"])
    expected_dir = runtime_api.TurnBundleService.build_turn_artifacts_dir(
        "user-1",
        "ws-1",
        "conv-1",
        "turn-1",
    )
    assert f"artifact_dir='{expected_dir}'" in wrapped
    assert "export_dataframe" in wrapped
    assert captured["persist"]["conversation_id"] == "conv-1"
    assert captured["persist"]["turn_id"] == "turn-1"


@pytest.mark.asyncio
async def test_execute_workspace_code_rejects_client_owned_artifact_directory(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-client-artifact-dir"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.db"
    duckdb_path.touch()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.execute_workspace_code(
            workspace_id="ws-client-artifact-dir",
            payload=runtime_api.ExecuteRequest(
                code="print('unsafe')",
                artifact_dir=str(tmp_path / "external"),
            ),
            session=object(),
            current_user=SimpleNamespace(id="user-1", username="alice"),
        )

    assert exc.value.status_code == 400
    assert "server-managed" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_execute_workspace_code_wraps_arbitrary_dataframe_variable_name(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws1-any-var"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    captured = {}

    async def fake_execute_code_with_workspace(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        captured["code"] = code
        _ = (timeout, working_dir, workspace_id, workspace_duckdb_path)
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code_with_workspace)
    async def fake_persist_runtime_execution_to_turn(**kwargs):
        _ = kwargs

    monkeypatch.setattr(runtime_api, "_persist_runtime_execution_to_turn", fake_persist_runtime_execution_to_turn)

    payload = runtime_api.ExecuteRequest(
        code="sample_data = conn.sql('select 1').df()\nprint(sample_data)",
        timeout=30,
        conversation_id="conv-1",
        turn_id="turn-1",
    )
    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-1",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1", username="alice"),
    )

    assert response.success is True
    assert "_inq_fallback_names" in captured["code"]
    assert '"sample_data"' in captured["code"]
    assert isinstance(response.run_id, str)


@pytest.mark.asyncio
async def test_execute_workspace_code_returns_upstream_result(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws2"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_execute_code(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        _ = (code, timeout, working_dir, workspace_id, workspace_duckdb_path)
        return {
            "success": False,
            "stdout": "",
            "stderr": "boom",
            "error": "boom",
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code)

    payload = runtime_api.ExecuteRequest(code='print("x")', timeout=30)
    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-2",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.success is False
    assert response.error == "boom"
    assert isinstance(response.run_id, str)


@pytest.mark.asyncio
async def test_execute_workspace_code_does_not_fabricate_artifacts_without_execution_payload(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws2-exports"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_execute_code(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        _ = (code, timeout, working_dir, workspace_id, workspace_duckdb_path)
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
            "artifacts": [],
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code)

    payload = runtime_api.ExecuteRequest(code='print("x")', timeout=30)
    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-2",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.success is True
    assert isinstance(response.run_id, str)
    assert response.artifacts == []


@pytest.mark.asyncio
async def test_execute_workspace_code_persists_active_turn_artifacts(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws2-active-turn"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_execute_workspace_code_impl(*, workspace_id, workspace_duckdb_path, payload):
        assert workspace_id == "ws-2"
        assert workspace_duckdb_path == str(duckdb_path)
        assert payload.conversation_id == "conv-1"
        assert payload.turn_id == "turn-1"
        return runtime_api.ExecuteResponse(
            success=True,
            run_id="run-1",
            stdout="",
            stderr="",
            error=None,
            result=None,
            result_type=None,
            result_kind="dataframe",
            artifacts=[{"artifact_id": "art-1", "kind": "dataframe"}],
        )

    captured = {}

    async def fake_persist_runtime_execution_to_turn(
        *,
        session,
        username,
        workspace_id,
        workspace_duckdb_path,
        conversation_id,
        turn_id,
        code,
        execution_result,
    ):
        _ = session
        captured["username"] = username
        captured["workspace_id"] = workspace_id
        captured["workspace_duckdb_path"] = workspace_duckdb_path
        captured["conversation_id"] = conversation_id
        captured["turn_id"] = turn_id
        captured["code"] = code
        captured["execution_result"] = execution_result

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "_execute_workspace_code_impl", fake_execute_workspace_code_impl)
    monkeypatch.setattr(runtime_api, "_persist_runtime_execution_to_turn", fake_persist_runtime_execution_to_turn)

    payload = runtime_api.ExecuteRequest(
        code='print("x")',
        timeout=30,
        conversation_id="conv-1",
        turn_id="turn-1",
    )
    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-2",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1", username="alice"),
    )

    assert response.success is True
    assert captured["username"] == "user-1"
    assert captured["workspace_id"] == "ws-2"
    assert captured["workspace_duckdb_path"] == str(duckdb_path)
    assert captured["conversation_id"] == "conv-1"
    assert captured["turn_id"] == "turn-1"
    assert captured["code"] == 'print("x")'
    assert captured["execution_result"].artifacts[0]["artifact_id"] == "art-1"


@pytest.mark.asyncio
async def test_workspace_dataframe_artifact_rows_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_get_rows(session, *, workspace_id, artifact_id, offset, limit, sort_model=None, filter_model=None, search_text=None):
        _ = session
        assert workspace_id == "ws-5"
        assert artifact_id == "art-1"
        assert offset == 0
        assert limit == 1000
        assert sort_model == []
        assert filter_model == {}
        assert search_text is None
        return {
            "artifact_id": "art-1",
            "name": "summary",
            "row_count": 2000,
            "columns": ["a"],
            "rows": [{"a": 1}],
            "offset": 0,
            "limit": 1000,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_dataframe_rows", fake_get_rows)

    response = await runtime_api.get_workspace_dataframe_artifact_rows(
        workspace_id="ws-5",
        artifact_id="art-1",
        offset=0,
        limit=1000,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.artifact_id == "art-1"
    assert response.row_count == 2000
    assert response.rows == [{"a": 1}]


@pytest.mark.asyncio
async def test_workspace_dataframe_artifact_rows_endpoint_forwards_sort_filter_and_search(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5-lock"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    captured = {}
    async def fake_get_rows(session, *, workspace_id, artifact_id, offset, limit, sort_model=None, filter_model=None, search_text=None):
        _ = session
        captured["workspace_id"] = workspace_id
        captured["artifact_id"] = artifact_id
        captured["offset"] = offset
        captured["limit"] = limit
        captured["sort_model"] = sort_model
        captured["filter_model"] = filter_model
        captured["search_text"] = search_text
        return {
            "artifact_id": artifact_id,
            "name": "summary",
            "row_count": 1,
            "columns": ["city"],
            "rows": [{"city": "New York"}],
            "offset": offset,
            "limit": limit,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_dataframe_rows", fake_get_rows)

    response = await runtime_api.get_workspace_dataframe_artifact_rows(
        workspace_id="ws-5",
        artifact_id="art-1",
        offset=0,
        limit=100,
        sort_model='[{"colId":"amount","sort":"desc"}]',
        filter_model='{"city":{"filterType":"text","type":"contains","filter":"new"}}',
        search="new",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.artifact_id == "art-1"
    assert captured["workspace_id"] == "ws-5"
    assert captured["artifact_id"] == "art-1"
    assert captured["offset"] == 0
    assert captured["limit"] == 100
    assert captured["sort_model"] == [{"colId": "amount", "sort": "desc"}]
    assert captured["filter_model"] == {"city": {"filterType": "text", "type": "contains", "filter": "new"}}
    assert captured["search_text"] == "new"


@pytest.mark.asyncio
async def test_workspace_artifact_metadata_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5-grid-models"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_get_meta(session, *, workspace_id, artifact_id):
        _ = session
        assert workspace_id == "ws-5"
        assert artifact_id == "fig-1"
        return {
            "artifact_id": "fig-1",
            "run_id": "run-1",
            "workspace_id": "ws-5",
            "logical_name": "chart_one",
            "kind": "figure",
            "pointer": str(workspace_dir / "artifacts" / "fig-1.json"),
            "table_name": None,
            "schema": None,
            "row_count": None,
            "payload": {"figure": {"data": [], "layout": {}}},
            "created_at": "2026-03-03T00:00:00+00:00",
            "expires_at": "2026-03-04T00:00:00+00:00",
            "status": "ready",
            "error": None,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_workspace_artifact", fake_get_meta)

    response = await runtime_api.get_workspace_artifact_metadata(
        workspace_id="ws-5",
        artifact_id="fig-1",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.artifact_id == "fig-1"
    assert response.kind == "figure"
    assert response.logical_name == "chart_one"
    assert response.payload == {"figure": {"data": [], "layout": {}}}


@pytest.mark.asyncio
async def test_workspace_artifact_delete_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5-meta"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_delete_turn_artifact(session, *, workspace_id, artifact_id):
        _ = session
        assert workspace_id == "ws-5"
        assert artifact_id == "fig-1"
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "delete_workspace_artifact", fake_delete_turn_artifact)

    response = await runtime_api.delete_workspace_artifact(
        workspace_id="ws-5",
        artifact_id="fig-1",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.artifact_id == "fig-1"
    assert response.deleted is True


@pytest.mark.asyncio
async def test_workspace_artifact_metadata_endpoint_returns_404_when_missing(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5-meta-lock"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    async def fake_get_turn_meta(session, *, workspace_id, artifact_id):
        _ = (session, workspace_id, artifact_id)
        return None

    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_workspace_artifact", fake_get_turn_meta)

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.get_workspace_artifact_metadata(
            workspace_id="ws-5",
            artifact_id="fig-1",
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 404
    assert "Artifact not found" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_workspace_artifact_delete_endpoint_returns_404_when_missing(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5-del"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    async def fake_delete_turn_artifact(session, *, workspace_id, artifact_id):
        _ = (session, workspace_id, artifact_id)
        return False

    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "delete_workspace_artifact", fake_delete_turn_artifact)

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.delete_workspace_artifact(
            workspace_id="ws-5",
            artifact_id="fig-1",
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 404
    assert "Artifact not found" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_workspace_artifact_usage_endpoint_returns_threshold_warnings(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5-del-lock"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_usage(session, *, workspace_id: str, workspace_duckdb_path: str):
        _ = session
        assert workspace_id == "ws-usage"
        assert workspace_duckdb_path == str(duckdb_path)
        return {
            "duckdb_bytes": (2 * 1024 * 1024 * 1024),
            "figure_count": 24,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_workspace_artifact_usage", fake_usage)

    response = await runtime_api.get_workspace_artifact_usage(
        workspace_id="ws-usage",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-usage"
    assert response.duckdb_bytes == (2 * 1024 * 1024 * 1024)
    assert response.figure_count == 24
    assert response.duckdb_warning_threshold_bytes == 1024 * 1024 * 1024
    assert response.figure_warning_threshold_count == 20
    assert response.duckdb_warning is True
    assert response.figure_warning is True
    assert response.warning is True


@pytest.mark.asyncio
async def test_workspace_artifact_usage_endpoint_wraps_storage_errors(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-usage-lock"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_usage(session, *, workspace_id: str, workspace_duckdb_path: str):
        _ = (session, workspace_duckdb_path)
        assert workspace_id == "ws-usage-lock"
        raise RuntimeError("Storage scan failed")

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_workspace_artifact_usage", fake_usage)

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.get_workspace_artifact_usage(
            workspace_id="ws-usage-lock",
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 409
    assert "Storage scan failed" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_workspace_artifact_usage_endpoint_uses_workspace_storage_path(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-usage-direct-guard"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_usage(session, *, workspace_id: str, workspace_duckdb_path: str):
        _ = session
        assert workspace_id == "ws-usage-direct-guard"
        assert workspace_duckdb_path == str(duckdb_path)
        return {
            "duckdb_bytes": 512 * 1024 * 1024,
            "figure_count": 7,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "get_workspace_artifact_usage", fake_usage)

    response = await runtime_api.get_workspace_artifact_usage(
        workspace_id="ws-usage-direct-guard",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-usage-direct-guard"
    assert response.duckdb_bytes == 512 * 1024 * 1024
    assert response.figure_count == 7
    assert response.duckdb_warning is False
    assert response.figure_warning is False
    assert response.warning is False


@pytest.mark.asyncio
async def test_workspace_artifact_list_endpoint_returns_only_turn_artifact_metadata(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-list"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_list_turn_artifacts(session, *, workspace_id, kind=None):
        _ = (session, workspace_id, kind)
        return [
            {
                "artifact_id": "artifact-1",
                "logical_name": "summary_df",
                "kind": "dataframe",
                "row_count": 2,
                "schema": [{"name": "amount", "dtype": "INTEGER"}],
                "created_at": "2026-05-17T00:00:00+00:00",
                "status": "active",
            }
        ]

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.TurnArtifactReadService, "list_workspace_artifacts", fake_list_turn_artifacts)

    response = await runtime_api.list_workspace_artifacts(
        workspace_id="ws-list",
        kind=None,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.total == 1
    assert {item.artifact_id for item in response.artifacts} == {"artifact-1"}


@pytest.mark.asyncio
async def test_workspace_runtime_status_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws3"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_status(workspace_id: str):
        assert workspace_id == "ws-3"
        return "ready"

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    async def fake_snapshots():
        return [
            {
                "workspace_id": "ws-3",
                "status": "ready",
                "last_used_at": "2026-06-21T00:00:00+00:00",
                "idle_seconds": 12,
            }
        ]

    monkeypatch.setattr(runtime_api, "get_workspace_runtime_status", fake_status)
    monkeypatch.setattr(runtime_api, "list_workspace_runtime_snapshots", fake_snapshots)

    response = await runtime_api.get_workspace_runtime_status_endpoint(
        workspace_id="ws-3",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-3"
    assert response.status == "ready"
    assert response.idle_seconds == 12


@pytest.mark.asyncio
async def test_workspace_runtime_reset_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws4"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_reset(workspace_id: str):
        assert workspace_id == "ws-4"
        return True

    async def fake_bootstrap_workspace_runtime(*, workspace_id, workspace_duckdb_path, progress_callback=None):
        assert workspace_id == "ws-4"
        assert workspace_duckdb_path == str(duckdb_path)
        assert progress_callback is None
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)
    monkeypatch.setattr(runtime_api, "bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    response = await runtime_api.reset_workspace_runtime(
        workspace_id="ws-4",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-4"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_kernel_interrupt_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws6"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_interrupt(workspace_id: str):
        assert workspace_id == "ws-6"
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "interrupt_workspace_kernel", fake_interrupt)

    response = await runtime_api.interrupt_workspace_runtime(
        workspace_id="ws-6",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-6"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_terminal_execute_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws7"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    captured = {}

    async def fake_run_terminal_command(*, user_id, workspace_id, command, workspace_dir, cwd, timeout):
        captured["user_id"] = user_id
        captured["workspace_id"] = workspace_id
        captured["command"] = command
        captured["workspace_dir"] = workspace_dir
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return {
            "stdout": "ok\n",
            "stderr": "",
            "exit_code": 0,
            "cwd": workspace_dir,
            "shell": "/bin/bash",
            "platform": "Darwin",
            "timed_out": False,
            "persistent": True,
        }

    async def fake_enforce_terminal_risk_acknowledged(session, user_id):
        _ = (session, user_id)
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "run_workspace_terminal_command", fake_run_terminal_command)
    monkeypatch.setattr(
        runtime_api,
        "_enforce_terminal_risk_acknowledged",
        fake_enforce_terminal_risk_acknowledged,
    )

    response = await runtime_api.execute_workspace_terminal_command(
        workspace_id="ws-7",
        payload=runtime_api.TerminalExecuteRequest(command="pwd", cwd=None, timeout=90),
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.exit_code == 0
    assert response.stdout == "ok\n"
    assert captured["user_id"] == "user-1"
    assert captured["workspace_id"] == "ws-7"
    assert captured["command"] == "pwd"
    assert captured["workspace_dir"] == str(workspace_dir)
    assert captured["cwd"] is None
    assert captured["timeout"] == 90


@pytest.mark.asyncio
async def test_workspace_terminal_session_reset_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws9"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_stop_terminal(*, user_id, workspace_id):
        assert user_id == "user-1"
        assert workspace_id == "ws-9"
        return True

    async def fake_enforce_terminal_risk_acknowledged(session, user_id):
        _ = (session, user_id)
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "stop_workspace_terminal_session", fake_stop_terminal)
    monkeypatch.setattr(
        runtime_api,
        "_enforce_terminal_risk_acknowledged",
        fake_enforce_terminal_risk_acknowledged,
    )

    response = await runtime_api.reset_workspace_terminal_session(
        workspace_id="ws-9",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-9"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_terminal_execute_enforces_allowlist_policy(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws10"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    def fake_load_runtime_config():
        return SimpleNamespace(
            terminal_enabled=True,
            terminal_command_allowlist=["pwd"],
            terminal_command_denylist=[],
        )

    async def fake_enforce_terminal_risk_acknowledged(session, user_id):
        _ = (session, user_id)
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "load_execution_runtime_config", fake_load_runtime_config)
    monkeypatch.setattr(
        runtime_api,
        "_enforce_terminal_risk_acknowledged",
        fake_enforce_terminal_risk_acknowledged,
    )

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.execute_workspace_terminal_command(
            workspace_id="ws-10",
            payload=runtime_api.TerminalExecuteRequest(command="ls -la", cwd=None, timeout=30),
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_workspace_terminal_execute_requires_risk_acknowledgment(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws10b"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    def fake_load_runtime_config():
        return SimpleNamespace(
            terminal_enabled=True,
            terminal_command_allowlist=[],
            terminal_command_denylist=[],
        )

    async def fake_get_prefs(session, principal_id):
        _ = (session, principal_id)
        return SimpleNamespace(terminal_risk_acknowledged=False)

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "load_execution_runtime_config", fake_load_runtime_config)
    monkeypatch.setattr(
        runtime_api.PreferencesRepository,
        "get_or_create",
        fake_get_prefs,
    )

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.execute_workspace_terminal_command(
            workspace_id="ws-10b",
            payload=runtime_api.TerminalExecuteRequest(command="pwd", cwd=None, timeout=30),
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 403
    assert "risk acknowledgment" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_workspace_kernel_restart_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws7"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_reset(workspace_id: str):
        assert workspace_id == "ws-7"
        return True

    async def fake_bootstrap_workspace_runtime(*, workspace_id, workspace_duckdb_path, progress_callback=None):
        assert workspace_id == "ws-7"
        assert workspace_duckdb_path == str(duckdb_path)
        assert progress_callback is None
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)
    monkeypatch.setattr(runtime_api, "bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    response = await runtime_api.restart_workspace_runtime(
        workspace_id="ws-7",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-7"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_kernel_restart_warms_when_no_existing_session(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws8"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_reset(workspace_id: str):
        assert workspace_id == "ws-8"
        return False

    async def fake_bootstrap_workspace_runtime(*, workspace_id, workspace_duckdb_path, progress_callback=None):
        assert workspace_id == "ws-8"
        assert workspace_duckdb_path == str(duckdb_path)
        assert progress_callback is None
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)
    monkeypatch.setattr(runtime_api, "bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    response = await runtime_api.restart_workspace_runtime(
        workspace_id="ws-8",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-8"
    assert response.reset is True
