"""Static safety checks for model-generated analysis code."""

from __future__ import annotations

import ast


class UnsafeCodeError(ValueError):
    pass


_BLOCKED_MODULES = {
    "builtins", "ctypes", "glob", "http", "httpx", "os", "pathlib", "requests",
    "shutil", "socket", "subprocess", "sys", "tempfile", "urllib",
}
_BLOCKED_CALLS = {"compile", "eval", "exec", "input", "open", "__import__"}
_BLOCKED_ATTRIBUTES = {
    "connect", "read_csv", "read_excel", "read_feather", "read_fwf", "read_html",
    "read_json", "read_orc", "read_parquet", "read_pickle", "read_sas", "read_sql",
    "read_stata", "read_table", "to_csv", "to_excel", "to_feather", "to_json",
    "to_orc", "to_parquet", "to_pickle", "to_sql",
}


def validate_analysis_code(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise UnsafeCodeError(f"Generated code has invalid Python syntax: {exc.msg}.") from exc
    violations: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                root = name.split(".", 1)[0]
                if root in _BLOCKED_MODULES:
                    violations.add(f"importing {root} is not allowed")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_CALLS:
                violations.add(f"calling {node.func.id} is not allowed")
            if isinstance(node.func, ast.Attribute) and node.func.attr in _BLOCKED_ATTRIBUTES:
                violations.add(f"calling .{node.func.attr} is not allowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.add("dunder attribute access is not allowed")
    if violations:
        raise UnsafeCodeError("; ".join(sorted(violations)))
