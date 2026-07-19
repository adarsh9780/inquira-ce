from __future__ import annotations

import asyncio
import json

import pytest

from inquira_data_worker.schema_generation import SchemaGenerator, validate_schema_request


class FakeModel:
    def __init__(self) -> None:
        self.prompts: list[list[dict[str, str]]] = []

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.prompts.append(messages)
        prompt = messages[-1]["content"]
        payload = json.loads(prompt.split("Columns JSON:\n", 1)[1])
        return "```json\n" + json.dumps({"columns": [
            {"name": column["name"], "description": f"Description for {column['name']}", "aliases": [f"{column['name']} alias"]}
            for column in reversed(payload)
        ]}) + "\n```"


def test_schema_generator_batches_columns_and_returns_bounded_metadata() -> None:
    async def scenario() -> None:
        model = FakeModel()
        generator = SchemaGenerator(model_factory=lambda _: model, batch_size=2)
        result = await generator.generate({
            "workspace_id": "workspace-1",
            "table_name": "sales",
            "context": "Finance reporting",
            "columns": [{"name": f"column_{index}", "dtype": "VARCHAR", "nullable": True} for index in range(5)],
            "model": {"provider": "openai", "model": "gpt-lite", "api_key": "secret", "base_url": "https://example.test"},
        })
        assert len(model.prompts) == 3
        assert [item["name"] for item in result["columns"]] == ["column_1", "column_0", "column_3", "column_2", "column_4"]
        assert result["columns"][0]["aliases"] == ["column_1 alias"]
        assert "Finance reporting" in model.prompts[0][-1]["content"]
        assert "secret" not in model.prompts[0][-1]["content"]

    asyncio.run(scenario())


def test_schema_generator_splits_length_limited_batches_until_they_fit() -> None:
    class LengthLimitedModel(FakeModel):
        async def complete(self, messages: list[dict[str, str]]) -> str:
            self.prompts.append(messages)
            payload = json.loads(messages[-1]["content"].split("Columns JSON:\n", 1)[1])
            if len(payload) > 1:
                raise RuntimeError("The provider reached its length limit")
            return json.dumps({"columns": [{
                "name": payload[0]["name"], "description": "Generated", "aliases": []
            }]})

    async def scenario() -> None:
        model = LengthLimitedModel()
        generator = SchemaGenerator(model_factory=lambda _: model, batch_size=20)
        result = await generator.generate({
            "workspace_id": "workspace-1", "table_name": "sales", "context": "",
            "columns": [{"name": f"column_{index}", "dtype": "BIGINT", "nullable": False} for index in range(4)],
            "model": {"provider": "openai", "model": "gpt-lite", "api_key": "secret", "base_url": "https://example.test"},
        })
        assert len(result["columns"]) == 4
        assert len(model.prompts) == 7

    asyncio.run(scenario())


@pytest.mark.parametrize("params", [
    {},
    {"workspace_id": "../escape", "table_name": "sales", "context": "", "columns": [], "model": {}},
    {"workspace_id": "workspace", "table_name": "sales", "context": "x" * 8001, "columns": [], "model": {}},
    {"workspace_id": "workspace", "table_name": "sales", "context": "", "columns": [{"name": "", "dtype": "VARCHAR"}], "model": {}},
])
def test_schema_request_validation_rejects_invalid_or_unbounded_inputs(params: dict) -> None:
    with pytest.raises(ValueError):
        validate_schema_request(params)
