from datetime import datetime, timezone

from app.v1.services.cursor_service import decode_cursor, encode_cursor


def test_cursor_round_trip():
    ts = datetime(2026, 2, 21, 12, 30, tzinfo=timezone.utc)
    cursor = encode_cursor(ts, "turn-1")
    decoded_ts, decoded_id = decode_cursor(cursor)

    assert decoded_id == "turn-1"
    assert decoded_ts == ts


def test_cursor_decode_invalid_returns_none_tuple():
    decoded_ts, decoded_id = decode_cursor("not-valid")
    assert decoded_ts is None
    assert decoded_id is None
