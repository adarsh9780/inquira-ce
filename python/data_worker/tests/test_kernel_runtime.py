from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import duckdb

from inquira_data_worker.kernel import WorkspaceKernelManager


def create_catalog(path: Path) -> None:
    connection = duckdb.connect(str(path))
    connection.execute("CREATE TABLE sales AS SELECT * FROM (VALUES (1, 10), (2, 20)) AS rows(id, amount)")
    connection.close()


def test_workspace_kernel_reuses_state_and_reads_catalog(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            first = await manager.execute(
                workspace_id="workspace-1",
                database_path=str(catalog),
                code="answer = conn.execute('SELECT SUM(amount) FROM sales').fetchone()[0]",
                run_id="run-1",
                artifact_dir=str(tmp_path / "run-1"),
                timeout_seconds=10,
            )
            second = await manager.execute(
                workspace_id="workspace-1",
                database_path=str(catalog),
                code="answer + 12",
                run_id="run-2",
                artifact_dir=str(tmp_path / "run-2"),
                timeout_seconds=10,
            )
            assert first["success"] is True
            assert second["result"] == 42
            assert second["result_kind"] == "scalar"
            assert await manager.status("workspace-1") == "ready"
            assert manager.session_count == 1
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_workspace_kernels_are_isolated_and_resettable(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            await manager.execute(
                workspace_id="workspace-1", database_path=str(catalog), code="secret_value = 9",
                run_id="run-1", artifact_dir=str(tmp_path / "one"), timeout_seconds=10,
            )
            isolated = await manager.execute(
                workspace_id="workspace-2", database_path=str(catalog), code="secret_value",
                run_id="run-2", artifact_dir=str(tmp_path / "two"), timeout_seconds=10,
            )
            assert isolated["success"] is False
            assert "NameError" in isolated["error"]
            assert await manager.reset("workspace-1") is True
            assert await manager.status("workspace-1") == "missing"
            assert await manager.reset("workspace-1") is False
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_kernel_captures_streams_dataframe_results_and_full_artifacts(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        artifact_dir = tmp_path / "artifacts"
        events: list[dict] = []
        manager = WorkspaceKernelManager()
        try:
            result = await manager.execute(
                workspace_id="workspace-1",
                database_path=str(catalog),
                code=(
                    "print('working')\n"
                    "import pandas as pd\n"
                    "regional_sales = pd.DataFrame([{'region': 'West', 'sales': 25}, {'region': 'East', 'sales': 18}])\n"
                    "regional_sales"
                ),
                run_id="run-dataframe",
                artifact_dir=str(artifact_dir),
                timeout_seconds=10,
                emit=events.append,
            )
            assert result["success"] is True
            assert result["stdout"].strip() == "working"
            assert result["result_kind"] == "dataframe"
            assert result["result_name"] == "regional_sales"
            assert result["has_stdout"] is True
            assert result["has_stderr"] is False
            assert result["variables"] == {"dataframes": {}, "figures": {}, "scalars": {}}
            assert result["result"]["rows"][0] == {"region": "West", "sales": 25}
            assert len(result["artifacts"]) == 1
            artifact = result["artifacts"][0]
            assert artifact["kind"] == "dataframe"
            assert artifact["logical_name"] == "regional_sales"
            artifact_path = Path(artifact["source_path"])
            assert artifact_path.parent == artifact_dir
            assert duckdb.read_parquet(str(artifact_path)).count("*").fetchone()[0] == 2
            assert any(event.get("type") == "stream" and event.get("text") == "working\n" for event in events)
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_kernel_displays_and_captures_a_plotly_last_expression(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            result = await manager.execute(
                workspace_id="workspace-plotly",
                database_path=str(catalog),
                code=(
                    "import plotly.graph_objects as go\n"
                    "sales_chart = go.Figure(data=[go.Bar(x=['West'], y=[25])])\n"
                    "sales_chart"
                ),
                run_id="run-plotly",
                artifact_dir=str(tmp_path / "plotly-artifacts"),
                timeout_seconds=10,
            )
            assert result["success"] is True
            assert result["result_kind"] == "figure"
            assert result["result_name"] == "sales_chart"
            assert result["result"]["data"][0]["type"] == "bar"
            assert len(result["artifacts"]) == 1
            assert result["artifacts"][0]["kind"] == "figure"
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_kernel_compiles_agent_chart_spec_and_persists_source_spec(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            result = await manager.execute(
                workspace_id="workspace-chart-spec",
                database_path=str(catalog),
                code=(
                    "sales_summary = conn.sql(\"SELECT id, amount FROM sales ORDER BY amount DESC\").df()\n"
                    "sales_summary"
                ),
                run_id="run-chart-spec",
                artifact_dir=str(tmp_path / "chart-spec-artifacts"),
                timeout_seconds=10,
                output_contract=[{"name": "sales_summary", "kind": "dataframe"}],
                chart_spec={
                    "schema": "inquira.chart/v1",
                    "data": {"logical_name": "sales_summary"},
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "id", "type": "ordinal"},
                        "y": {"field": "amount", "type": "quantitative"},
                    },
                    "title": "Sales by ID",
                },
            )
            assert result["success"] is True, result
            artifacts = {(item["kind"], item["logical_name"]): item for item in result["artifacts"]}
            assert set(artifacts) == {
                ("dataframe", "sales_summary"),
                ("chart_spec", "sales_summary_chart_spec"),
                ("figure", "sales_summary_chart"),
            }
            saved_spec = json.loads(
                Path(artifacts[("chart_spec", "sales_summary_chart_spec")]["source_path"]).read_text()
            )
            saved_figure = json.loads(
                Path(artifacts[("figure", "sales_summary_chart")]["source_path"]).read_text()
            )
            assert saved_spec["schema"] == "inquira.chart/v1"
            assert saved_figure["data"][0]["type"] == "bar"
            assert saved_figure["data"][0]["y"] == [20, 10]
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_kernel_preserves_legacy_set_active_run_argument_order(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            result = await manager.execute(
                workspace_id="workspace-1",
                database_path=str(catalog),
                code=(
                    "set_active_run('manual', 'conversation-1', 'turn-1', "
                    f"{str(tmp_path / 'manual')!r})\n"
                    "str(_inquira_runs['manual']['artifact_dir'])"
                ),
                run_id="outer",
                artifact_dir=str(tmp_path / "outer"),
                timeout_seconds=10,
            )
            assert result["success"] is True
            assert result["result"] == str((tmp_path / "manual").resolve())
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_kernel_timeout_interrupts_execution_and_remains_usable(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            timed_out = await manager.execute(
                workspace_id="workspace-1", database_path=str(catalog),
                code="import time; time.sleep(5)", run_id="slow",
                artifact_dir=str(tmp_path / "slow"), timeout_seconds=1,
            )
            assert timed_out["success"] is False
            assert timed_out["timed_out"] is True
            recovered = await manager.execute(
                workspace_id="workspace-1", database_path=str(catalog), code="6 * 7",
                run_id="recovered", artifact_dir=str(tmp_path / "recovered"), timeout_seconds=10,
            )
            assert recovered["success"] is True
            assert recovered["result"] == 42
        finally:
            await manager.shutdown()

    asyncio.run(scenario())


def test_workspace_kernel_reconnects_when_catalog_is_atomically_replaced(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        create_catalog(catalog)
        manager = WorkspaceKernelManager()
        try:
            before = await manager.execute(
                workspace_id="workspace-1",
                database_path=str(catalog),
                code="conn.execute('SELECT SUM(amount) FROM sales').fetchone()[0]",
                run_id="before",
                artifact_dir=str(tmp_path / "before"),
                timeout_seconds=10,
            )
            assert before["result"] == 30

            replacement = tmp_path / "replacement.duckdb"
            connection = duckdb.connect(str(replacement))
            connection.execute("CREATE TABLE sales AS SELECT * FROM (VALUES (1, 100), (2, 200)) AS rows(id, amount)")
            connection.close()
            os.replace(replacement, catalog)

            after = await manager.execute(
                workspace_id="workspace-1",
                database_path=str(catalog),
                code="conn.execute('SELECT SUM(amount) FROM sales').fetchone()[0]",
                run_id="after",
                artifact_dir=str(tmp_path / "after"),
                timeout_seconds=10,
            )
            assert after["result"] == 300
        finally:
            await manager.shutdown()

    asyncio.run(scenario())
