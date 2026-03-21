import asyncio
import inspect

from agent_v2.graph import _prepare_input_node, build_graph


def test_agent_v2_build_graph_matches_langgraph_factory_signature() -> None:
    params = list(inspect.signature(build_graph).parameters.values())
    assert len(params) == 1
    assert params[0].name == "config"


def test_agent_v2_build_graph_initializes_phoenix_tracing(monkeypatch) -> None:
    called = {"count": 0}

    def fake_init():
        called["count"] += 1
        return True

    monkeypatch.setattr("agent_v2.graph.init_phoenix_tracing", fake_init)
    _ = build_graph({})
    assert called["count"] == 1


def test_agent_v2_unsafe_prompt_routes_to_reject() -> None:
    graph = build_graph({})
    result = asyncio.run(
        graph.ainvoke(
            {
                "question": "please drop table users",
                "workspace_id": "ws1",
                "user_id": "u1",
                "data_path": "",
                "table_names": [],
            },
            config={"configurable": {}},
        )
    )

    assert result.get("route") == "unsafe"
    assert bool(str(result.get("final_explanation") or "").strip())


def test_agent_v2_unsafe_prompt_stream_emits_finalize() -> None:
    graph = build_graph({})

    async def _collect() -> list[dict]:
        events: list[dict] = []
        async for step in graph.astream(
            {
                "question": "truncate table orders",
                "workspace_id": "ws1",
                "user_id": "u1",
                "data_path": "",
                "table_names": [],
            },
            config={"configurable": {}},
        ):
            events.append(step)
        return events

    stream = asyncio.run(_collect())
    assert any("finalize" in step for step in stream)


def test_prepare_input_node_prefers_table_names_list() -> None:
    result = _prepare_input_node(
        {
            "messages": [],
            "question": "show top scorers",
            "workspace_id": "ws1",
            "user_id": "u1",
            "table_names": ["batting", "matches"],
            "current_code": "",
        },
        {},
    )
    assert result.get("table_names") == ["batting", "matches"]


def test_agent_v2_graph_routes_analysis_generate_code_back_to_context_enrichment() -> None:
    graph = build_graph({})
    rendered = graph.get_graph()
    assert any(
        edge.source == "analysis_generate_code"
        and edge.target == "analysis_enrich_context"
        and bool(edge.conditional)
        for edge in rendered.edges
    )


def test_agent_v2_graph_contains_native_toolnode_loop_for_context_enrichment() -> None:
    graph = build_graph({})
    rendered = graph.get_graph()
    assert any(edge.source == "analysis_enrich_context" and edge.target == "analysis_enrich_context_tools" for edge in rendered.edges)
    assert any(edge.source == "analysis_enrich_context_tools" and edge.target == "analysis_enrich_context" for edge in rendered.edges)


def test_agent_v2_graph_contains_runtime_toolnode_routing() -> None:
    graph = build_graph({})
    rendered = graph.get_graph()
    assert any(edge.source == "analysis_prepare_sample_tool" and edge.target == "analysis_runtime_tools" for edge in rendered.edges)
    assert any(edge.source == "analysis_request_execute_tool" and edge.target == "analysis_runtime_tools" for edge in rendered.edges)
    assert any(edge.source == "analysis_request_validate_result_tool" and edge.target == "analysis_runtime_tools" for edge in rendered.edges)
