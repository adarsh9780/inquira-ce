from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from .nodes import build_result


class AgentV1Graph:
    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = config
        return build_result(str(state.get("question") or ""))

    async def astream(self, state: dict[str, Any], config: dict[str, Any] | None = None) -> AsyncGenerator[dict[str, Any], None]:
        _ = config
        result = await self.ainvoke(state, config=config)
        yield {"general_chat": {"answer": str(result.get("final_explanation") or "")}}
        yield {"finalize": result}


def build_graph(*_args: Any, **_kwargs: Any) -> AgentV1Graph:
    return AgentV1Graph()
