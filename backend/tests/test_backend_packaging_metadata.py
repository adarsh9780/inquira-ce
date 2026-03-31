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


def test_backend_runtime_dependencies_exclude_optional_tracing_and_stale_packages():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    runtime_deps = set(data.get("project", {}).get("dependencies", []))
    dev_deps = set(data.get("dependency-groups", {}).get("dev", []))
    debug_deps = set(data.get("dependency-groups", {}).get("debug", []))

    assert "arize-phoenix>=13.3.0" not in runtime_deps
    assert "openinference-instrumentation-langchain>=0.1.59" not in runtime_deps
    assert "rich>=14.3.3" not in runtime_deps

    assert "aiofiles>=24.1.0" not in runtime_deps
    assert "pyjwt[crypto]>=2.10.1" not in runtime_deps
    assert "langchain>=1.0.1" not in runtime_deps
    assert "langgraph-checkpoint-sqlite>=2.0.11" not in runtime_deps
    assert "langgraph-cli[inmem]>=0.4.4" not in runtime_deps
    assert "sse-starlette>=2.1.3" not in runtime_deps

    assert "arize-phoenix>=13.3.0" not in dev_deps
    assert "openinference-instrumentation-langchain>=0.1.59" not in dev_deps
    assert "rich>=14.3.3" not in dev_deps

    assert "arize-phoenix>=13.3.0" in debug_deps
    assert "openinference-instrumentation-langchain>=0.1.59" in debug_deps
    assert "rich>=14.3.3" in debug_deps


def test_backend_dev_group_stays_focused_on_test_and_lint_tooling():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev_deps = set(data.get("dependency-groups", {}).get("dev", []))

    assert dev_deps == {
        "mypy>=1.18.2",
        "pytest>=9.0.2",
        "pytest-asyncio>=1.3.0",
        "ruff>=0.13.1",
    }


def test_backend_runtime_dependencies_keep_greenlet_for_sqlalchemy_async_sessions():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    runtime_deps = set(data.get("project", {}).get("dependencies", []))

    assert "greenlet>=3.2.4" in runtime_deps
