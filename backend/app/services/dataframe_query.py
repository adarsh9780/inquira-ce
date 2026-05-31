"""Helpers for building safe dataframe page queries."""

from __future__ import annotations

from typing import Any


def _quoted(ident: str) -> str:
    return '"' + str(ident).replace('"', '""') + '"'


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_single_filter_clause(
    *,
    model: dict[str, Any],
    quoted_column: str,
) -> tuple[str, list[Any]]:
    if not isinstance(model, dict):
        return "", []

    operator = str(model.get("operator") or "").upper()
    nested_conditions: list[dict[str, Any]] = []
    if isinstance(model.get("conditions"), list):
        nested_conditions = [
            item for item in model["conditions"] if isinstance(item, dict)
        ]
    else:
        condition_one = model.get("condition1")
        condition_two = model.get("condition2")
        if isinstance(condition_one, dict):
            nested_conditions.append(condition_one)
        if isinstance(condition_two, dict):
            nested_conditions.append(condition_two)

    if nested_conditions:
        nested_sql_parts: list[str] = []
        nested_params: list[Any] = []
        joiner = " OR " if operator == "OR" else " AND "
        for nested_model in nested_conditions:
            clause, clause_params = _build_single_filter_clause(
                model=nested_model,
                quoted_column=quoted_column,
            )
            if not clause:
                continue
            nested_sql_parts.append(f"({clause})")
            nested_params.extend(clause_params)
        if not nested_sql_parts:
            return "", []
        return joiner.join(nested_sql_parts), nested_params

    filter_type = str(model.get("filterType") or "").lower()
    filter_mode = str(model.get("type") or "").strip()

    if filter_type == "set":
        raw_values = model.get("values")
        if not isinstance(raw_values, list):
            return "", []
        if not raw_values:
            return "1 = 0", []
        placeholders = ", ".join(["?"] * len(raw_values))
        return f"{quoted_column} IN ({placeholders})", list(raw_values)

    if filter_mode == "blank":
        return (
            f"({quoted_column} IS NULL OR CAST({quoted_column} AS VARCHAR) = '')",
            [],
        )
    if filter_mode == "notBlank":
        return (
            f"({quoted_column} IS NOT NULL AND CAST({quoted_column} AS VARCHAR) <> '')",
            [],
        )

    if filter_type == "text":
        haystack = f"LOWER(CAST({quoted_column} AS VARCHAR))"
        value = str(model.get("filter") or "").lower()
        if filter_mode == "contains":
            return f"{haystack} LIKE ?", [f"%{value}%"]
        if filter_mode == "notContains":
            return f"({quoted_column} IS NULL OR {haystack} NOT LIKE ?)", [
                f"%{value}%"
            ]
        if filter_mode == "equals":
            return f"{haystack} = ?", [value]
        if filter_mode == "notEqual":
            return f"({quoted_column} IS NULL OR {haystack} <> ?)", [value]
        if filter_mode == "startsWith":
            return f"{haystack} LIKE ?", [f"{value}%"]
        if filter_mode == "endsWith":
            return f"{haystack} LIKE ?", [f"%{value}"]
        return "", []

    if filter_type == "number":
        numeric_expr = f"TRY_CAST({quoted_column} AS DOUBLE)"
        number_value = _coerce_float(model.get("filter"))
        number_to_value = _coerce_float(model.get("filterTo"))
        if filter_mode == "equals" and number_value is not None:
            return f"{numeric_expr} = ?", [number_value]
        if filter_mode == "notEqual" and number_value is not None:
            return f"({numeric_expr} IS NULL OR {numeric_expr} <> ?)", [
                number_value
            ]
        if filter_mode == "greaterThan" and number_value is not None:
            return f"{numeric_expr} > ?", [number_value]
        if filter_mode == "greaterThanOrEqual" and number_value is not None:
            return f"{numeric_expr} >= ?", [number_value]
        if filter_mode == "lessThan" and number_value is not None:
            return f"{numeric_expr} < ?", [number_value]
        if filter_mode == "lessThanOrEqual" and number_value is not None:
            return f"{numeric_expr} <= ?", [number_value]
        if (
            filter_mode == "inRange"
            and number_value is not None
            and number_to_value is not None
        ):
            low, high = sorted([number_value, number_to_value])
            return f"{numeric_expr} BETWEEN ? AND ?", [low, high]
        return "", []

    if filter_type == "date":
        date_expr = f"TRY_CAST({quoted_column} AS TIMESTAMP)"
        date_value = model.get("dateFrom") or model.get("filter")
        date_to_value = model.get("dateTo") or model.get("filterTo")
        if filter_mode == "equals" and date_value:
            return f"{date_expr} = TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
        if filter_mode == "notEqual" and date_value:
            return (
                f"({date_expr} IS NULL OR {date_expr} <> TRY_CAST(? AS TIMESTAMP))",
                [str(date_value)],
            )
        if filter_mode == "greaterThan" and date_value:
            return f"{date_expr} > TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
        if filter_mode == "greaterThanOrEqual" and date_value:
            return f"{date_expr} >= TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
        if filter_mode == "lessThan" and date_value:
            return f"{date_expr} < TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
        if filter_mode == "lessThanOrEqual" and date_value:
            return f"{date_expr} <= TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
        if filter_mode == "inRange" and date_value and date_to_value:
            return (
                f"{date_expr} BETWEEN TRY_CAST(? AS TIMESTAMP) AND TRY_CAST(? AS TIMESTAMP)",
                [str(date_value), str(date_to_value)],
            )
        return "", []

    if filter_type == "boolean":
        bool_val = model.get("filter")
        if isinstance(bool_val, bool):
            return (
                f"TRY_CAST({quoted_column} AS BOOLEAN) IS {'TRUE' if bool_val else 'FALSE'}",
                [],
            )
        value_text = str(bool_val).strip().lower()
        if value_text in {"true", "false"}:
            return (
                f"TRY_CAST({quoted_column} AS BOOLEAN) IS {value_text.upper()}",
                [],
            )
        return "", []

    return "", []


