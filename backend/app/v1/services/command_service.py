"""Slash command parsing and execution for workspace DuckDB datasets."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import duckdb


DEFAULT_ROW_LIMIT = 500
MAX_ROW_LIMIT = 2000


class CommandExecutionError(ValueError):
    """Raised when a slash command is invalid or cannot be executed safely."""


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    usage: str
    description: str
    category: str


COMMAND_DEFINITIONS: list[CommandDefinition] = [
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
    return [
        {
            "name": item.name,
            "usage": item.usage,
            "description": item.description,
            "category": item.category,
        }
        for item in COMMAND_DEFINITIONS
    ]


def parse_command_text(text: str) -> tuple[str, str, list[str]]:
    raw = str(text or "").strip()
    if not raw:
        raise CommandExecutionError("Command text is required.")
    if not raw.startswith("/"):
        raise CommandExecutionError("Commands must start with '/'.")

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()

    if not tokens:
        raise CommandExecutionError("Command text is required.")

    command_token = tokens[0].strip()
    name = command_token[1:].strip().lower() if command_token.startswith("/") else command_token.lower()
    if not name:
        raise CommandExecutionError("Missing command name after '/'.")

    args = tokens[1:]
    raw_args = " ".join(args).strip()
    return name, raw_args, args


@dataclass
class _Catalog:
    tables: dict[str, str]
    columns: dict[str, dict[str, str]]
    dtypes: dict[tuple[str, str], str]


@dataclass
class _Result:
    name: str
    output: str
    result_type: str
    result: dict[str, Any] | None
    truncated: bool = False


def _quote_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _safe_value(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows_to_dict(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for idx, column_name in enumerate(columns):
            item[column_name] = _safe_value(row[idx] if idx < len(row) else None)
        out.append(item)
    return out


def _build_catalog(con: duckdb.DuckDBPyConnection) -> _Catalog:
    rows = con.execute(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'main'
        ORDER BY table_name, ordinal_position
        """
    ).fetchall()

    tables: dict[str, str] = {}
    columns: dict[str, dict[str, str]] = {}
    dtypes: dict[tuple[str, str], str] = {}

    for table_name_raw, column_name_raw, dtype_raw in rows:
        table_name = str(table_name_raw)
        column_name = str(column_name_raw)
        dtype = str(dtype_raw or "")
        table_key = table_name.lower()
        column_key = column_name.lower()

        tables[table_key] = table_name
        table_columns = columns.setdefault(table_name, {})
        table_columns[column_key] = column_name
        dtypes[(table_name, column_name)] = dtype

    return _Catalog(tables=tables, columns=columns, dtypes=dtypes)


def _resolve_table(catalog: _Catalog, token: str | None, default_table: str | None = None) -> str:
    candidate = str(token or "").strip()
    if not candidate:
        candidate = str(default_table or "").strip()

    if not candidate:
        raise CommandExecutionError("Table name is required.")

    table = catalog.tables.get(candidate.lower())
    if not table:
        raise CommandExecutionError(f"Unknown table: {candidate}")
    return table


def _resolve_column(catalog: _Catalog, table_name: str, column_token: str) -> str:
    candidate = str(column_token or "").strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {'"', "'"}:
        quote = candidate[0]
        candidate = candidate[1:-1]
        if quote == '"':
            candidate = candidate.replace('""', '"')
        else:
            candidate = candidate.replace("''", "'")
    candidate = candidate.strip()
    if not candidate:
        raise CommandExecutionError("Column name is required.")

    table_columns = catalog.columns.get(table_name, {})
    column = table_columns.get(candidate.lower())
    if not column:
        raise CommandExecutionError(f"Unknown column '{candidate}' in table '{table_name}'")
    return column


def _resolve_table_column_ref(
    catalog: _Catalog,
    ref: str,
    *,
    default_table: str | None = None,
) -> tuple[str, str]:
    token = str(ref or "").strip()
    if not token:
        raise CommandExecutionError("Column reference is required (expected table.column).")

    if "." in token:
        table_part, column_part = token.split(".", 1)
        table_name = _resolve_table(catalog, table_part, default_table)
        column_name = _resolve_column(catalog, table_name, column_part)
        return table_name, column_name

    if token.endswith("]") and "[" in token:
        table_part, column_part = token[:-1].split("[", 1)
        table_name = _resolve_table(catalog, table_part, default_table)
        column_name = _resolve_column(catalog, table_name, column_part)
        return table_name, column_name

    table_name = _resolve_table(catalog, None, default_table)
    column_name = _resolve_column(catalog, table_name, token)
    return table_name, column_name


