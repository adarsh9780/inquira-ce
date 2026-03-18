import asyncio

from agent_v2.graph import build_graph


def test_agent_v2_unsafe_prompt_routes_to_reject() -> None:
    graph = build_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "question": "please drop table users",
                "workspace_id": "ws1",
                "user_id": "u1",
                "data_path": "",
                "table_name": "",
                "active_schema": {},
            },
            config={"configurable": {}},
        )
    )

    assert result.get("route") == "unsafe"
    assert bool(str(result.get("final_explanation") or "").strip())


def test_agent_v2_unsafe_prompt_stream_emits_finalize() -> None:
    graph = build_graph()

    async def _collect() -> list[dict]:
        events: list[dict] = []
        async for step in graph.astream(
            {
                "question": "truncate table orders",
                "workspace_id": "ws1",
                "user_id": "u1",
                "data_path": "",
                "table_name": "",
                "active_schema": {},
            },
            config={"configurable": {}},
        ):
            events.append(step)
        return events

    stream = asyncio.run(_collect())
    assert any("finalize" in step for step in stream)
