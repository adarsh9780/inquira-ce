"""Global pytest isolation so tests never write into a real user profile."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


_TEST_HOME = Path(tempfile.mkdtemp(prefix="inquira-tests-home-")).resolve()
_TEST_INQUIRA_DIR = _TEST_HOME / ".inquira"
_TEST_INQUIRA_DIR.mkdir(parents=True, exist_ok=True)


def _sqlite_async_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


# Force all test imports to use a temporary user home + sqlite files.
os.environ["INQUIRA_TEST_HOME"] = str(_TEST_HOME)
os.environ["HOME"] = str(_TEST_HOME)
os.environ["USERPROFILE"] = str(_TEST_HOME)
if _TEST_HOME.drive:
    os.environ["HOMEDRIVE"] = _TEST_HOME.drive
    os.environ["HOMEPATH"] = str(_TEST_HOME)[len(_TEST_HOME.drive) :]
os.environ["INQUIRA_AUTH_DB_URL"] = _sqlite_async_url(_TEST_INQUIRA_DIR / "auth_v1.db")
os.environ["INQUIRA_APPDATA_DB_URL"] = _sqlite_async_url(_TEST_INQUIRA_DIR / "appdata_v1.db")
os.environ.setdefault("INQUIRA_AUTH_PROVIDER", "sqlite")


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001, ANN201
    _ = (session, exitstatus)
    shutil.rmtree(_TEST_HOME, ignore_errors=True)
