import ast
from pathlib import Path


def test_agent_runtime_does_not_import_backend_app_modules():
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []

    for py_file in root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = str(alias.name)
                    if name.startswith("app") or name.startswith("backend"):
                        offenders.append(f"{py_file.relative_to(root)}: import {name}")
            elif isinstance(node, ast.ImportFrom):
                module = str(node.module or "")
                if module.startswith("app") or module.startswith("backend"):
                    offenders.append(f"{py_file.relative_to(root)}: from {module} import ...")

    assert not offenders, "agent-runtime must be backend-independent:\n" + "\n".join(offenders)
