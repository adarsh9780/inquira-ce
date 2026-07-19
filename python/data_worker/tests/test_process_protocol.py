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
        messages = payload["messages"]
        is_answer = "Executed code:" in messages[-1]["content"]
        content = (
            json.dumps({"answer": "Total sales are 30."})
            if is_answer
            else json.dumps({"code": "result = conn.execute('SELECT SUM(amount) AS total FROM sales').df()"})
        )
        encoded = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
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
        assert [request["messages"][-1]["content"] for request in ModelHandler.requests][0].find("sales") >= 0
        assert any(event["type"] == "agent_status" and event["data"]["stage"] == "executing" for event in events)
    finally:
        process.stdin.close()
        process.wait(timeout=20)
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
        if process.poll() is None:
            process.kill()
    assert process.returncode == 0
