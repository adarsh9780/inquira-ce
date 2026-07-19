from __future__ import annotations

import asyncio
import json
from pathlib import Path

import duckdb

from inquira_data_worker.agent import AnalysisAgent


class FakeModel:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[list[dict[str, str]]] = []

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.prompts.append(messages)
        return self.responses.pop(0)


class FakeKernels:
    def __init__(self, results: list[dict]) -> None:
        self.results = list(results)
        self.codes: list[str] = []

    async def execute(self, **kwargs) -> dict:
        self.codes.append(kwargs["code"])
        return self.results.pop(0)


def catalog(path: Path) -> None:
    connection = duckdb.connect(str(path))
    connection.execute("CREATE TABLE sales(region VARCHAR, amount INTEGER)")
    connection.close()


def test_agent_generates_executes_and_explains_against_catalog_schema(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = tmp_path / "workspace.duckdb"
        catalog(database)
        model = FakeModel([
            json.dumps({"code": "result = conn.execute('SELECT SUM(amount) AS total FROM sales').df()"}),
            json.dumps({"answer": "Total sales are 42."}),
        ])
        kernels = FakeKernels([{
            "success": True, "stdout": "", "stderr": "", "error": None,
            "result": {"columns": ["total"], "rows": [{"total": 42}]},
            "result_kind": "dataframe", "artifacts": [], "timed_out": False,
        }])
        events: list[dict] = []
        agent = AnalysisAgent(kernels=kernels, model_factory=lambda _: model)
        result = await agent.analyze({
            "workspace_id": "workspace-1", "database_path": str(database),
            "question": "What are total sales?", "run_id": "run-1",
            "artifact_dir": str(tmp_path / "artifacts"), "timeout_seconds": 30,
            "model": {"provider": "openai", "model": "gpt-test", "api_key": "secret"},
        }, events.append)
        assert result["success"] is True
        assert result["answer"] == "Total sales are 42."
        assert result["code"] == kernels.codes[0]
        assert "sales" in model.prompts[0][1]["content"]
        assert "amount" in model.prompts[0][1]["content"]
        assert any(event["type"] == "agent_status" and event["stage"] == "executing" for event in events)

    asyncio.run(scenario())


def test_agent_rejects_unsafe_code_and_retries_execution_errors(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = tmp_path / "workspace.duckdb"
        catalog(database)
        model = FakeModel([
            json.dumps({"code": "open('/tmp/leak', 'w').write('x')"}),
            json.dumps({"code": "result = conn.execute('SELECT missing FROM sales').df()"}),
            json.dumps({"code": "result = conn.execute('SELECT SUM(amount) AS total FROM sales').df()"}),
            json.dumps({"answer": "Recovered and calculated the total."}),
        ])
        kernels = FakeKernels([
            {"success": False, "stdout": "", "stderr": "Binder Error", "error": "Binder Error", "result": None, "result_kind": "error", "artifacts": [], "timed_out": False},
            {"success": True, "stdout": "", "stderr": "", "error": None, "result": 42, "result_kind": "scalar", "artifacts": [], "timed_out": False},
        ])
        agent = AnalysisAgent(kernels=kernels, model_factory=lambda _: model, max_attempts=3)
        result = await agent.analyze({
            "workspace_id": "workspace-1", "database_path": str(database), "question": "Total?",
            "run_id": "run-1", "artifact_dir": str(tmp_path / "artifacts"), "timeout_seconds": 30,
            "model": {"provider": "openai", "model": "gpt-test", "api_key": "secret"},
        }, lambda _: None)
        assert result["success"] is True
        assert len(kernels.codes) == 2
        assert "open(" not in "\n".join(kernels.codes)
        assert "Binder Error" in model.prompts[2][1]["content"]

    asyncio.run(scenario())


def test_agent_uses_structured_conversation_context_as_untrusted_history(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = tmp_path / "workspace.duckdb"
        catalog(database)
        model = FakeModel([
            json.dumps({"code": "result = conn.execute('SELECT SUM(amount) AS total FROM sales').df()"}),
            json.dumps({"answer": "The prior comparison still holds."}),
        ])
        kernels = FakeKernels([{
            "success": True, "stdout": "", "stderr": "", "error": None,
            "result": {"columns": ["total"], "rows": [{"total": 42}]},
            "result_kind": "dataframe", "artifacts": [], "timed_out": False,
        }])
        agent = AnalysisAgent(kernels=kernels, model_factory=lambda _: model)
        await agent.analyze({
            "workspace_id": "workspace-1", "database_path": str(database),
            "question": "Does that still hold?", "run_id": "run-1",
            "artifact_dir": str(tmp_path / "artifacts"), "timeout_seconds": 30,
            "model": {"provider": "openai", "model": "gpt-test", "api_key": "secret"},
            "context": {"turns": [{
                "turn_id": "turn-1", "user_text": "Which region leads?",
                "assistant_text": "West leads.", "code": "result = regional_sales",
                "result_kind": "dataframe", "result": {"columns": ["region", "sales"]},
                "artifacts": [{"kind": "dataframe", "logical_name": "regional_sales", "display_name": "Regional sales", "payload_format": "parquet"}],
            }]},
        }, lambda _: None)
        generation_prompt = model.prompts[0][1]["content"]
        answer_prompt = model.prompts[1][1]["content"]
        assert "Which region leads?" in generation_prompt
        assert "West leads." in generation_prompt
        assert "regional_sales" in generation_prompt
        assert "untrusted" in model.prompts[0][0]["content"].lower()
        assert "Which region leads?" in answer_prompt

    asyncio.run(scenario())