def _parse_positive_int(value: str | None, default: int, *, min_value: int = 1, max_value: int = MAX_ROW_LIMIT) -> int:
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise CommandExecutionError(f"Expected an integer value, got: {value}") from exc
    if parsed < min_value or parsed > max_value:
        raise CommandExecutionError(f"Value must be between {min_value} and {max_value}.")
    return parsed


def _run_sql(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    *,
    row_limit: int,
    result_type: str = "table",
) -> tuple[dict[str, Any], bool]:
    cursor = con.execute(sql)
    columns = [str(col[0]) for col in (cursor.description or [])]
    fetched = cursor.fetchmany(max(1, row_limit) + 1)
    truncated = len(fetched) > row_limit
    rows = fetched[:row_limit]
    data = _rows_to_dict(columns, rows)
    return {
        "columns": columns,
        "data": data,
        "row_count": len(data),
        "result_type": result_type,
    }, truncated


def _run_help(args: list[str]) -> _Result:
    if not args:
        rows = [
            {
                "command": f"/{item.name}",
                "usage": item.usage,
                "description": item.description,
                "category": item.category,
            }
            for item in COMMAND_DEFINITIONS
        ]
        return _Result(
            name="help",
            output="Available slash commands.",
            result_type="table",
            result={
                "columns": ["command", "usage", "description", "category"],
                "data": rows,
                "row_count": len(rows),
                "result_type": "table",
            },
            truncated=False,
        )

    target = str(args[0] or "").strip().lstrip("/").lower()
    if not target:
        raise CommandExecutionError("Provide a command name, e.g. /help describe")

    found = next((item for item in COMMAND_DEFINITIONS if item.name == target), None)
    if not found:
        raise CommandExecutionError(f"Unknown command: {target}")

    rows = [
        {
            "command": f"/{found.name}",
            "usage": found.usage,
            "description": found.description,
            "category": found.category,
        }
    ]
    return _Result(
        name="help",
        output=f"Help for /{found.name}",
        result_type="table",
        result={
            "columns": ["command", "usage", "description", "category"],
            "data": rows,
            "row_count": 1,
            "result_type": "table",
        },
        truncated=False,
    )


def _run_overview(
    name: str,
    args: list[str],
    *,
    con: duckdb.DuckDBPyConnection,
    catalog: _Catalog,
    default_table: str | None,
    row_limit: int,
) -> _Result:
    table = _resolve_table(catalog, args[0] if args else None, default_table)
    qt = _quote_ident(table)

    if name == "describe":
        sql = f"SUMMARIZE SELECT * FROM {qt}"
    elif name == "info":
        table_literal = _quote_literal(table)
        sql = (
            "SELECT p.cid, p.name AS column_name, p.type AS dtype, p.notnull AS not_null, p.pk "
            f"FROM pragma_table_info({table_literal}) p ORDER BY p.cid"
        )
    elif name == "shape":
        table_literal = _quote_literal(table)
        sql = (
            f"SELECT COUNT(*) AS row_count, "
            f"(SELECT COUNT(*) FROM pragma_table_info({table_literal})) AS column_count "
            f"FROM {qt}"
        )
    elif name == "dtypes":
        table_literal = _quote_literal(table)
        sql = (
            "SELECT p.name AS column_name, p.type AS dtype "
            f"FROM pragma_table_info({table_literal}) p ORDER BY p.cid"
        )
    elif name == "head":
        n = _parse_positive_int(args[1] if len(args) > 1 else None, 10, min_value=1, max_value=MAX_ROW_LIMIT)
        sql = f"SELECT * FROM {qt} LIMIT {n}"
    elif name == "tail":
        n = _parse_positive_int(args[1] if len(args) > 1 else None, 10, min_value=1, max_value=MAX_ROW_LIMIT)
        sql = (
            "WITH numbered AS ("
            f"SELECT *, ROW_NUMBER() OVER () AS __rownum FROM {qt}"
            ") "
            "SELECT * EXCLUDE (__rownum) FROM numbered "
            f"ORDER BY __rownum DESC LIMIT {n}"
        )
    elif name == "sample":
        n = _parse_positive_int(args[1] if len(args) > 1 else None, 10, min_value=1, max_value=MAX_ROW_LIMIT)
        sql = f"SELECT * FROM {qt} USING SAMPLE {n} ROWS"
    else:
        raise CommandExecutionError(f"Unsupported overview command: {name}")

    payload, truncated = _run_sql(con, sql, row_limit=row_limit, result_type="table")
    return _Result(
        name=name,
        output=f"/{name} executed for table '{table}'.",
        result_type="table",
        result=payload,
        truncated=truncated,
    )


