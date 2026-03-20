from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent_v2.nodes import chat_node


@patch("agent_v2.nodes._emit_text_chunks")
@patch("agent_v2.nodes._get_model")
@patch("agent_v2.nodes._ainvoke_structured_chain")
@pytest.mark.asyncio
async def test_chat_node_no_name_error(mock_ainvoke, mock_get_model, mock_emit_chunks) -> None:
    mock_get_model.return_value = MagicMock()
    # Mock ChatOutput structure
    mock_chat_output = MagicMock()
    mock_chat_output.answer = "Mock response"
    mock_ainvoke.return_value = mock_chat_output

    state = {"messages": [HumanMessage(content="Hello")]}
    config = {"configurable": {}}

    # This will raise a NameError if MessagesPlaceholder is not defined
    result = await chat_node(state, config)

    assert result["route"] == "general_chat"
    assert "Mock response" in result["final_explanation"]


@patch("agent_v2.nodes.ChatPromptTemplate.from_messages")
@patch("agent_v2.nodes._emit_text_chunks")
@patch("agent_v2.nodes._get_model")
@patch("agent_v2.nodes._ainvoke_structured_chain")
@pytest.mark.asyncio
async def test_chat_node_falls_back_to_plain_chain_on_empty_json_parse_error(
    mock_ainvoke,
    mock_get_model,
    _mock_emit_chunks,
    mock_prompt_from_messages,
) -> None:
    class _Prompt:
        def __or__(self, other):
            return other

    mock_prompt_from_messages.return_value = _Prompt()
    model = MagicMock()
    structured_chain = object()
    model.with_structured_output.return_value = structured_chain
    mock_get_model.return_value = model
    mock_ainvoke.side_effect = [
        ValueError("expected value at line 1 column 1"),
        AIMessage(content="Recovered response"),
    ]

    state = {"messages": [HumanMessage(content="Hello")]}
    config = {"configurable": {}}
    result = await chat_node(state, config)

    assert result["route"] == "general_chat"
    assert result["final_explanation"] == "Recovered response"
    assert mock_ainvoke.call_count == 2
    assert mock_ainvoke.call_args_list[0].args[0] is structured_chain
    assert mock_ainvoke.call_args_list[1].args[0] is model
