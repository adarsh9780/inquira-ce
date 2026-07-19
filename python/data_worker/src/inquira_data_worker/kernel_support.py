"""Helpers installed into each workspace kernel namespace."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


def install(namespace: dict[str, Any], *, workspace_id: str, database_path: str) -> None:
    import duckdb
    from IPython.display import display

    existing = namespace.get("conn")
    if existing is not None:
        try:
            existing.close()
        except Exception:
            pass
    namespace["conn"] = duckdb.connect(database_path, read_only=True)
    namespace["_inquira_workspace_id"] = workspace_id
    namespace["_inquira_runs"] = {}
    namespace["_inquira_active_run"] = None

    def set_active_run(
        run_id: str,
        conversation_id: str | None = None,
        turn_id: str | None = None,
        artifact_dir: str | None = None,
    ) -> str:
        _ = conversation_id, turn_id
        target = Path(artifact_dir or ".").expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        namespace["_inquira_active_run"] = str(run_id)
        namespace["_inquira_runs"][str(run_id)] = {"artifact_dir": target, "exports": []}
        return str(run_id)

    def active_run(run_id: str | None = None) -> dict[str, Any]:
        key = str(run_id or namespace.get("_inquira_active_run") or "")
        run = namespace["_inquira_runs"].get(key)
        if run is None:
            raise RuntimeError("No active analysis run is configured.")
        return run

    def target_path(kind: str, payload_format: str, run_id: str | None = None) -> Path:
        run = active_run(run_id)
        return run["artifact_dir"] / f"{uuid.uuid4()}.{payload_format}"

    def record(descriptor: dict[str, Any], run_id: str | None = None) -> dict[str, Any]:
        active_run(run_id)["exports"].append(descriptor)
        return descriptor

    def dataframe_value(value: Any) -> Any:
        try:
            import pandas as pd
        except Exception:
            pd = None
        if pd is not None and isinstance(value, pd.DataFrame):
            return value
        if isinstance(value, duckdb.DuckDBPyRelation):
            return value.df()
        return None

    def export_dataframe(value: Any, logical_name: str = "dataframe", run_id: str | None = None, display_name: str | None = None) -> dict[str, Any]:
        frame = dataframe_value(value)
        if frame is None:
            raise TypeError("export_dataframe requires a pandas DataFrame or DuckDB relation.")
        path = target_path("dataframe", "parquet", run_id)
        export_connection = duckdb.connect(":memory:")
        try:
            export_connection.register("_inquira_frame", frame)
            export_connection.execute("COPY _inquira_frame TO ? (FORMAT PARQUET)", [str(path)])
        finally:
            export_connection.close()
        descriptor = {
            "kind": "dataframe",
            "logical_name": str(logical_name),
            "display_name": str(display_name or logical_name),
            "payload_format": "parquet",
            "media_type": "application/vnd.apache.parquet",
            "source_path": str(path),
        }
        return record(descriptor, run_id)

    def export_figure(value: Any, logical_name: str = "figure", run_id: str | None = None, display_name: str | None = None) -> dict[str, Any]:
        if hasattr(value, "to_plotly_json"):
            payload = value.to_plotly_json()
        elif isinstance(value, dict) and "data" in value:
            payload = value
        else:
            raise TypeError("export_figure requires a Plotly figure or compatible dictionary.")
        path = target_path("figure", "json", run_id)
        path.write_text(json.dumps(payload, default=str), encoding="utf-8")
        descriptor = {
            "kind": "figure",
            "logical_name": str(logical_name),
            "display_name": str(display_name or logical_name),
            "payload_format": "json",
            "media_type": "application/vnd.plotly.v1+json",
            "source_path": str(path),
        }
        return record(descriptor, run_id)

    def export_scalar(value: Any, logical_name: str = "scalar", run_id: str | None = None, display_name: str | None = None, meta: Any = None) -> dict[str, Any]:
        path = target_path("scalar", "json", run_id)
        path.write_text(json.dumps({"value": _json_safe(value), "meta": _json_safe(meta)}, default=str), encoding="utf-8")
        descriptor = {
            "kind": "scalar",
            "logical_name": str(logical_name),
            "display_name": str(display_name or logical_name),
            "payload_format": "json",
            "media_type": "application/json",
            "source_path": str(path),
        }
        return record(descriptor, run_id)

    def emit_capture(value: Any, logical_name: str = "result") -> None:
        frame = dataframe_value(value)
        if frame is not None:
            export_dataframe(frame, logical_name=logical_name)
            preview = frame.head(1000)
            payload = {
                "columns": [str(column) for column in preview.columns],
                "rows": json.loads(preview.to_json(orient="records", date_format="iso")),
            }
            display({"application/json": {"kind": "dataframe", "value": payload}}, raw=True)
            return
        if hasattr(value, "to_plotly_json") or (isinstance(value, dict) and "data" in value and "layout" in value):
            export_figure(value, logical_name=logical_name)
            figure = value.to_plotly_json() if hasattr(value, "to_plotly_json") else value
            display({"application/json": {"kind": "figure", "value": _json_safe(figure)}}, raw=True)
            return
        display({"application/json": {"kind": "scalar", "value": _json_safe(value)}}, raw=True)

    def emit_preview(value: Any, logical_name: str = "result") -> None:
        _ = logical_name
        frame = dataframe_value(value)
        if frame is not None:
            preview = frame.head(1000)
            payload = {
                "columns": [str(column) for column in preview.columns],
                "rows": json.loads(preview.to_json(orient="records", date_format="iso")),
            }
            display({"application/json": {"kind": "dataframe", "value": payload}}, raw=True)
            return
        if hasattr(value, "to_plotly_json") or (isinstance(value, dict) and "data" in value and "layout" in value):
            figure = value.to_plotly_json() if hasattr(value, "to_plotly_json") else value
            display({"application/json": {"kind": "figure", "value": _json_safe(figure)}}, raw=True)
            return
        display({"application/json": {"kind": "scalar", "value": _json_safe(value)}}, raw=True)

    def emit_exports(run_id: str) -> None:
        exports = list(active_run(run_id)["exports"])
        display({"application/json": {"kind": "exports", "value": exports}}, raw=True)

    namespace["set_active_run"] = set_active_run
    namespace["export_dataframe"] = export_dataframe
    namespace["export_figure"] = export_figure
    namespace["export_scalar"] = export_scalar
    namespace["_inquira_emit_capture"] = emit_capture
    namespace["_inquira_emit_preview"] = emit_preview
    namespace["_inquira_emit_exports"] = emit_exports


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)
