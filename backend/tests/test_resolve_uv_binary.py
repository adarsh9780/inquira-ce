"""Verify the runner_env _resolve_uv_binary helper works correctly."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

from app.services.runner_env import _resolve_uv_binary


def test_resolve_uv_binary_prefers_env_var(tmp_path):
    """INQUIRA_UV_BIN env var should be preferred when the file exists."""
    fake_uv = tmp_path / "uv"
    fake_uv.write_text("#!/bin/sh\n")
    fake_uv.chmod(0o755)

    with patch.dict(os.environ, {"INQUIRA_UV_BIN": str(fake_uv)}):
        result = _resolve_uv_binary()
    assert result == str(fake_uv)


def test_resolve_uv_binary_ignores_nonexistent_env_var():
    """INQUIRA_UV_BIN should be ignored if the path doesn't exist."""
    with patch.dict(os.environ, {"INQUIRA_UV_BIN": "/nonexistent/uv"}):
        with patch("shutil.which", return_value=None):
            result = _resolve_uv_binary()
    assert result == "uv"


def test_resolve_uv_binary_falls_back_to_which():
    """Should use shutil.which when env var is not set."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("INQUIRA_UV_BIN", None)
        with patch("shutil.which", return_value="/usr/local/bin/uv"):
            result = _resolve_uv_binary()
    assert result == "/usr/local/bin/uv"


def test_resolve_uv_binary_falls_back_to_bare_uv():
    """Should return bare 'uv' when nothing else works."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("INQUIRA_UV_BIN", None)
        with patch("shutil.which", return_value=None):
            result = _resolve_uv_binary()
    assert result == "uv"
