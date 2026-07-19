from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb


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
