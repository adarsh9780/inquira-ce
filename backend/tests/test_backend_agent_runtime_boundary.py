import ast
from pathlib import Path


def test_backend_does_not_import_agent_runtime_modules():
    backend_root = Path(__file__).resolve().parents[1] / "app"
    offenders: list[str] = []

    for py_file in backend_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if str(alias.name).startswith("agent_runtime"):
                        offenders.append(f"{py_file.relative_to(backend_root)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = str(node.module or "")
                if module.startswith("agent_runtime"):
                    offenders.append(f"{py_file.relative_to(backend_root)}: from {module} import ...")

    assert not offenders, "Backend must call agent via API only:\n" + "\n".join(offenders)
