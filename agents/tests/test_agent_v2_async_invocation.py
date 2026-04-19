from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from agent_v2.coding_subagent.generator import (
    StructuredOutputEmptyError,
    ainvoke_coding_chain,
)
from agent_v2.nodes import _ainvoke_structured_chain


class _AsyncOnlyChain:
    async def ainvoke(self, payload):
        self.last_payload = payload
        return {"code": "print('ok')", "explanation": "done"}

    def invoke(self, payload):  # pragma: no cover - should never run
        raise AssertionError("sync invoke should not be used in async paths")


class _AsyncNoneChain:
    async def ainvoke(self, _payload):
        return None


@pytest.mark.asyncio
async def test_ainvoke_coding_chain_uses_async_chain_invoke() -> None:
    chain = _AsyncOnlyChain()

    result = await ainvoke_coding_chain(
        chain=chain,
        messages=[HumanMessage(content="what tables do i have")],
        table_name="",
        workspace_tables_json="[]",
        workspace_db_path="/tmp/workspace.duckdb",
        schema_summary="",
        known_columns_json="[]",
        sample_table="",
        sample_json="[]",
        context="",
    )

    assert result.code == "print('ok')"
    assert result.explanation == "done"


@pytest.mark.asyncio
async def test_ainvoke_coding_chain_raises_on_empty_structured_output() -> None:
    chain = _AsyncNoneChain()
    with pytest.raises(StructuredOutputEmptyError):
        await ainvoke_coding_chain(
            chain=chain,
            messages=[HumanMessage(content="what tables do i have")],
            table_name="",
            workspace_tables_json="[]",
            workspace_db_path="/tmp/workspace.duckdb",
            schema_summary="",
            known_columns_json="[]",
            sample_table="",
            sample_json="[]",
            context="",
        )


@pytest.mark.asyncio
async def test_nodes_async_structured_invoker_prefers_ainvoke() -> None:
    chain = _AsyncOnlyChain()
    payload = {"messages": [HumanMessage(content="hello")]}

    result = await _ainvoke_structured_chain(chain, payload)

    assert result["code"] == "print('ok')"
    assert getattr(chain, "last_payload", {}) == payload
