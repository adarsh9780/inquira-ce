from fastapi import HTTPException

from app.v1.api.chat import _error_event_payload


def test_error_event_payload_uses_http_exception_status_and_detail():
    payload = _error_event_payload(HTTPException(status_code=502, detail="Agent stream failed"))

    assert payload["status_code"] == 502
    assert payload["detail"] == "Agent stream failed"


def test_error_event_payload_falls_back_to_exception_name_when_empty_message():
    payload = _error_event_payload(RuntimeError(""))

    assert payload["status_code"] == 500
    assert payload["detail"] == "RuntimeError"
