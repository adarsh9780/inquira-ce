from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from .nodes import build_result


class AgentV2Graph:
    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = config
        question = str(state.get("question") or "")
        table_name = str(state.get("table_name") or "data")
        return build_result(question=question, table_name=table_name)

    async def astream(
        self,
        state: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        _ = config
        result = await self.ainvoke(state, config=config)
        yield {"react_loop": {"plan": str((result.get("metadata") or {}).get("plan") or "")}}
        yield {"finalize": result}


def build_graph(*_args: Any, **_kwargs: Any) -> AgentV2Graph:
    return AgentV2Graph()
