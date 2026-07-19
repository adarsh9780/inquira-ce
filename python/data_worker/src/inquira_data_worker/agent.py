"""Schema-aware local analysis agent that reuses workspace Jupyter kernels."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Callable

import duckdb

from .agent_guard import UnsafeCodeError, validate_analysis_code
from .model_client import create_model_client


class AnalysisAgent:
    def __init__(self, *, kernels: Any, model_factory: Callable[[dict[str, Any]], Any] = create_model_client,
                 max_attempts: int = 3) -> None:
        self.kernels = kernels
        self.model_factory = model_factory
        self.max_attempts = max(1, max_attempts)

    async def analyze(self, params: dict[str, Any], emit: Callable[[dict[str, Any]], Any] | None = None) -> dict[str, Any]:
        values = _validate_params(params)
        await _emit(emit, {"type": "agent_status", "stage": "reading_schema"})
        schema = _catalog_schema(values["database_path"])
        model = self.model_factory(values["model"])
        feedback = ""
        execution: dict[str, Any] | None = None
        code = ""
        for attempt in range(1, self.max_attempts + 1):
            await _emit(emit, {"type": "agent_status", "stage": "generating", "attempt": attempt})
            response = await model.complete(_code_messages(values["question"], schema, feedback))
            try:
                code = _json_object(response, "code")["code"]
                if not isinstance(code, str) or not code.strip():
                    raise ValueError("The model did not return analysis code.")
                validate_analysis_code(code)
            except (ValueError, UnsafeCodeError) as exc:
                feedback = str(exc)
                await _emit(emit, {"type": "agent_status", "stage": "retrying", "attempt": attempt, "reason": feedback})
                continue
            await _emit(emit, {"type": "agent_status", "stage": "executing", "attempt": attempt})
            execution = await self.kernels.execute(
                workspace_id=values["workspace_id"], database_path=values["database_path"], code=code,
                run_id=values["run_id"], artifact_dir=values["artifact_dir"],
                timeout_seconds=values["timeout_seconds"], emit=emit,
            )
            if execution.get("success"):
                break
            feedback = str(execution.get("error") or execution.get("stderr") or "The code failed without an error message.")
            await _emit(emit, {"type": "agent_status", "stage": "retrying", "attempt": attempt, "reason": feedback})
        if not execution or not execution.get("success"):
            return {"success": False, "answer": "", "code": code, "execution": execution,
                    "error": feedback or "The agent could not produce safe, working analysis code."}
        await _emit(emit, {"type": "agent_status", "stage": "explaining"})
        response = await model.complete(_answer_messages(values["question"], code, execution))
        answer = _json_object(response, "answer")["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("The model did not return an answer.")
        await _emit(emit, {"type": "agent_status", "stage": "completed"})
        return {"success": True, "answer": answer.strip(), "code": code, "execution": execution, "error": None}


def _catalog_schema(database_path: str) -> str:
    connection = duckdb.connect(database_path, read_only=True)
    try:
        rows = connection.execute("""
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name, ordinal_position
        """).fetchall()
    finally:
        connection.close()
    if not rows:
        return "No tables are currently available."
    tables: dict[tuple[str, str], list[str]] = {}
    for table_schema, table_name, column_name, data_type in rows:
        tables.setdefault((table_schema, table_name), []).append(f'"{column_name}" {data_type}')
    return "\n".join(f'{schema}."{table}": ' + ", ".join(columns) for (schema, table), columns in tables.items())


def _code_messages(question: str, schema: str, feedback: str) -> list[dict[str, str]]:
    system = (
        "You are a careful data analyst. Return one JSON object with a single string field named code. "
        "Write Python that analyzes the user's question using the existing read-only DuckDB connection `conn`. "
        "Do not open files, network connections, subprocesses, or another database connection. pandas and plotly are available. "
        "Assign the final useful value, dataframe, or plotly figure to `result`. Quote SQL identifiers when needed."
    )
    content = f"Question:\n{question}\n\nDuckDB schema:\n{schema}"
    if feedback:
        content += f"\n\nThe previous attempt failed. Correct this error:\n{feedback}"
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def _answer_messages(question: str, code: str, execution: dict[str, Any]) -> list[dict[str, str]]:
    evidence = {
        "result": execution.get("result"), "result_kind": execution.get("result_kind"),
        "stdout": execution.get("stdout"), "stderr": execution.get("stderr"),
    }
    return [
        {"role": "system", "content": "Explain analysis results accurately and concisely. Return one JSON object with a string field named answer. Do not claim anything absent from the evidence."},
        {"role": "user", "content": f"Question:\n{question}\n\nExecuted code:\n{code}\n\nEvidence:\n{json.dumps(evidence, default=str)}"},
    ]


def _json_object(raw: str, required_key: str) -> dict[str, Any]:
    value = raw.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1]).strip()
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The model did not return valid JSON.") from exc
        decoded = json.loads(value[start:end + 1])
    if not isinstance(decoded, dict) or required_key not in decoded:
        raise ValueError(f"The model response must contain {required_key}.")
    return decoded


def _validate_params(params: dict[str, Any]) -> dict[str, Any]:
    required_strings = ("workspace_id", "database_path", "question", "run_id", "artifact_dir")
    for key in required_strings:
        if not isinstance(params.get(key), str) or not params[key].strip():
            raise ValueError(f"{key} is required.")
    database = Path(params["database_path"]).expanduser().resolve()
    if not database.is_file():
        raise ValueError("database_path must identify an existing workspace catalog.")
    timeout = params.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
        raise ValueError("timeout_seconds must be between 1 and 3600.")
    if not isinstance(params.get("model"), dict):
        raise ValueError("model configuration is required.")
    return {**params, "database_path": str(database), "artifact_dir": str(Path(params["artifact_dir"]).resolve())}


async def _emit(callback: Callable[[dict[str, Any]], Any] | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    value = callback(event)
    if inspect.isawaitable(value):
        await value
