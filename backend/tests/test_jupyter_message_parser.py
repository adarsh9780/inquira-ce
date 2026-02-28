from app.services.jupyter_message_parser import (
    ParsedExecutionOutput,
    update_from_iopub_message,
)


def test_stream_messages_are_aggregated_to_stdout_and_stderr():
    output = ParsedExecutionOutput()
    update_from_iopub_message(
        output,
        "stream",
        {"name": "stdout", "text": "hello\n"},
    )
    update_from_iopub_message(
        output,
        "stream",
        {"name": "stderr", "text": "warn\n"},
    )
    payload = output.as_response()
    assert payload["stdout"] == "hello"
    assert payload["stderr"] == "warn"
    assert payload["has_stdout"] is True
    assert payload["has_stderr"] is True
    assert payload["success"] is False


def test_execute_result_prefers_plotly_payload_and_sets_figure_type():
    output = ParsedExecutionOutput()
    update_from_iopub_message(
        output,
        "execute_result",
        {"data": {"application/vnd.plotly.v1+json": {"data": [], "layout": {}}}},
    )
    payload = output.as_response()
    assert payload["result_type"] == "Figure"
    assert payload["result"] == {"data": [], "layout": {}}
    assert payload["has_stdout"] is False
    assert payload["has_stderr"] is False


def test_error_message_produces_failure_payload():
    output = ParsedExecutionOutput()
    update_from_iopub_message(
        output,
        "error",
        {"traceback": ["Traceback line 1", "Traceback line 2"]},
    )
    payload = output.as_response()
    assert payload["success"] is False
    assert payload["has_stderr"] is True
    assert "Traceback line 1" in (payload["error"] or "")
