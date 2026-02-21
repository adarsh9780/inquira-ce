from app.database import database as db


def test_get_dataset_by_path_skips_error_for_browser_virtual_file_not_found(monkeypatch):
    def _raise_missing(_):
        raise FileNotFoundError("missing")

    calls = []
    monkeypatch.setattr(db, "file_fingerprint_md5", _raise_missing)
    monkeypatch.setattr(db, "logprint", lambda _msg, level="info": calls.append(level))

    result = db.get_dataset_by_path("user-1", "/browser:/ball_by_ball_ipl")
    assert result is None
    assert "error" not in calls
    assert "debug" in calls


def test_get_dataset_by_path_logs_error_for_real_file_not_found(monkeypatch):
    def _raise_missing(_):
        raise FileNotFoundError("missing")

    calls = []
    monkeypatch.setattr(db, "file_fingerprint_md5", _raise_missing)
    monkeypatch.setattr(db, "logprint", lambda _msg, level="info": calls.append(level))

    result = db.get_dataset_by_path("user-1", "/tmp/does-not-exist.csv")
    assert result is None
    assert "error" in calls
