from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "maintenance" / "bump_versions.py"


def _load_module():
    spec = spec_from_file_location("bump_versions", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load bump_versions script module")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pep440_to_tauri_semver_prerelease_mapping():
    mod = _load_module()
    assert mod.pep440_to_tauri_semver("0.5.0a1") == "0.5.0-alpha.1"
    assert mod.pep440_to_tauri_semver("0.5.0b2") == "0.5.0-beta.2"
    assert mod.pep440_to_tauri_semver("0.5.0rc3") == "0.5.0-rc.3"
    assert mod.pep440_to_tauri_semver("0.5.0") == "0.5.0"


def test_resolve_target_versions_allows_per_target_overrides():
    mod = _load_module()
    out = mod.resolve_target_versions(
        base_version="0.5.0a1",
        backend_version="0.5.1a2",
        tauri_version="0.5.1-alpha.2",
        frontend_version="0.5.0a1",
    )
    assert out == {
        "base": "0.5.0a1",
        "backend": "0.5.1a2",
        "tauri": "0.5.1-alpha.2",
        "frontend": "0.5.0a1",
    }


def test_run_updates_dry_run_reports_all_effective_versions():
    mod = _load_module()
    lines = mod.run_updates(base_version="0.6.0a1", dry_run=True)
    joined = "\n".join(lines)
    assert "base_version=0.6.0a1" in joined
    assert "backend_version=0.6.0a1" in joined
    assert "tauri_version=0.6.0-alpha.1" in joined
    assert "frontend_version=0.6.0-alpha.1" in joined


def test_normalize_version_input_accepts_tag_style():
    mod = _load_module()
    assert mod.normalize_version_input("v0.5.0a6") == "0.5.0a6"
    assert mod.normalize_version_input("0.5.0a6") == "0.5.0a6"
