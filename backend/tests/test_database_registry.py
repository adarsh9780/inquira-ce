from __future__ import annotations

import pytest

from app.data_access import (
    AccessMode,
    DatabaseRole,
    OwnershipMode,
    can_accessor_use_database,
    get_database_spec,
    list_database_specs,
)


def test_database_registry_contains_expected_specs() -> None:
    specs = {spec.db_id: spec for spec in list_database_specs()}

    assert set(specs) == {
        "auth_sqlite",
        "appdata_sqlite",
        "workspace_duckdb",
        "turn_blob_store",
    }
    assert specs["auth_sqlite"].role == DatabaseRole.CONTROL_PLANE
    assert specs["workspace_duckdb"].ownership_mode == OwnershipMode.KERNEL_OWNED
    assert specs["turn_blob_store"].role == DatabaseRole.ARTIFACT_BLOB


def test_each_known_database_has_one_ownership_mode() -> None:
    specs = list_database_specs()
    assert len({spec.db_id for spec in specs}) == len(specs)
    for spec in specs:
        assert isinstance(spec.ownership_mode, OwnershipMode)


@pytest.mark.parametrize(
    ("accessor", "db_id", "mode"),
    [
        ("sqlalchemy_session", "auth_sqlite", AccessMode.WRITE_LIVE),
        ("repository", "appdata_sqlite", AccessMode.READ_LIVE),
        ("workspace_runtime_adapter", "workspace_duckdb", AccessMode.READ_LIVE),
        ("workspace_offline_adapter", "workspace_duckdb", AccessMode.METADATA),
        ("artifact_blob_store", "turn_blob_store", AccessMode.READ_OFFLINE),
    ],
)
def test_access_policy_allows_supported_combinations(accessor: str, db_id: str, mode: AccessMode) -> None:
    assert can_accessor_use_database(accessor=accessor, db_id=db_id, access_mode=mode) is True


@pytest.mark.parametrize(
    ("accessor", "db_id", "mode"),
    [
        ("workspace_runtime_adapter", "workspace_duckdb", AccessMode.READ_OFFLINE),
        ("repository", "turn_blob_store", AccessMode.READ_OFFLINE),
        ("artifact_blob_store", "turn_blob_store", AccessMode.WRITE_LIVE),
    ],
)
def test_access_policy_blocks_unsupported_combinations(accessor: str, db_id: str, mode: AccessMode) -> None:
    assert can_accessor_use_database(accessor=accessor, db_id=db_id, access_mode=mode) is False


def test_get_database_spec_raises_for_unknown_id() -> None:
    with pytest.raises(KeyError, match="Unknown database spec"):
        get_database_spec("missing_db")
