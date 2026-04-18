from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agent_v2.memory.summarizer import build_conversation_memory, summarize_messages


def test_build_conversation_memory_summarizes_older_turns() -> None:
    messages = [
        HumanMessage(content="Need revenue trend by month."),
        AIMessage(content="I will inspect schema."),
        HumanMessage(content="Focus only APAC first."),
        AIMessage(content="Noted."),
        HumanMessage(content="Also compare with EMEA."),
    ]

    memory = build_conversation_memory(
        messages,
        max_recent_messages=2,
        max_summary_chars=800,
    )

    summary = str(memory.get("summary") or "")
    recent = memory.get("recent_messages") or []
    assert "User requests:" in summary
    assert "Need revenue trend by month." in summary
    assert len(recent) == 2


def test_summarize_messages_keeps_recent_window() -> None:
    messages = [
        HumanMessage(content="one"),
        AIMessage(content="two"),
        HumanMessage(content="three"),
    ]
    recent = summarize_messages(messages, max_messages=2)
    assert len(recent) == 2
