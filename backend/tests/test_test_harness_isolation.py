import os
from pathlib import Path


def test_pytest_harness_uses_temporary_home_and_databases():
    test_home = Path(os.environ["INQUIRA_TEST_HOME"]).resolve()
    assert Path.home().resolve() == test_home

    auth_url = os.environ["INQUIRA_AUTH_DB_URL"]
    appdata_url = os.environ["INQUIRA_APPDATA_DB_URL"]

    expected_auth_path = str((test_home / ".inquira" / "auth_v1.db").as_posix())
    expected_appdata_path = str((test_home / ".inquira" / "appdata_v1.db").as_posix())

    assert auth_url.startswith("sqlite+aiosqlite:///")
    assert appdata_url.startswith("sqlite+aiosqlite:///")
    assert expected_auth_path in auth_url
    assert expected_appdata_path in appdata_url
