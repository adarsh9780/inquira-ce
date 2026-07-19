"""Safe inspection and paging for immutable dataframe artifacts."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import math
from pathlib import Path
from typing import Any
from uuid import UUID

import duckdb

from .errors import AdapterError


def _quoted(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def _path(value: str) -> Path:
    path = Path(str(value or "")).expanduser()
    if (
        not path.is_absolute()
        or path.suffix.lower() != ".parquet"
        or not path.is_file()
    ):
        raise AdapterError(
            "artifact_path_invalid",
            "Artifact path must identify an existing Parquet file.",
        )
    return path.resolve()


def _schema(connection: duckdb.DuckDBPyConnection, path: Path) -> list[dict[str, str]]:
    rows = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]
    ).fetchall()
    return [{"name": str(row[0]), "type": str(row[1])} for row in rows]


def inspect_parquet(value: str) -> dict[str, Any]:
    path = _path(value)
    connection = duckdb.connect()
    try:
        schema = _schema(connection, path)
        count = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)", [str(path)]
        ).fetchone()[0]
        return {"row_count": int(count), "schema": schema, "columns": schema}
    finally:
        connection.close()


def _float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _single_filter(model: dict[str, Any], column: str) -> tuple[str, list[Any]]:
    conditions = (
        model.get("conditions")
        if isinstance(model.get("conditions"), list)
        else [model.get("condition1"), model.get("condition2")]
    )
    nested = [item for item in conditions if isinstance(item, dict)]
    if nested:
        parts, params = [], []
        for item in nested:
            clause, values = _single_filter(item, column)
            if clause:
                parts.append(f"({clause})")
                params.extend(values)
        return (
            (
                " OR " if str(model.get("operator", "")).upper() == "OR" else " AND "
            ).join(parts),
            params,
        )
    kind, mode = str(model.get("filterType", "")).lower(), str(model.get("type", ""))
    if kind == "set":
        values = model.get("values")
        if not isinstance(values, list):
            return "", []
        if not values:
            return "1=0", []
        return f"{column} IN ({','.join('?' for _ in values)})", list(values)
    if mode == "blank":
        return f"({column} IS NULL OR CAST({column} AS VARCHAR)='')", []
    if mode == "notBlank":
        return f"({column} IS NOT NULL AND CAST({column} AS VARCHAR)<>'')", []
    if kind == "text":
        expr, value = (
            f"LOWER(CAST({column} AS VARCHAR))",
            str(model.get("filter") or "").lower(),
        )
        operations = {
            "contains": ("LIKE", f"%{value}%"),
            "notContains": ("NOT LIKE", f"%{value}%"),
            "equals": ("=", value),
            "notEqual": ("<>", value),
            "startsWith": ("LIKE", f"{value}%"),
            "endsWith": ("LIKE", f"%{value}"),
        }
        if mode in operations:
            operator, parameter = operations[mode]
            return f"{expr} {operator} ?", [parameter]
    if kind == "number":
        first, second, expr = (
            _float(model.get("filter")),
            _float(model.get("filterTo")),
            f"TRY_CAST({column} AS DOUBLE)",
        )
        operators = {
            "equals": "=",
            "notEqual": "<>",
            "greaterThan": ">",
            "greaterThanOrEqual": ">=",
            "lessThan": "<",
            "lessThanOrEqual": "<=",
        }
        if mode in operators and first is not None:
            return f"{expr} {operators[mode]} ?", [first]
        if mode == "inRange" and first is not None and second is not None:
            return f"{expr} BETWEEN ? AND ?", sorted([first, second])
    if kind == "date":
        first, second, expr = (
            model.get("dateFrom") or model.get("filter"),
            model.get("dateTo") or model.get("filterTo"),
            f"TRY_CAST({column} AS TIMESTAMP)",
        )
        operators = {
            "equals": "=",
            "notEqual": "<>",
            "greaterThan": ">",
            "greaterThanOrEqual": ">=",
            "lessThan": "<",
            "lessThanOrEqual": "<=",
        }
        if mode in operators and first:
            return f"{expr} {operators[mode]} TRY_CAST(? AS TIMESTAMP)", [str(first)]
        if mode == "inRange" and first and second:
            return (
                f"{expr} BETWEEN TRY_CAST(? AS TIMESTAMP) AND TRY_CAST(? AS TIMESTAMP)",
                [str(first), str(second)],
            )
    if kind == "boolean" and str(model.get("filter", "")).lower() in {"true", "false"}:
        return f"TRY_CAST({column} AS BOOLEAN) IS {str(model['filter']).upper()}", []
    return "", []


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def query_parquet(
    value: str,
    *,
    offset: int,
    limit: int,
    sort_model: list[dict[str, Any]] | None = None,
    filter_model: dict[str, Any] | None = None,
    search_text: str = "",
) -> dict[str, Any]:
    path = _path(value)
    if (
        not isinstance(offset, int)
        or offset < 0
        or not isinstance(limit, int)
        or limit < 1
        or limit > 1000
    ):
        raise AdapterError(
            "artifact_page_invalid",
            "Artifact offset must be non-negative and limit must be between 1 and 1000.",
        )
    connection = duckdb.connect()
    try:
        schema = _schema(connection, path)
        names = [column["name"] for column in schema]
        allowed = set(names)
        where, params = [], []
        for name, model in (
            filter_model if isinstance(filter_model, dict) else {}
        ).items():
            if name not in allowed or not isinstance(model, dict):
                continue
            clause, values = _single_filter(model, _quoted(name))
            if clause:
                where.append(f"({clause})")
                params.extend(values)
        needle = str(search_text or "").strip().lower()
        if needle and names:
            where.append(
                "("
                + " OR ".join(
                    f"LOWER(CAST({_quoted(name)} AS VARCHAR)) LIKE ?" for name in names
                )
                + ")"
            )
            params.extend([f"%{needle}%"] * len(names))
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        orders = []
        for item in sort_model if isinstance(sort_model, list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("colId", ""))
            direction = str(item.get("sort", "")).lower()
            if name in allowed and direction in {"asc", "desc"}:
                orders.append(f"{_quoted(name)} {direction.upper()}")
        order_sql = "ORDER BY " + ", ".join(orders) if orders else ""
        total = int(
            connection.execute(
                f"SELECT COUNT(*) FROM read_parquet(?) {where_sql}",
                [str(path), *params],
            ).fetchone()[0]
        )
        cursor = connection.execute(
            f"SELECT * FROM read_parquet(?) {where_sql} {order_sql} LIMIT ? OFFSET ?",
            [str(path), *params, limit, offset],
        )
        rows = [
            {name: _json_value(value) for name, value in zip(names, row)}
            for row in cursor.fetchall()
        ]
        return {
            "row_count": total,
            "schema": schema,
            "columns": names,
            "rows": rows,
            "offset": offset,
            "limit": limit,
        }
    finally:
        connection.close()
