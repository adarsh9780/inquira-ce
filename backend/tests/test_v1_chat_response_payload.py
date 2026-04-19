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


def test_reconcile_success_explanation_keeps_failure_when_no_renderable_artifacts():
    payload = {
        "execution": {"success": True, "status": "success"},
        "explanation": "I could not complete this analysis.",
        "result_explanation": "I could not complete this analysis.",
        "artifacts": [],
        "metadata": {},
    }

    ChatService._reconcile_success_explanation(payload)

    assert payload["explanation"] == "I could not complete this analysis."
    assert payload["result_explanation"] == "I could not complete this analysis."
    assert "result_explanation" not in payload["metadata"]


def test_reconcile_success_explanation_keeps_failure_when_dataframe_artifact_not_viewable():
    payload = {
        "execution": {"success": True, "status": "success"},
        "explanation": "I could not produce safe executable code for this request.",
        "result_explanation": "I could not produce safe executable code for this request.",
        "artifacts": [
            {
                "kind": "dataframe",
                "artifact_id": None,
                "pointer": None,
                "preview_rows": [],
                "status": "ready",
            }
        ],
        "metadata": {},
    }

    ChatService._reconcile_success_explanation(payload)

    assert payload["explanation"] == "I could not produce safe executable code for this request."
    assert payload["result_explanation"] == "I could not produce safe executable code for this request."
    assert "result_explanation" not in payload["metadata"]


def test_reconcile_success_explanation_promotes_success_for_renderable_table_artifact():
    payload = {
        "execution": {"success": True, "status": "success"},
        "explanation": "I could not complete this analysis.",
        "result_explanation": "I could not complete this analysis.",
        "artifacts": [
            {
                "kind": "dataframe",
                "artifact_id": "art-1",
                "pointer": "duckdb://scratchpad/artifacts.duckdb#artifact=art-1",
                "preview_rows": [],
                "status": "ready",
            }
        ],
        "metadata": {},
    }

    ChatService._reconcile_success_explanation(payload)

    expected = "Analysis completed successfully. Results are available in the table view."
    assert payload["explanation"] == expected
    assert payload["result_explanation"] == expected
    assert payload["metadata"]["result_explanation"] == expected