def build_dataframe_where_clause(
    *,
    column_names: list[str],
    filter_model: dict[str, Any] | None = None,
    search_text: str | None = None,
) -> tuple[str, list[Any]]:
    quoted_columns = {str(name): _quoted(str(name)) for name in column_names}
    where_parts: list[str] = []
    where_params: list[Any] = []

    safe_filter_model = filter_model if isinstance(filter_model, dict) else {}
    for raw_col_id, raw_model in safe_filter_model.items():
        quoted_column = quoted_columns.get(str(raw_col_id))
        if not quoted_column or not isinstance(raw_model, dict):
            continue
        clause, params = _build_single_filter_clause(
            model=raw_model,
            quoted_column=quoted_column,
        )
        if not clause:
            continue
        where_parts.append(f"({clause})")
        where_params.extend(params)

    needle = str(search_text or "").strip().lower()
    if needle and quoted_columns:
        search_clauses = [
            f"LOWER(CAST({expr} AS VARCHAR)) LIKE ?"
            for expr in quoted_columns.values()
        ]
        where_parts.append(f"({' OR '.join(search_clauses)})")
        where_params.extend([f"%{needle}%"] * len(search_clauses))

    if not where_parts:
        return "", []
    return f"WHERE {' AND '.join(where_parts)}", where_params


def build_dataframe_order_clause(
    *,
    column_names: list[str],
    sort_model: list[dict[str, Any]] | None = None,
) -> str:
    quoted_columns = {str(name): _quoted(str(name)) for name in column_names}
    safe_sort_model = sort_model if isinstance(sort_model, list) else []
    order_parts: list[str] = []

    for entry in safe_sort_model:
        if not isinstance(entry, dict):
            continue
        quoted_column = quoted_columns.get(str(entry.get("colId") or ""))
        direction = str(entry.get("sort") or "").lower()
        if not quoted_column or direction not in {"asc", "desc"}:
            continue
        order_parts.append(f"{quoted_column} {direction.upper()}")

    if not order_parts:
        return ""
    return f"ORDER BY {', '.join(order_parts)}"
