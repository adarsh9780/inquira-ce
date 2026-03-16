from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_install_scripts_do_not_reference_wheel_downloads():
    sh_script = (ROOT / "scripts" / "install-inquira.sh").read_text(encoding="utf-8")
    ps_script = (ROOT / "scripts" / "install-inquira.ps1").read_text(encoding="utf-8")

    combined = sh_script + "\n" + ps_script

    assert "py3-none-any.whl" not in combined
    assert "desktop builds only" in combined
    assert "releases/latest" in combined