def _run_single_column_aggregate(
    name: str,
    args: list[str],
    *,
    con: duckdb.DuckDBPyConnection,
    catalog: _Catalog,
    default_table: str | None,
    row_limit: int,
) -> _Result:
    if not args:
        raise CommandExecutionError(f"/{name} requires a column reference (<table>.<col>).")

    table, column = _resolve_table_column_ref(catalog, args[0], default_table=default_table)
    qt = _quote_ident(table)
    qc = _quote_ident(column)

    if name == "mean":
        expr = f"AVG({qc})"
    elif name == "median":
        expr = f"MEDIAN({qc})"
    elif name == "mode":
        expr = f"MODE({qc})"
    elif name == "std":
        expr = f"STDDEV_SAMP({qc})"
    elif name == "sum":
        expr = f"SUM({qc})"
    elif name == "min":
        expr = f"MIN({qc})"
    elif name == "max":
        expr = f"MAX({qc})"
    elif name == "percentile":
        percentile = _parse_positive_int(args[1] if len(args) > 1 else None, 50, min_value=1, max_value=100)
        quantile = percentile / 100.0
        expr = f"QUANTILE_CONT({qc}, {quantile})"
    else:
        raise CommandExecutionError(f"Unsupported aggregate command: {name}")

    sql = f"SELECT {expr} AS value FROM {qt}"
    payload, truncated = _run_sql(con, sql, row_limit=max(1, min(row_limit, 10)), result_type="scalar")
    rows = payload.get("data") or []
    scalar_value = rows[0].get("value") if rows else None
    payload["scalar"] = scalar_value
    return _Result(
        name=name,
        output=f"/{name} for {table}.{column}: {scalar_value}",
        result_type="scalar",
        result=payload,
        truncated=truncated,
    )


def _run_distribution(
    name: str,
    args: list[str],
    *,
    con: duckdb.DuckDBPyConnection,
    catalog: _Catalog,
    default_table: str | None,
    row_limit: int,
) -> _Result:
    if name in {"value_counts", "unique", "histogram"}:
        if not args:
            raise CommandExecutionError(f"/{name} requires a column reference (<table>.<col>).")
        table, column = _resolve_table_column_ref(catalog, args[0], default_table=default_table)
        qt = _quote_ident(table)
        qc = _quote_ident(column)

        if name == "value_counts":
            n = _parse_positive_int(args[1] if len(args) > 1 else None, 20, min_value=1, max_value=MAX_ROW_LIMIT)
            sql = (
                f"SELECT {qc} AS value, COUNT(*) AS count "
                f"FROM {qt} "
                f"GROUP BY {qc} "
                "ORDER BY count DESC, value "
                f"LIMIT {n}"
            )
        elif name == "unique":
            sql = (
                "WITH stats AS ("
                f"SELECT COUNT(DISTINCT {qc}) AS distinct_count FROM {qt}"
                "), samples AS ("
                f"SELECT DISTINCT {qc} AS sample_value FROM {qt} LIMIT 50"
                ") "
                "SELECT stats.distinct_count, samples.sample_value "
                "FROM stats LEFT JOIN samples ON TRUE"
            )
        else:
            bins = _parse_positive_int(args[1] if len(args) > 1 else None, 10, min_value=2, max_value=100)
            sql = (
                "WITH ranked AS ("
                f"SELECT NTILE({bins}) OVER (ORDER BY {qc}) AS bucket "
                f"FROM {qt} WHERE {qc} IS NOT NULL"
                ") "
                "SELECT bucket, COUNT(*) AS frequency "
                "FROM ranked GROUP BY bucket ORDER BY bucket"
            )

        payload, truncated = _run_sql(con, sql, row_limit=row_limit, result_type="table")
        return _Result(
            name=name,
            output=f"/{name} executed for {table}.{column}.",
            result_type="table",
            result=payload,
            truncated=truncated,
        )

    if name in {"corr", "crosstab"}:
        if len(args) < 2:
            raise CommandExecutionError(f"/{name} requires two columns. Usage: /{name} <table>.<c1> <c2>")

        table, c1 = _resolve_table_column_ref(catalog, args[0], default_table=default_table)
        second = str(args[1] or "").strip()
        if "." in second:
            table2, c2 = _resolve_table_column_ref(catalog, second, default_table=default_table)
            if table2.lower() != table.lower():
                raise CommandExecutionError("Both columns must belong to the same table.")
        else:
            c2 = _resolve_column(catalog, table, second)

        qt = _quote_ident(table)
        qc1 = _quote_ident(c1)
        qc2 = _quote_ident(c2)

        if name == "corr":
            sql = f"SELECT CORR({qc1}, {qc2}) AS correlation FROM {qt}"
            payload, truncated = _run_sql(con, sql, row_limit=5, result_type="scalar")
            rows = payload.get("data") or []
            corr_value = rows[0].get("correlation") if rows else None
            payload["scalar"] = corr_value
            return _Result(
                name=name,
                output=f"/{name} for {table}.{c1} and {table}.{c2}: {corr_value}",
                result_type="scalar",
                result=payload,
                truncated=truncated,
            )

        sql = (
            f"SELECT {qc1} AS col_1, {qc2} AS col_2, COUNT(*) AS count "
            f"FROM {qt} "
            f"GROUP BY {qc1}, {qc2} "
            "ORDER BY count DESC "
            f"LIMIT {row_limit}"
        )
        payload, truncated = _run_sql(con, sql, row_limit=row_limit, result_type="table")
        return _Result(
            name=name,
            output=f"/{name} executed for {table}.{c1} and {table}.{c2}.",
            result_type="table",
            result=payload,
            truncated=truncated,
        )

    raise CommandExecutionError(f"Unsupported distribution command: {name}")


