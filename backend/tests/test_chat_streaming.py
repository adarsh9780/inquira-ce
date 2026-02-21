import json

from app.api.chat import _build_data_analysis_response, _to_sse


def test_to_sse_formats_event_with_json_payload():
    payload = {"stage": "start", "message": "Starting analysis"}
    msg = _to_sse("status", payload)
    assert msg.startswith("event: status\n")
    assert "\ndata: " in msg
    assert msg.endswith("\n\n")
    assert json.loads(msg.split("data: ", 1)[1].strip()) == payload


def test_build_data_analysis_response_prefers_plan_when_code_present():
    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "df = await query('SELECT 1')\ndf",
        "plan": "This is the planned explanation",
        "messages": [],
    }
    response = _build_data_analysis_response(result)
    assert response.is_safe is True
    assert response.is_relevant is True
    assert "await query" in response.code
    assert response.explanation == "This is the planned explanation"
