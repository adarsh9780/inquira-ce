"""Static safety checks for model-generated analysis code."""

from __future__ import annotations

import ast
import re


class UnsafeCodeError(ValueError):
    pass


_BLOCKED_MODULES = {
    "builtins", "ctypes", "glob", "http", "httpx", "os", "pathlib", "requests",
    "shutil", "socket", "subprocess", "sys", "tempfile", "urllib",
}
_BLOCKED_CALLS = {
    "compile", "delattr", "eval", "exec", "getattr", "globals", "input", "locals",
    "open", "setattr", "vars", "__import__",
}
_BLOCKED_ATTRIBUTES = {
    "connect", "read_csv", "read_excel", "read_feather", "read_fwf", "read_html",
    "read_json", "read_orc", "read_parquet", "read_pickle", "read_sas", "read_sql",
    "read_stata", "read_table", "to_csv", "to_excel", "to_feather", "to_json",
    "to_orc", "to_parquet", "to_pickle", "to_sql",
}
_SQL_METHODS = {"execute", "executemany", "query", "sql"}
_SAFE_SQL_STARTS = {"describe", "explain", "from", "select", "show", "summarize", "values", "with"}
_UNSAFE_SQL_PATTERN = re.compile(
    r"\b(attach|call|copy|create\s+secret|detach|export|force\s+install|import|install|load|pragma|set|"
    r"read_(csv|json|ndjson|parquet|text|blob)|read_csv_auto|sqlite_scan|postgres_scan|mysql_scan|httpfs)\b",
    re.IGNORECASE,
)


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
            if isinstance(node.func, ast.Attribute) and node.func.attr in _SQL_METHODS:
                violation = _inspect_sql_call(node)
                if violation:
                    violations.add(violation)
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.add("dunder attribute access is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            violations.add("dunder name access is not allowed")
    if violations:
        raise UnsafeCodeError("; ".join(sorted(violations)))


def _inspect_sql_call(node: ast.Call) -> str | None:
    if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
        return "SQL passed to the workspace connection must be a literal string"
    sql = re.sub(r"/\*.*?\*/|--[^\n]*", " ", node.args[0].value, flags=re.DOTALL).strip()
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    if len(statements) != 1:
        return "only one read-only SQL statement is allowed"
    first = re.match(r"[a-zA-Z]+", statements[0])
    if first is None or first.group(0).lower() not in _SAFE_SQL_STARTS:
        return "only read-only SQL statements are allowed"
    if _UNSAFE_SQL_PATTERN.search(statements[0]):
        return "SQL file, network, extension, or configuration access is not allowed"
    return None
