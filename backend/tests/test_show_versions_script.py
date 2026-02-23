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
        "backend/app/main.py.APP_VERSION",
        "src-tauri/Cargo.toml.version",
        "src-tauri/tauri.conf.json.version",
        "frontend/package.json.version",
        "frontend/package-lock.json.version",
        "frontend/package-lock.json.packages[''].version",
        "scripts/install-inquira.sh.wheel_version",
        "scripts/install-inquira.ps1.wheel_version",
    }
    assert expected_keys.issubset(set(data.keys()))


def test_collect_versions_reads_version_file_value():
    mod = _load_module()
    data = mod.collect_versions()
    current = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert data["VERSION"] == current
