from __future__ import annotations

import csv
from pathlib import Path

import pytest

from inquira_data_worker.rpc import handle_request


def write_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows([["id", "name"], [1, "Ada"], [2, "Grace"]])


def test_rpc_discover_preview_and_materialize_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "people.csv"
    write_csv(source)
    discovered = handle_request({"id": "1", "method": "discover", "params": {"adapter_kind": "csv", "source_path": str(source)}})
    assert discovered["id"] == "1"
    assert discovered["error"] is None
    assert discovered["result"]["objects"][0]["id"] == "file"

    previewed = handle_request({"id": "2", "method": "preview", "params": {"adapter_kind": "csv", "source_path": str(source), "limit": 1}})
    assert previewed["result"]["rows"] == [{"id": 1, "name": "Ada"}]
    assert previewed["result"]["truncated"] is True

    target = tmp_path / "snapshot"
    materialized = handle_request({
        "id": "3",
        "method": "materialize",
        "params": {
            "adapter_kind": "csv",
            "source_path": str(source),
            "target_dir": str(target),
            "selected_object_ids": ["file"],
        },
    })
    assert materialized["error"] is None
    assert materialized["result"]["outputs"][0]["row_count"] == 2


@pytest.mark.parametrize(
    "payload,code",
    [
        ({}, "invalid_request"),
        ({"id": "1", "method": "unknown", "params": {}}, "method_not_found"),
        ({"id": "1", "method": "discover", "params": {"adapter_kind": "csv"}}, "invalid_params"),
        ({"id": "1", "method": "discover", "params": {"adapter_kind": "sqlite", "source_path": "/tmp/a.sqlite"}}, "adapter_not_supported"),
    ],
)
def test_rpc_returns_structured_errors(payload: dict, code: str) -> None:
    response = handle_request(payload)
    assert response["result"] is None
    assert response["error"]["code"] == code
    assert response["error"]["message"]


def test_rpc_passes_excel_sheet_selection_to_preview(tmp_path: Path) -> None:
    from openpyxl import Workbook

    path = tmp_path / "book.xlsx"
    workbook = Workbook()
    workbook.active.title = "Sales"
    workbook.active.append(["id"])
    workbook.active.append([1])
    workbook.save(path)
    workbook.close()

    response = handle_request({
        "id": "preview-excel",
        "method": "preview",
        "params": {
            "adapter_kind": "excel",
            "source_path": str(path),
            "source_object_id": "sheet:Sales",
            "limit": 10,
            "options": {},
        },
    })

    assert response["error"] is None
    assert response["result"]["rows"] == [{"id": 1}]
