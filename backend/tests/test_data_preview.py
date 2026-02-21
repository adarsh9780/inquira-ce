import pytest
from fastapi import HTTPException

from app.api.data_preview import read_file_with_duckdb_sample


def test_read_file_with_duckdb_sample_browser_path_returns_400():
    """Regression: browser:// should not be masked as 500."""
    with pytest.raises(HTTPException) as exc:
        read_file_with_duckdb_sample("browser://sales_data", sample_type="random")

    assert exc.value.status_code == 400
    assert "frontend runtime" in str(exc.value.detail)


def test_read_file_with_duckdb_sample_missing_file_returns_404():
    """Regression: missing files should preserve 404 instead of converting to 500."""
    with pytest.raises(HTTPException) as exc:
        read_file_with_duckdb_sample("/tmp/definitely_missing_file.csv", sample_type="random")

    assert exc.value.status_code == 404
