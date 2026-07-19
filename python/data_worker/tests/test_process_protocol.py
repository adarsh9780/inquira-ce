from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import duckdb


class ModelHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        self.requests.append(payload)
        response_format = payload.get("response_format") or {}
        schema = response_format.get("json_schema") or {}
        schema_name = str(schema.get("name") or "")
        if schema_name == "ContextEnrichmentPlan":
            value = {
                "enough_context": True,
                "missing_context": [],
                "notes": "The sales table and amount column are available.",
                "progress_message": "I found the fields needed for the calculation.",
                "tools": [],
            }
        elif schema_name == "AnalysisOutput":
            value = {
                "code": "result = conn.sql('SELECT SUM(amount) AS total FROM sales').df()",
                "explanation": "Sum the sales amount.",
                "progress_message": "I prepared the total-sales calculation.",
                "output_contract": [{"name": "result", "kind": "dataframe", "description": "Total sales"}],
                "search_schema_queries": [],
                "selected_tables": ["sales"],
                "join_keys": [],
                "joins_used": False,
            }
        elif schema_name == "ResultExplanation":
            value = {
                "result_explanation": "Total sales are 30.",
                "code_explanation": "The query summed the amount column.",
                "progress_message": "I summarized the calculated total.",
            }
        elif schema_name == "RouteDecision":
            value = {
                "route": "analysis",
                "reasoning": "The question asks for a calculation against sales data.",
                "progress_message": "I will analyze the sales table.",
            }
        else:
            value = {"answer": "Total sales are 30.", "progress_message": "I answered the question."}
        content = json.dumps(value)
        encoded = json.dumps({
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-test",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: object) -> None:
        pass


def test_json_lines_process_keeps_kernel_state_and_shuts_down_cleanly(tmp_path: Path) -> None:
    catalog = tmp_path / "workspace.duckdb"
    connection = duckdb.connect(str(catalog))
    connection.close()
    process = subprocess.Popen(
        [sys.executable, "-m", "inquira_data_worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    assert process.stdout is not None

    def call(request_id: str, code: str, artifact_dir: Path) -> dict:
        process.stdin.write(json.dumps({
            "id": request_id,
            "method": "kernel_execute",
            "params": {
                "workspace_id": "workspace-1",
                "database_path": str(catalog),
                "code": code,
                "run_id": request_id,
                "artifact_dir": str(artifact_dir),
                "timeout_seconds": 10,
            },
        }) + "\n")
        process.stdin.flush()
        while True:
            message = json.loads(process.stdout.readline())
            if message.get("id") == request_id and "event" not in message:
                return message

    try:
        first = call("first", "state = 40", tmp_path / "first")
        second = call("second", "state + 2", tmp_path / "second")
        assert first["error"] is None
        assert second["result"]["result"] == 42
    finally:
        process.stdin.close()
        process.wait(timeout=15)
        if process.poll() is None:
            process.kill()
    assert process.returncode == 0


def test_json_lines_process_runs_agent_from_model_to_duckdb_result(tmp_path: Path) -> None:
    catalog = tmp_path / "workspace.duckdb"
    connection = duckdb.connect(str(catalog))
    connection.execute("CREATE TABLE sales AS SELECT * FROM (VALUES (10), (20)) AS rows(amount)")
    connection.close()
    ModelHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    process = subprocess.Popen(
        [sys.executable, "-m", "inquira_data_worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    request = {
        "id": "agent-1",
        "method": "agent_analyze",
        "params": {
            "workspace_id": "workspace-1", "database_path": str(catalog),
            "question": "What are total sales?", "run_id": "agent-1",
            "artifact_dir": str(tmp_path / "artifacts"), "timeout_seconds": 15,
                "model": {
                "provider": "openai", "model": "gpt-test", "api_key": "test-secret",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                },
                "schema": {
                    "context": "Sales reporting",
                    "tables": [{
                        "name": "sales",
                        "columns": [{"name": "amount", "dtype": "BIGINT", "description": "Sale amount", "aliases": []}],
                    }],
                },
        },
    }
    events: list[dict] = []
    try:
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        while True:
            message = json.loads(process.stdout.readline())
            if message.get("event"):
                events.append(message["event"])
                continue
            if message.get("id") == "agent-1":
                response = message
                break
        assert response["error"] is None
        result = response["result"]
        assert result["success"] is True
        assert result["answer"] == "Total sales are 30."
        assert result["execution"]["result"]["rows"] == [{"total": 30.0}]
        assert "sales" in json.dumps(ModelHandler.requests)
        assert any(
            event["type"] == "agent_status" and event["data"].get("step") == "executing_code"
            for event in events
        )
    finally:
        process.stdin.close()
        process.wait(timeout=20)
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
        if process.poll() is None:
            process.kill()
    assert process.returncode == 0
