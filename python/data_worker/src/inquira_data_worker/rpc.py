"""Single-request JSON RPC dispatch for the Go control plane."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .adapters.registry import get_adapter
from .errors import AdapterError
from .models import AdapterRequest, MaterializeRequest


def _result(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id") if isinstance(request, dict) else None
    response = {"id": request_id, "result": None, "error": None}
    try:
        if not isinstance(request, dict) or not request_id or not isinstance(request.get("method"), str):
            raise AdapterError("invalid_request", "RPC request requires an id and method.")
        params = request.get("params")
        if not isinstance(params, dict):
            raise AdapterError("invalid_params", "RPC params must be an object.")
        method = request["method"]
        if method not in {"discover", "preview", "materialize"}:
            raise AdapterError("method_not_found", f"RPC method {method} was not found.")
        adapter_kind = params.get("adapter_kind")
        source_path = params.get("source_path")
        if not isinstance(adapter_kind, str) or not isinstance(source_path, str) or not source_path.strip():
            raise AdapterError("invalid_params", "adapter_kind and source_path are required.")
        adapter = get_adapter(adapter_kind)
        if method == "discover":
            value = adapter.discover(AdapterRequest(source_path=source_path, options=params.get("options") or {}))
        elif method == "preview":
            limit = params.get("limit", 100)
            if not isinstance(limit, int):
                raise AdapterError("invalid_params", "Preview limit must be an integer.")
            value = adapter.preview(AdapterRequest(source_path=source_path, options=params.get("options") or {}), limit)
        else:
            selected = params.get("selected_object_ids")
            target_dir = params.get("target_dir")
            if not isinstance(selected, list) or not isinstance(target_dir, str) or not target_dir.strip():
                raise AdapterError("invalid_params", "target_dir and selected_object_ids are required.")
            value = adapter.materialize(MaterializeRequest(
                source_path=source_path,
                target_dir=target_dir,
                selected_object_ids=[str(item) for item in selected],
                options=params.get("options") or {},
            ))
        response["result"] = _result(value)
    except AdapterError as exc:
        response["error"] = {"code": exc.code, "message": exc.message}
    except Exception:
        response["error"] = {"code": "worker_internal_error", "message": "The data worker could not complete the request."}
    return response
