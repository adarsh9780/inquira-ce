from __future__ import annotations

from agent_v2.coding_subagent.schema import AnalysisOutput


def test_analysis_output_schema_uses_strict_output_contract_items() -> None:
    schema = AnalysisOutput.model_json_schema()
    defs = schema["$defs"]
    output_contract_item = defs["OutputContractItem"]

    assert output_contract_item["type"] == "object"
    assert output_contract_item["additionalProperties"] is False
    assert set(output_contract_item["required"]) == set(output_contract_item["properties"])
    assert set(schema["required"]) == set(schema["properties"])
    assert output_contract_item["properties"]["name"]["type"] == "string"
    assert output_contract_item["properties"]["kind"]["type"] == "string"
    assert "default" not in str(schema)
