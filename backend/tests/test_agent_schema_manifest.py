import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "agents" / "agent_v2" / "schema_manifest.py"
spec = importlib.util.spec_from_file_location("agent_schema_manifest", MODULE_PATH)
schema_manifest = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(schema_manifest)

build_schema_context_pack = schema_manifest.build_schema_context_pack
build_schema_manifest = schema_manifest.build_schema_manifest
schema_context_budget = schema_manifest.schema_context_budget


def test_schema_context_budget_uses_ten_percent_with_bounds():
    assert schema_context_budget(20_000) == 3_000
    assert schema_context_budget(80_000) == 8_000
    assert schema_context_budget(200_000) == 10_000
    assert schema_context_budget(0) == 10_000


def test_schema_context_pack_loads_full_schema_when_under_budget():
    manifest = build_schema_manifest(
        data_path="/tmp/workspace.duckdb",
        workspace_schema={
            "schema_version": "test-v1",
            "tables": [
                {
                    "table_name": "orders",
                    "context": "Order facts",
                    "columns": [
                        {
                            "name": "gross_revenue",
                            "dtype": "DOUBLE",
                            "description": "Revenue before discounts",
                            "aliases": ["sales"],
                            "samples": [100.5, 220.0],
                        }
                    ],
                }
            ],
        },
    )

    pack = build_schema_context_pack(manifest=manifest, context_window=100_000)

    assert pack["mode"] == "full"
    assert pack["schema_version"] == "test-v1"
    assert pack["schema_folder_path"] == "/tmp/meta"
    column = pack["tables"][0]["columns"][0]
    assert column["description"] == "Revenue before discounts"
    assert column["sample_values"] == [100.5, 220.0]


def test_schema_context_pack_compacts_when_full_schema_exceeds_budget():
    columns = [
        {
            "name": f"column_{idx}",
            "dtype": "VARCHAR",
            "description": "long description " * 40,
            "aliases": [f"alias_{idx}"],
            "samples": ["sample value " * 20],
        }
        for idx in range(120)
    ]
    manifest = build_schema_manifest(
        data_path="/tmp/workspace.duckdb",
        workspace_schema={"tables": [{"table_name": "wide_table", "context": "Wide table", "columns": columns}]},
    )

    pack = build_schema_context_pack(manifest=manifest, context_window=30_000)

    assert pack["mode"] == "compact"
    first_column = pack["tables"][0]["columns"][0]
    assert set(first_column) == {"name", "dtype", "aliases"}
    assert "column.description" in pack["omitted"]["fields"]
