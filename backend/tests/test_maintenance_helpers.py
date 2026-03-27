from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECK_UV_SCRIPT = ROOT / "scripts" / "maintenance" / "check_uv_version.py"
VERSION_GUARD_SCRIPT = ROOT / "scripts" / "maintenance" / "version_guard.py"


def _load_module(path: Path, name: str):
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_uv_version_parser_extracts_semver_triplet():
    mod = _load_module(CHECK_UV_SCRIPT, "check_uv_version")
    assert mod.parse_uv_version("uv 0.6.3") == "0.6.3"
    assert mod.parse_uv_version("uv version: 0.6.3 (abcd1234)") == "0.6.3"


def test_version_guard_compare_rejects_non_increasing_version(tmp_path: Path):
    mod = _load_module(VERSION_GUARD_SCRIPT, "version_guard")
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.5.24\n", encoding="utf-8")

    args = type("Args", (), {"current_file": str(version_file), "new_version": "0.5.24"})
    try:
        mod.cmd_greater(args)
        assert False, "Expected ValueError for non-increasing version"
    except ValueError as exc:
        assert "must be greater than current VERSION" in str(exc)
