"""Compile the desktop slash-command catalog into workspace-kernel code."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any


DEFAULT_ROW_LIMIT = 500
MAX_ROW_LIMIT = 2000


class CommandExecutionError(ValueError):
    """Raised when a slash command cannot be resolved safely."""


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    usage: str
    description: str
    category: str


COMMAND_DEFINITIONS = [
    CommandDefinition("describe", "/describe <table>", "Profile columns using DuckDB SUMMARIZE", "overview"),
    CommandDefinition("info", "/info <table>", "Show table structure and row count", "overview"),
    CommandDefinition("shape", "/shape <table>", "Show row count and column count", "overview"),
    CommandDefinition("dtypes", "/dtypes <table>", "List columns and data types", "overview"),
    CommandDefinition("head", "/head <table> [n]", "Preview first N rows (default 10)", "overview"),
    CommandDefinition("tail", "/tail <table> [n]", "Preview last N rows (default 10)", "overview"),
    CommandDefinition("sample", "/sample <table> [n]", "Preview random N rows (default 10)", "overview"),
    CommandDefinition("mean", "/mean <table>.<col>", "Arithmetic mean of numeric column", "column_stats"),
    CommandDefinition("median", "/median <table>.<col>", "Median of numeric column", "column_stats"),
    CommandDefinition("mode", "/mode <table>.<col>", "Most frequent value in column", "column_stats"),
    CommandDefinition("std", "/std <table>.<col>", "Standard deviation", "column_stats"),
    CommandDefinition("sum", "/sum <table>.<col>", "Sum of values", "column_stats"),
    CommandDefinition("min", "/min <table>.<col>", "Minimum value", "column_stats"),
    CommandDefinition("max", "/max <table>.<col>", "Maximum value", "column_stats"),
    CommandDefinition("percentile", "/percentile <table>.<col> [p]", "Pth percentile (default 50)", "column_stats"),
    CommandDefinition("value_counts", "/value_counts <table>.<col> [n]", "Top N value counts (default 20)", "distribution"),
    CommandDefinition("unique", "/unique <table>.<col>", "Distinct count with sample values", "distribution"),
    CommandDefinition("histogram", "/histogram <table>.<col> [bins]", "Bucketed distribution (default 10 bins)", "distribution"),
    CommandDefinition("corr", "/corr <table>.<c1> <c2>", "Pearson correlation between two columns", "distribution"),
    CommandDefinition("crosstab", "/crosstab <table>.<c1> <c2>", "Cross-tab style frequency counts", "distribution"),
    CommandDefinition("nulls", "/nulls <table> OR /nulls <table>.<col>", "Null counts per column or for one column", "quality"),
    CommandDefinition("duplicates", "/duplicates <table> [col1,col2,...]", "Duplicate rows/groups by columns", "quality"),
    CommandDefinition("outliers", "/outliers <table>.<col>", "Rows outside 1.5*IQR bounds", "quality"),
    CommandDefinition("help", "/help [command]", "List commands or show command usage", "help"),
]


def list_command_definitions() -> list[dict[str, str]]:
    return [item.__dict__.copy() for item in COMMAND_DEFINITIONS]


@dataclass(frozen=True)
class _Catalog:
    tables: dict[str, str]
    columns: dict[str, dict[str, str]]


def _catalog(rows: Any) -> _Catalog:
    tables: dict[str, str] = {}
    columns: dict[str, dict[str, str]] = {}
    if not isinstance(rows, list):
        raise CommandExecutionError("Command columns must be an array.")
    for row in rows:
        if not isinstance(row, dict):
            continue
        table = str(row.get("table_name") or "").strip()
        column = str(row.get("column_name") or "").strip()
        if not table or not column:
            continue
        tables[table.lower()] = table
        columns.setdefault(table, {})[column.lower()] = column
    return _Catalog(tables, columns)


def _parse(payload: dict[str, Any]) -> tuple[str, str, list[str]]:
    text = str(payload.get("text") or "").strip()
    if text:
        if not text.startswith("/"):
            raise CommandExecutionError("Commands must start with '/'.")
        try:
            tokens = shlex.split(text)
        except ValueError as exc:
            raise CommandExecutionError(f"Could not parse command: {exc}") from exc
        if not tokens or not tokens[0][1:].strip():
            raise CommandExecutionError("Missing command name after '/'.")
        return tokens[0][1:].strip().lower(), " ".join(tokens[1:]), tokens[1:]

    name = str(payload.get("name") or "").strip().lstrip("/").lower()
    raw_args = str(payload.get("raw_args") or "").strip()
    if not name:
        raise CommandExecutionError("Provide either command text or command name.")
    try:
        args = shlex.split(raw_args) if raw_args else []
    except ValueError as exc:
        raise CommandExecutionError(f"Could not parse command: {exc}") from exc
    return name, raw_args, args


def _qi(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _ql(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _table(catalog: _Catalog, token: str | None, default: str | None) -> str:
    candidate = str(token or default or "").strip()
    if not candidate:
        raise CommandExecutionError("Table name is required.")
    resolved = catalog.tables.get(candidate.lower())
    if not resolved:
        raise CommandExecutionError(f"Unknown table: {candidate}")
    return resolved


def _column(catalog: _Catalog, table: str, token: str) -> str:
    candidate = str(token or "").strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {'"', "'"}:
        candidate = candidate[1:-1]
    resolved = catalog.columns.get(table, {}).get(candidate.lower())
    if not resolved:
        raise CommandExecutionError(f"Unknown column '{candidate}' in table '{table}'")
    return resolved


def _column_ref(catalog: _Catalog, token: str, default: str | None) -> tuple[str, str]:
    value = str(token or "").strip()
    if "." in value:
        table_name, column_name = value.split(".", 1)
        table = _table(catalog, table_name, default)
        return table, _column(catalog, table, column_name)
    if value.endswith("]") and "[" in value:
        table_name, column_name = value[:-1].split("[", 1)
        table = _table(catalog, table_name, default)
        return table, _column(catalog, table, column_name)
    table = _table(catalog, None, default)
    return table, _column(catalog, table, value)


def _consume_ref(
    catalog: _Catalog, args: list[str], default: str | None, start: int = 0
) -> tuple[str, str, int]:
    match: tuple[str, str, int] | None = None
    for end in range(start + 1, len(args) + 1):
        token = " ".join(args[start:end]).strip()
        try:
            table, column = _column_ref(catalog, token, default)
        except CommandExecutionError:
            continue
        match = table, column, end
    if match is None:
        unresolved = " ".join(args[start:]).strip() or "<empty>"
        raise CommandExecutionError(
            "Column reference is required (expected table.column). "
            f"Could not resolve: {unresolved}"
        )
    return match


def _positive_int(
    raw: str | None, default: int, *, minimum: int = 1, maximum: int = MAX_ROW_LIMIT
) -> int:
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise CommandExecutionError(f"Expected an integer value, got: {raw}") from exc
    if value < minimum or value > maximum:
        raise CommandExecutionError(f"Value must be between {minimum} and {maximum}.")
    return value


_PREAMBLE = """
from datetime import date as _cmd_date, datetime as _cmd_datetime, time as _cmd_time
from decimal import Decimal as _cmd_decimal

