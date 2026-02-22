from app.v1.services.chat_service import ChatService


def test_build_response_payload_surfaces_guard_feedback_when_code_blocked():
    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "",
        "code_guard_feedback": "Legacy `await query(...)` bridge detected.",
        "plan": "Plan text should not be used when code is blocked",
        "messages": [],
    }

    payload = ChatService._build_response_payload(result)

    assert payload["code"] == ""
    assert "could not generate executable code" in payload["explanation"]
    assert "Legacy `await query(...)` bridge detected." in payload["explanation"]
