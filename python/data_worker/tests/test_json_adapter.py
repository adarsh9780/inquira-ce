from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.adapters.registry import get_adapter
from inquira_data_worker.errors import AdapterError
from inquira_data_worker.models import AdapterRequest, MaterializeRequest


@pytest.mark.parametrize("suffix", [".json", ".JSON", ".jsonl", ".JSONL", ".ndjson", ".NDJSON"])
def test_json_adapter_discovers_json_arrays_and_lines(suffix: str, tmp_path: Path) -> None:
    path = tmp_path / f"events{suffix}"
    rows = [
        {"id": 1, "customer": "José", "tags": ["new", "priority"], "profile": {"city": "東京"}},
        {"id": 2, "customer": None, "tags": [], "profile": {"city": "Pune"}},
    ]
    if suffix.lower() == ".json":
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    else:
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )

    adapter = get_adapter("json")
    discovery = adapter.discover(AdapterRequest(source_path=str(path)))
    assert discovery.adapter_kind == "json"
    assert discovery.objects[0].id == "file"
    assert [column.name for column in discovery.objects[0].columns] == [
        "id",
        "customer",
        "tags",
        "profile",
    ]

    preview = adapter.preview(AdapterRequest(source_path=str(path)), limit=1)
    assert preview.rows[0]["customer"] == "José"
    assert preview.rows[0]["tags"] == ["new", "priority"]
    assert preview.rows[0]["profile"]["city"] == "東京"
    assert preview.truncated is True


def test_json_adapter_materializes_to_canonical_parquet(tmp_path: Path) -> None:
    source = tmp_path / "records.ndjson"
    source.write_text('{"id": 1, "active": true}\n{"id": 2, "active": false}\n', encoding="utf-8")
    target = tmp_path / "snapshot"

    result = get_adapter("json").materialize(MaterializeRequest(
        source_path=str(source),
        target_dir=str(target),
        selected_object_ids=["file"],
    ))

    assert result.outputs[0].row_count == 2
    assert result.outputs[0].relative_path == "data.parquet"
    assert duckdb.sql(
        f"SELECT id, active FROM read_parquet('{target / 'data.parquet'}') ORDER BY id"
    ).fetchall() == [(1, True), (2, False)]


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("empty.json", "", "empty"),
        ("broken.json", "{not-json", "read"),
        ("wrong.txt", "[]", "extension"),
    ],
)
def test_json_adapter_rejects_invalid_sources(
    name: str,
    content: str,
    message: str,
    tmp_path: Path,
) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    with pytest.raises(AdapterError, match=message):
        get_adapter("json").discover(AdapterRequest(source_path=str(path)))
