from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_execute_workspace_code_blocks_package_install_commands(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

    with pytest.raises(HTTPException) as exc:
        await runtime_api.execute_workspace_code(
            workspace_id="ws-1",
            payload=runtime_api.ExecuteRequest(code="!pip install seaborn", timeout=30),
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 400
    assert "settings > runner packages" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_install_runner_package_requires_exact_version(monkeypatch):
    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path="/tmp/ws.duckdb")

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(
        runtime_api,
        "load_execution_runtime_config",
        lambda: SimpleNamespace(
            runner_package_allowlist=[],
            runner_package_denylist=[],
            runner_install_max_packages_per_request=1,
            runner_index_url=None,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await runtime_api.install_runner_runtime_package(
            payload=runtime_api.RunnerPackageInstallRequest(
                workspace_id="ws-1",
                package="pandas",
                version=">=2.0.0",
                index_url=None,
                save_as_default=False,
            ),
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 400
    assert "exact" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_install_runner_package_success_resets_kernel(monkeypatch):
    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path="/tmp/ws.duckdb")

    async def fake_reset_workspace_kernel(workspace_id):
        assert workspace_id == "ws-1"
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset_workspace_kernel)
    monkeypatch.setattr(
        runtime_api,
        "load_execution_runtime_config",
        lambda: SimpleNamespace(
            runner_package_allowlist=[],
            runner_package_denylist=[],
            runner_install_max_packages_per_request=1,
            runner_index_url=None,
            runner_python_executable="/tmp/runner/bin/python",
            runner_packages=[],
        ),
    )

    def fake_install_runner_package(config, package_spec, index_url, workspace_duckdb_path):
        _ = config
        assert package_spec == "seaborn==0.13.2"
        assert index_url is None
        assert workspace_duckdb_path == "/tmp/ws.duckdb"
        return SimpleNamespace(
            installer="uv",
            command=["uv", "pip", "install", package_spec],
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(runtime_api, "install_runner_package", fake_install_runner_package)

    response = await runtime_api.install_runner_runtime_package(
        payload=runtime_api.RunnerPackageInstallRequest(
            workspace_id="ws-1",
            package="seaborn",
            version="0.13.2",
            index_url=None,
            save_as_default=False,
        ),
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.installed is True
    assert response.package_spec == "seaborn==0.13.2"
    assert response.workspace_kernel_reset is True
    assert response.saved_as_default is False
