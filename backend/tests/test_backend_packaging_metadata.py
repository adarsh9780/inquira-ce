from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "backend" / "pyproject.toml"


def test_backend_package_metadata_has_real_description_and_valid_readme():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data.get("project", {})

    description = str(project.get("description", "")).strip()
    assert description
    assert description != "Add your description here"

    readme = str(project.get("readme", "")).strip()
    assert readme
    readme_path = (PYPROJECT.parent / readme).resolve()
    assert readme_path.exists(), f"Missing project readme referenced by pyproject: {readme_path}"