def _cmd_safe_value(value):
    if isinstance(value, (_cmd_datetime, _cmd_date, _cmd_time)):
        return value.isoformat()
    if isinstance(value, _cmd_decimal):
        return float(value)
    return value

def _cmd_run_sql(sql, row_limit, result_type='table'):
    _cursor = conn.execute(sql)
    _columns = [str(item[0]) for item in (_cursor.description or [])]
    _fetched = _cursor.fetchmany(max(1, int(row_limit)) + 1)
    _truncated = len(_fetched) > int(row_limit)
    _data = [
        {name: _cmd_safe_value(row[index] if index < len(row) else None) for index, name in enumerate(_columns)}
        for row in _fetched[:int(row_limit)]
    ]
    return {'columns': _columns, 'data': _data, 'row_count': len(_data), 'result_type': result_type}, _truncated
"""


def _table_code(name: str, sql: str, output: str, limit: int) -> str:
    return (
        _PREAMBLE
        + f"_cmd_payload, _cmd_truncated = _cmd_run_sql({json.dumps(sql)}, {limit}, 'table')\n"
        + f"_cmd_result = {{'name': {name!r}, 'output': {output!r}, 'result_type': 'table', 'result': _cmd_payload, 'truncated': bool(_cmd_truncated)}}\n"
        + "_cmd_result\n"
    )


def _scalar_code(name: str, sql: str, prefix: str, key: str, limit: int = 10) -> str:
    return (
        _PREAMBLE
        + f"_cmd_payload, _cmd_truncated = _cmd_run_sql({json.dumps(sql)}, {limit}, 'scalar')\n"
        + "_cmd_rows = _cmd_payload.get('data') or []\n"
        + f"_cmd_scalar = _cmd_rows[0].get({key!r}) if _cmd_rows else None\n"
        + "_cmd_payload['scalar'] = _cmd_scalar\n"
        + f"_cmd_result = {{'name': {name!r}, 'output': {prefix!r} + str(_cmd_scalar), 'result_type': 'scalar', 'result': _cmd_payload, 'truncated': bool(_cmd_truncated)}}\n"
        + "_cmd_result\n"
    )


def _compiled(name: str, output: str, result_type: str, code: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "output": output, "result_type": result_type, "python_code": code, **extra}


def _help(args: list[str]) -> dict[str, Any]:
    definitions = COMMAND_DEFINITIONS
    output = "Available slash commands."
    if args:
        wanted = str(args[0]).lstrip("/").lower()
        definitions = [item for item in definitions if item.name == wanted]
        if not definitions:
            raise CommandExecutionError(f"Unknown command: {wanted}")
        output = f"Help for /{wanted}"
    rows = [
        {"command": f"/{item.name}", "usage": item.usage, "description": item.description, "category": item.category}
        for item in definitions
    ]
    result = {
        "columns": ["command", "usage", "description", "category"],
        "data": rows,
        "row_count": len(rows),
        "result_type": "table",
    }
    payload = {"name": "help", "output": output, "result_type": "table", "result": result, "truncated": False}
    return _compiled("help", output, "table", f"_cmd_result = {payload!r}\n_cmd_result\n", result=result, truncated=False)


def compile_command(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and compile one command without touching the workspace database."""
    if not isinstance(payload, dict):
        raise CommandExecutionError("Command request must be an object.")
    name, _raw_args, args = _parse(payload)
    known = {item.name for item in COMMAND_DEFINITIONS}
    if name not in known:
        raise CommandExecutionError(f"Unknown command '/{name}'.")
    if name == "help":
        return _help(args)

    catalog = _catalog(payload.get("columns", []))
    if not catalog.tables:
        raise CommandExecutionError("No tables found in workspace database.")
    default_table = str(payload.get("default_table") or "").strip() or None
    row_limit = max(1, min(int(payload.get("row_limit") or DEFAULT_ROW_LIMIT), MAX_ROW_LIMIT))

    if name in {"describe", "info", "shape", "dtypes", "head", "tail", "sample"}:
        table = _table(catalog, args[0] if args else None, default_table)
        qt, literal = _qi(table), _ql(table)
        if name == "describe":
            sql = f"SUMMARIZE SELECT * FROM {qt}"
        elif name == "info":
            sql = f"SELECT p.cid, p.name AS column_name, p.type AS dtype, p.notnull AS not_null, p.pk FROM pragma_table_info({literal}) p ORDER BY p.cid"
        elif name == "shape":
            sql = f"SELECT COUNT(*) AS row_count, (SELECT COUNT(*) FROM pragma_table_info({literal})) AS column_count FROM {qt}"
        elif name == "dtypes":
            sql = f"SELECT p.name AS column_name, p.type AS dtype FROM pragma_table_info({literal}) p ORDER BY p.cid"
        else:
            count = _positive_int(args[1] if len(args) > 1 else None, 10)
            if name == "head":
                sql = f"SELECT * FROM {qt} LIMIT {count}"
            elif name == "tail":
                sql = f"WITH numbered AS (SELECT *, ROW_NUMBER() OVER () AS __rownum FROM {qt}) SELECT * EXCLUDE (__rownum) FROM numbered ORDER BY __rownum DESC LIMIT {count}"
            else:
                sql = f"SELECT * FROM {qt} USING SAMPLE {count} ROWS"
        output = f"/{name} executed for table '{table}'."
        return _compiled(name, output, "table", _table_code(name, sql, output, row_limit))

    if name in {"mean", "median", "mode", "std", "sum", "min", "max", "percentile"}:
        table, column, next_arg = _consume_ref(catalog, args, default_table)
        expressions = {
            "mean": "AVG", "median": "MEDIAN", "mode": "MODE", "std": "STDDEV_SAMP",
            "sum": "SUM", "min": "MIN", "max": "MAX",
        }
        if name == "percentile":
            percentile = _positive_int(args[next_arg] if len(args) > next_arg else None, 50, maximum=100)
            expression = f"QUANTILE_CONT({_qi(column)}, {percentile / 100.0})"
        else:
            expression = f"{expressions[name]}({_qi(column)})"
        sql = f"SELECT {expression} AS value FROM {_qi(table)}"
        return _compiled(name, "", "scalar", _scalar_code(name, sql, f"/{name} for {table}.{column}: ", "value"))

    if name in {"value_counts", "unique", "histogram"}:
        table, column, next_arg = _consume_ref(catalog, args, default_table)
        qt, qc = _qi(table), _qi(column)
        if name == "value_counts":
            count = _positive_int(args[next_arg] if len(args) > next_arg else None, 20)
            sql = f"SELECT {qc} AS value, COUNT(*) AS count FROM {qt} GROUP BY {qc} ORDER BY count DESC, value LIMIT {count}"
        elif name == "unique":
            sql = f"WITH stats AS (SELECT COUNT(DISTINCT {qc}) AS distinct_count FROM {qt}), samples AS (SELECT DISTINCT {qc} AS sample_value FROM {qt} LIMIT 50) SELECT stats.distinct_count, samples.sample_value FROM stats LEFT JOIN samples ON TRUE"
        else:
            bins = _positive_int(args[next_arg] if len(args) > next_arg else None, 10, minimum=2, maximum=100)
            sql = f"WITH ranked AS (SELECT NTILE({bins}) OVER (ORDER BY {qc}) AS bucket FROM {qt} WHERE {qc} IS NOT NULL) SELECT bucket, COUNT(*) AS frequency FROM ranked GROUP BY bucket ORDER BY bucket"
        output = f"/{name} executed for {table}.{column}."
        return _compiled(name, output, "table", _table_code(name, sql, output, row_limit))

    if name in {"corr", "crosstab"}:
        table, first, next_arg = _consume_ref(catalog, args, default_table)
        if next_arg >= len(args):
            raise CommandExecutionError(f"/{name} requires two columns.")
        second_table, second, _ = _consume_ref(catalog, args, table, next_arg)
        if second_table.lower() != table.lower():
            raise CommandExecutionError("Both columns must belong to the same table.")
        qt, q1, q2 = _qi(table), _qi(first), _qi(second)
        if name == "corr":
            sql = f"SELECT CORR({q1}, {q2}) AS correlation FROM {qt}"
            return _compiled(name, "", "scalar", _scalar_code(name, sql, f"/corr for {table}.{first} and {table}.{second}: ", "correlation", 5))
        sql = f"SELECT {q1} AS col_1, {q2} AS col_2, COUNT(*) AS count FROM {qt} GROUP BY {q1}, {q2} ORDER BY count DESC LIMIT {row_limit}"
        output = f"/crosstab executed for {table}.{first} and {table}.{second}."
        return _compiled(name, output, "table", _table_code(name, sql, output, row_limit))

    if name == "nulls":
        if not args:
            raise CommandExecutionError("/nulls requires a table or table.column argument.")
        target = " ".join(args).strip()
        try:
            table = _table(catalog, target, default_table)
        except CommandExecutionError:
            table, column, _ = _consume_ref(catalog, args, default_table)
            sql = f"SELECT COUNT(*) FILTER (WHERE {_qi(column)} IS NULL) AS null_count, COUNT(*) FILTER (WHERE {_qi(column)} IS NOT NULL) AS non_null_count FROM {_qi(table)}"
            return _compiled(name, "", "scalar", _scalar_code(name, sql, f"/nulls for {table}.{column}: ", "null_count", 5))
        pieces = [
            f"SELECT {_ql(column)} AS column_name, COUNT(*) FILTER (WHERE {_qi(column)} IS NULL) AS null_count FROM {_qi(table)}"
            for column in catalog.columns.get(table, {}).values()
        ]
        sql = " UNION ALL ".join(pieces)
        output = f"/nulls executed for table '{table}'."
        return _compiled(name, output, "table", _table_code(name, sql, output, row_limit))

    if name == "duplicates":
        if not args:
            raise CommandExecutionError("/duplicates requires a table argument.")
        table = _table(catalog, args[0], default_table)
        raw_columns = " ".join(args[1:]).strip()
        if raw_columns:
            columns = [_column(catalog, table, item.strip()) for item in raw_columns.split(",") if item.strip()]
        else:
            columns = list(catalog.columns.get(table, {}).values())
        if not columns:
            raise CommandExecutionError("No columns found to evaluate duplicates.")
        group = ", ".join(_qi(item) for item in columns)
        sql = f"SELECT {group}, COUNT(*) AS duplicate_count FROM {_qi(table)} GROUP BY {group} HAVING COUNT(*) > 1 ORDER BY duplicate_count DESC LIMIT {row_limit}"
        output = f"/duplicates executed for table '{table}'."
        return _compiled(name, output, "table", _table_code(name, sql, output, row_limit))

    if name == "outliers":
        table, column, _ = _consume_ref(catalog, args, default_table)
        qt, qc = _qi(table), _qi(column)
        sql = (
            f"WITH quantiles AS (SELECT QUANTILE_CONT({qc}, 0.25) AS q1, QUANTILE_CONT({qc}, 0.75) AS q3 FROM {qt}), "
            "bounds AS (SELECT q1, q3, q1 - 1.5 * (q3 - q1) AS lower_bound, q3 + 1.5 * (q3 - q1) AS upper_bound FROM quantiles) "
            f"SELECT t.*, b.lower_bound, b.upper_bound FROM {qt} t CROSS JOIN bounds b WHERE t.{qc} < b.lower_bound OR t.{qc} > b.upper_bound LIMIT {row_limit}"
        )
        output = f"/outliers executed for {table}.{column}."
        return _compiled(name, output, "table", _table_code(name, sql, output, row_limit))

    raise CommandExecutionError(f"Unsupported command '/{name}'.")
