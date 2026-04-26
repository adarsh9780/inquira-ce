from app.v1.services.chat_service import ChatService


def test_agent_execution_is_authoritative_for_success_without_artifacts():
    response_payload = {
        "execution": {"status": "success", "success": True},
        "metadata": {"execution_source": "workspace_runtime"},
        "artifacts": [],
    }
    result_payload = {"final_executed_code": "result = 1"}

    assert ChatService._agent_execution_is_authoritative(
        response_payload=response_payload,
        result_payload=result_payload,
        code_to_execute="result = 1",
    )


def test_agent_execution_requires_runtime_source_contract():
    response_payload = {
        "execution": {"status": "success", "success": True},
        "metadata": {},
        "artifacts": [],
    }

    assert not ChatService._agent_execution_is_authoritative(
        response_payload=response_payload,
        result_payload={"final_executed_code": "result = 1"},
        code_to_execute="result = 1",
    )
