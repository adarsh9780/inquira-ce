from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

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
