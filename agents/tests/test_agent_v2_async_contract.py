from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_SYNC_METHODS = {"invoke", "stream", "batch"}


def _async_sync_method_violations(source: str, file_path: Path) -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []
    async_fn_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            async_fn_stack.append(node.name)
            self.generic_visit(node)
            async_fn_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            if async_fn_stack and isinstance(node.func, ast.Attribute):
                method_name = str(node.func.attr or "")
                if method_name in FORBIDDEN_SYNC_METHODS:
                    violations.append(
                        (
                            f"{file_path}:{node.lineno} async function "
                            f"'{async_fn_stack[-1]}' uses sync method '{method_name}()'"
                        )
                    )
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


def test_agent_v2_async_methods_do_not_call_sync_runnables() -> None:
    code_root = Path(__file__).resolve().parents[1] / "agent_v2"
    violations: list[str] = []
    for py_file in sorted(code_root.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        violations.extend(_async_sync_method_violations(source, py_file))

    assert not violations, "Async contract violations found:\n" + "\n".join(violations)
