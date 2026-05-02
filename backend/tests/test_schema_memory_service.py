from __future__ import annotations

import json

from app.v1.services.schema_memory_service import SchemaMemoryService


def test_schema_memory_service_reuses_and_extends_existing_memory() -> None:
    current_memory = json.dumps(
        {
            "schema_version": 1,
            "data_fingerprint": "old",
            "tables_loaded": ["orders"],
            "columns_loaded": {"orders": ["order_id", "customer_id"]},
            "join_paths": [],
            "important_notes": ["orders.order_id: primary key"],
            "token_estimate": 20,
        }
    )
    turn_usage = SchemaMemoryService.build_turn_schema_usage(
        workspace_schema={
            "table_name": "orders",
            "tables": [
                {
                    "table_name": "orders",
                    "context": "Fact table",
                    "columns": [
                        {"name": "order_id", "description": "primary key"},
                        {"name": "revenue", "description": "net revenue"},
                    ],
                },
                {
                    "table_name": "customers",
                    "context": "Dimension table",
                    "columns": [{"name": "customer_id", "description": "customer key"}],
                },
            ],
        },
        data_path="/tmp/workspace.db",
    )

    merged_json, merged_version = SchemaMemoryService.merge_conversation_schema_memory(
        current_memory,
        3,
        turn_usage,
    )
    merged = json.loads(merged_json)

    assert merged_version == 4
    assert merged["tables_loaded"] == ["orders", "customers"]
    assert merged["columns_loaded"]["orders"] == ["order_id", "customer_id", "revenue"]
    assert merged["columns_loaded"]["customers"] == ["customer_id"]
    assert "orders: Fact table" in merged["important_notes"]
    assert merged["data_fingerprint"]