def _run_quality(
    name: str,
    args: list[str],
    *,
    con: duckdb.DuckDBPyConnection,
    catalog: _Catalog,
    default_table: str | None,
    row_limit: int,
) -> _Result:
    if name == "nulls":
        if not args:
            raise CommandExecutionError("/nulls requires a table or table.column argument.")

        target = str(args[0] or "").strip()
        if "." in target:
            table, column = _resolve_table_column_ref(catalog, target, default_table=default_table)
            qt = _quote_ident(table)
            qc = _quote_ident(column)
            sql = (
                f"SELECT COUNT(*) AS null_count, COUNT(*) FILTER (WHERE {qc} IS NOT NULL) AS non_null_count "
                f"FROM {qt} WHERE {qc} IS NULL OR {qc} IS NOT NULL"
            )
            payload, truncated = _run_sql(con, sql, row_limit=5, result_type="scalar")
            scalar_rows = payload.get("data") or []
            null_count = scalar_rows[0].get("null_count") if scalar_rows else 0
            payload["scalar"] = null_count
            return _Result(
                name=name,
                output=f"/{name} for {table}.{column}: {null_count}",
                result_type="scalar",
                result=payload,
                truncated=truncated,
            )

        table = _resolve_table(catalog, target, default_table)
        qt = _quote_ident(table)
        table_columns = list(catalog.columns.get(table, {}).values())
        rows: list[dict[str, Any]] = []
        for column in table_columns:
            qc = _quote_ident(column)
            sql = f"SELECT COUNT(*) AS null_count FROM {qt} WHERE {qc} IS NULL"
            value = con.execute(sql).fetchone()
            rows.append({"column_name": column, "null_count": int(value[0] if value else 0)})

        payload = {
            "columns": ["column_name", "null_count"],
            "data": rows[:row_limit],
            "row_count": len(rows[:row_limit]),
            "result_type": "table",
        }
        truncated = len(rows) > row_limit
        return _Result(
            name=name,
            output=f"/{name} executed for table '{table}'.",
            result_type="table",
            result=payload,
            truncated=truncated,
        )

    if name == "duplicates":
        if not args:
            raise CommandExecutionError("/duplicates requires a table argument.")

        table = _resolve_table(catalog, args[0], default_table)
        qt = _quote_ident(table)

        specified_cols = " ".join(args[1:]).strip()
        if specified_cols:
            raw_cols = [item.strip() for item in specified_cols.split(",") if item.strip()]
            if not raw_cols:
                raise CommandExecutionError("Could not parse duplicate grouping columns.")
            resolved_cols = [_resolve_column(catalog, table, item) for item in raw_cols]
        else:
            resolved_cols = list(catalog.columns.get(table, {}).values())

        if not resolved_cols:
            raise CommandExecutionError("No columns found to evaluate duplicates.")

        quoted_cols = ", ".join(_quote_ident(col) for col in resolved_cols)
        sql = (
            f"SELECT {quoted_cols}, COUNT(*) AS duplicate_count "
            f"FROM {qt} "
            f"GROUP BY {quoted_cols} "
            "HAVING COUNT(*) > 1 "
            "ORDER BY duplicate_count DESC "
            f"LIMIT {row_limit}"
        )
        payload, truncated = _run_sql(con, sql, row_limit=row_limit, result_type="table")
        return _Result(
            name=name,
            output=f"/{name} executed for table '{table}'.",
            result_type="table",
            result=payload,
            truncated=truncated,
        )

    if name == "outliers":
        if not args:
            raise CommandExecutionError("/outliers requires a column reference (<table>.<col>).")

        table, column = _resolve_table_column_ref(catalog, args[0], default_table=default_table)
        qt = _quote_ident(table)
        qc = _quote_ident(column)
        sql = (
            "WITH quantiles AS ("
            f"SELECT QUANTILE_CONT({qc}, 0.25) AS q1, QUANTILE_CONT({qc}, 0.75) AS q3 FROM {qt}"
            "), bounds AS ("
            "SELECT q1, q3, (q3 - q1) AS iqr, q1 - 1.5 * (q3 - q1) AS lower_bound, q3 + 1.5 * (q3 - q1) AS upper_bound "
            "FROM quantiles"
            ") "
            f"SELECT t.*, b.lower_bound, b.upper_bound FROM {qt} t CROSS JOIN bounds b "
            f"WHERE t.{qc} < b.lower_bound OR t.{qc} > b.upper_bound "
            f"LIMIT {row_limit}"
        )
        payload, truncated = _run_sql(con, sql, row_limit=row_limit, result_type="table")
        return _Result(
            name=name,
            output=f"/{name} executed for {table}.{column}.",
            result_type="table",
            result=payload,
            truncated=truncated,
        )

    raise CommandExecutionError(f"Unsupported quality command: {name}")


