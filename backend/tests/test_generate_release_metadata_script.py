from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "maintenance" / "generate_release_metadata.py"


def _load_module():
    spec = spec_from_file_location("generate_release_metadata", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load generate_release_metadata script module")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_release_metadata_markdown_supports_heading_title():
    mod = _load_module()
    title, body = mod.parse_release_metadata_markdown(
        "# Inquira v0.5.0a6\n\n- Added fix A\n- Added fix B\n"
    )
    assert title == "Inquira v0.5.0a6"
    assert "- Added fix A" in body
    assert "- Added fix B" in body


def test_build_metadata_payload_sets_version_and_tag():
    mod = _load_module()
    payload = mod.build_metadata_payload(
        version="0.5.0a6",
        title="Inquira v0.5.0a6",
        body="Release notes",
    )
    assert payload["version"] == "0.5.0a6"
    assert payload["tag"] == "v0.5.0a6"
    assert payload["release_name"] == "Inquira v0.5.0a6"
    assert payload["release_body"] == "Release notes"


def test_read_version_uses_version_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    mod = _load_module()
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.9.0rc1\n", encoding="utf-8")
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)

    assert mod._read_version() == "0.9.0rc1"
