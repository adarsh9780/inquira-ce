from pathlib import Path

from app.coding_agent import AnalysisOutput, invoke_coding_chain


def test_coding_agent_prompt_is_self_contained():
    root = Path(__file__).resolve().parents[2]
    prompt_path = root / "backend" / "app" / "coding_agent" / "prompts" / "coding_system.yaml"
    source = prompt_path.read_text(encoding="utf-8")

    assert "dedicated coding subagent" in source
    assert "search_schema_queries" in source
    assert "conn.sql(...)" in source


def test_invoke_coding_chain_normalizes_structured_output_dict():
    captured: dict[str, object] = {}

    def fake_invoker(chain, payload):
        captured["chain"] = chain
        captured["payload"] = payload
        return {
            "code": "print('ok')",
            "explanation": "done",
            "output_contract": [{"name": "result_df", "kind": "dataframe"}],
            "search_schema_queries": ["revenue"],
            "selected_tables": ["sales"],
            "join_keys": [],
            "joins_used": False,
        }

    result = invoke_coding_chain(
        chain=object(),
        messages=[],
        table_name="sales",
        workspace_tables_json='["sales"]',
        workspace_db_path="/tmp/workspace.db",
        schema_summary="sales: id, revenue",
        known_columns_json="[]",
        sample_table="sales",
        sample_json='{"row_count": 0}',
        context="",
        invoke_structured_chain=fake_invoker,
    )

    assert isinstance(result, AnalysisOutput)
    assert result.code == "print('ok')"
    assert result.search_schema_queries == ["revenue"]
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["table_name"] == "sales"