def execute_workspace_command(
    *,
    duckdb_path: str,
    name: str,
    args: list[str],
    default_table: str | None = None,
    row_limit: int = DEFAULT_ROW_LIMIT,
) -> dict[str, Any]:
    normalized_name = str(name or "").strip().lower()
    if not normalized_name:
        raise CommandExecutionError("Command name is required.")

    row_limit = max(1, min(int(row_limit or DEFAULT_ROW_LIMIT), MAX_ROW_LIMIT))

    if normalized_name != "help" and normalized_name not in {item.name for item in COMMAND_DEFINITIONS}:
        known = ", ".join(sorted(f"/{item.name}" for item in COMMAND_DEFINITIONS))
        raise CommandExecutionError(f"Unknown command '/{normalized_name}'. Available: {known}")

    if normalized_name == "help":
        result = _run_help(args)
        return {
            "name": result.name,
            "output": result.output,
            "result_type": result.result_type,
            "result": result.result,
            "truncated": result.truncated,
        }

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        catalog = _build_catalog(con)
        if not catalog.tables:
            raise CommandExecutionError("No tables found in workspace database.")

        if normalized_name in {"describe", "info", "shape", "dtypes", "head", "tail", "sample"}:
            result = _run_overview(
                normalized_name,
                args,
                con=con,
                catalog=catalog,
                default_table=default_table,
                row_limit=row_limit,
            )
        elif normalized_name in {"mean", "median", "mode", "std", "sum", "min", "max", "percentile"}:
            result = _run_single_column_aggregate(
                normalized_name,
                args,
                con=con,
                catalog=catalog,
                default_table=default_table,
                row_limit=row_limit,
            )
        elif normalized_name in {"value_counts", "unique", "histogram", "corr", "crosstab"}:
            result = _run_distribution(
                normalized_name,
                args,
                con=con,
                catalog=catalog,
                default_table=default_table,
                row_limit=row_limit,
            )
        elif normalized_name in {"nulls", "duplicates", "outliers"}:
            result = _run_quality(
                normalized_name,
                args,
                con=con,
                catalog=catalog,
                default_table=default_table,
                row_limit=row_limit,
            )
        else:
            raise CommandExecutionError(f"Unsupported command: /{normalized_name}")
    finally:
        con.close()

    return {
        "name": result.name,
        "output": result.output,
        "result_type": result.result_type,
        "result": result.result,
        "truncated": result.truncated,
    }
