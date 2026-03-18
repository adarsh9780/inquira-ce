import ast
from pathlib import Path


def _imports_old_agent(module_path: Path) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.agent"):
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if module.startswith("app.agent"):
                violations.append(f"from {module} import ...")
            if node.level >= 1 and module.startswith("agent"):
                violations.append(f"from {'.' * node.level}{module} import ...")

    return violations


def test_agent_v2_has_no_imports_from_legacy_agent_package():
    agent_v2_root = Path(__file__).resolve().parents[1] / "app" / "agent_v2"
    offenders: list[str] = []

    for py_file in sorted(agent_v2_root.rglob("*.py")):
        for violation in _imports_old_agent(py_file):
            offenders.append(f"{py_file.relative_to(agent_v2_root)}: {violation}")

    assert not offenders, "agent_v2 still depends on legacy app.agent modules:\n" + "\n".join(offenders)
