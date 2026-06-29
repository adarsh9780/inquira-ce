from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "maintenance" / "show_versions.py"


def _load_module():
    spec = spec_from_file_location("show_versions", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load show_versions script module")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collect_versions_includes_expected_keys():
    mod = _load_module()
    data = mod.collect_versions()
    expected_keys = {
        "VERSION",
        "backend/pyproject.toml.version",
        "backend/uv.lock.inquira-ce.version",
        "backend/app/main.py.APP_VERSION",
        "src-tauri/Cargo.toml.version",
        "src-tauri/tauri.conf.json.version",
        "frontend/package.json.version",
        "frontend/package-lock.json.version",
        "frontend/package-lock.json.packages[''].version",
    }
    assert expected_keys.issubset(set(data.keys()))


def test_collect_versions_reads_version_file_value():
    mod = _load_module()
    data = mod.collect_versions()
    current = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert data["VERSION"] == current


def test_versions_aligned_returns_true_only_when_all_values_match():
    mod = _load_module()
    assert mod.versions_aligned({"a": "1.0.0", "b": "1.0.0"}) is True
    assert mod.versions_aligned({"a": "1.0.0", "b": "1.0.1"}) is False


def test_verify_mode_fails_for_mismatched_versions(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setattr(mod, "collect_versions", lambda: {"VERSION": "1.0.0", "other": "1.0.1"})

    assert mod.main(["--verify"]) == 1
    captured = capsys.readouterr()
    assert "version mismatch detected" in captured.err
