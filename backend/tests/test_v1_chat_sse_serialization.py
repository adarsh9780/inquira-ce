import json

from app.v1.api.chat import _to_sse


def _extract_sse_data(event_text: str) -> dict:
    for line in event_text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: ") :])
    raise AssertionError("Missing data line in SSE payload")


def test_to_sse_replaces_non_finite_numbers_with_null() -> None:
    event_text = _to_sse(
        "tool_result",
        {
            "call_id": "sample_data_demo",
            "status": "success",
            "output": {
                "rows": [
                    {
                        "runs": float("nan"),
                        "strike_rate": float("inf"),
                        "economy": float("-inf"),
                    }
                ]
            },
        },
    )

    parsed = _extract_sse_data(event_text)
    row = parsed["output"]["rows"][0]

    assert parsed["call_id"] == "sample_data_demo"
    assert parsed["status"] == "success"
    assert row["runs"] is None
    assert row["strike_rate"] is None
    assert row["economy"] is None
