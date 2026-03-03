from app.v1.services.chat_service import ChatService


def test_build_response_payload_prefers_final_explanation_when_code_present():
    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "print('hello')",
        "plan": "Plan details",
        "final_explanation": "I generated a simple script and ran it.",
        "messages": [],
    }

    payload = ChatService._build_response_payload(result)

    assert payload["code"] == "print('hello')"
    assert payload["explanation"] == "I generated a simple script and ran it."


def test_build_response_payload_falls_back_to_plan_when_final_explanation_missing():
    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "print('hello')",
        "plan": "Plan fallback explanation",
        "final_explanation": "",
        "messages": [],
    }

    payload = ChatService._build_response_payload(result)

    assert payload["explanation"] == "Plan fallback explanation"


def test_build_node_stream_payload_includes_safety_reasoning():
    event = ChatService._build_node_stream_payload(
        node_name="check_safety",
        payload={
            "metadata": {
                "is_safe": False,
                "safety_reasoning": "The request attempts a destructive action.",
            }
        },
        aggregated={},
    )

    assert event["node"] == "check_safety"
    assert event["decision"] == "unsafe"
    assert event["output"] == "The request attempts a destructive action."
