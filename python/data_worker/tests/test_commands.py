from __future__ import annotations

import asyncio
from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.commands import (
    CommandExecutionError,
    compile_command,
    list_command_definitions,
)
from inquira_data_worker.runtime import WorkerRuntime


COLUMNS = [
    {"table_name": "sales", "column_name": "region", "dtype": "VARCHAR"},
    {"table_name": "sales", "column_name": "amount", "dtype": "DOUBLE"},
    {"table_name": "sales", "column_name": "order date", "dtype": "DATE"},
]


@pytest.mark.parametrize(
    ("text", "expected_name", "expected_fragment"),
    [
        ("/describe sales", "describe", "SUMMARIZE"),
        ("/head sales 25", "head", "LIMIT 25"),
        ("/mean sales.amount", "mean", "AVG"),
        ("/percentile sales.amount 95", "percentile", "QUANTILE_CONT"),
        ("/value_counts sales.region 12", "value_counts", "GROUP BY"),
        ("/corr sales.amount amount", "corr", "CORR"),
        ("/nulls sales", "nulls", "null_count"),
        ("/duplicates sales region,amount", "duplicates", "duplicate_count"),
        ("/outliers sales.amount", "outliers", "lower_bound"),
    ],
)
def test_compile_command_preserves_every_command_category(
    text: str, expected_name: str, expected_fragment: str
) -> None:
    compiled = compile_command({"text": text, "columns": COLUMNS})
    assert compiled["name"] == expected_name
    assert expected_fragment in compiled["python_code"]
    assert "_cmd_result" in compiled["python_code"]


def test_compile_command_supports_default_table_quoted_columns_and_help() -> None:
    aggregate = compile_command(
        {"text": '/sum "order date"', "default_table": "sales", "columns": COLUMNS}
    )
    assert aggregate["name"] == "sum"
    assert "order date" in aggregate["python_code"]

    help_result = compile_command({"text": "/help mean", "columns": []})
    assert help_result["result_type"] == "table"
    assert help_result["result"]["data"][0]["command"] == "/mean"
    assert len(list_command_definitions()) == 24


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"text": "mean sales.amount", "columns": COLUMNS}, "start with"),
        ({"text": "/unknown", "columns": COLUMNS}, "Unknown command"),
        ({"text": "/head missing", "columns": COLUMNS}, "Unknown table"),
        ({"text": "/mean sales.missing", "columns": COLUMNS}, "Could not resolve"),
        ({"text": "/head sales 0", "columns": COLUMNS}, "between 1 and 2000"),
        ({"text": "/histogram sales.amount 101", "columns": COLUMNS}, "between 2 and 100"),
        ({"text": "/describe", "columns": []}, "No tables"),
    ],
)
def test_compile_command_rejects_invalid_or_unsafe_inputs(
    payload: dict, message: str
) -> None:
    with pytest.raises(CommandExecutionError, match=message):
        compile_command(payload)


def test_runtime_compiles_and_executes_command_in_workspace_kernel(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = tmp_path / "workspace.duckdb"
        connection = duckdb.connect(str(database))
        connection.execute("CREATE TABLE sales AS SELECT * FROM (VALUES ('east', 10), ('west', 30), ('east', 20)) t(region, amount)")
        connection.close()
        runtime = WorkerRuntime()
        try:
            compiled = await runtime.handle(
                {
                    "id": "compile",
                    "method": "command_compile",
                    "params": {
                        "text": "/mean sales.amount",
                        "columns": COLUMNS,
                        "row_limit": 500,
                    },
                },
                lambda _: None,
            )
            assert compiled["error"] is None
            executed = await runtime.handle(
                {
                    "id": "execute",
                    "method": "kernel_execute",
                    "params": {
                        "workspace_id": "workspace-1",
                        "database_path": str(database),
                        "code": compiled["result"]["python_code"],
                        "run_id": "command-run",
                        "artifact_dir": str(tmp_path / "artifacts"),
                        "timeout_seconds": 10,
                    },
                },
                lambda _: None,
            )
            assert executed["error"] is None
            assert executed["result"]["result"]["name"] == "mean"
            assert executed["result"]["result"]["result"]["scalar"] == 20
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())


def test_every_rust_slash_command_compiles_and_executes_against_duckdb() -> None:
    connection = duckdb.connect()
    connection.execute(
        """
        CREATE TABLE sales AS
        SELECT * FROM (VALUES
            ('east', 10.0, DATE '2026-01-01'),
            ('west', 30.0, DATE '2026-01-02'),
            ('east', 20.0, DATE '2026-01-03'),
            ('east', 10.0, DATE '2026-01-01'),
            (NULL, 500.0, NULL)
        ) t(region, amount, "order date")
        """
    )
    commands = [
        "/describe sales", "/info sales", "/shape sales", "/dtypes sales",
        "/head sales 2", "/tail sales 2", "/sample sales 2",
        "/mean sales.amount", "/median sales.amount", "/mode sales.amount",
        "/std sales.amount", "/sum sales.amount", "/min sales.amount",
        "/max sales.amount", "/percentile sales.amount 75",
        "/value_counts sales.region 5", "/unique sales.region",
        "/histogram sales.amount 4", "/corr sales.amount amount",
        "/crosstab sales.region amount", "/nulls sales", "/nulls sales.region",
        "/duplicates sales region,amount,order date", "/outliers sales.amount",
        "/help",
    ]
    try:
        for command in commands:
            compiled = compile_command({"text": command, "columns": COLUMNS})
            namespace = {"conn": connection}
            exec(compiled["python_code"], namespace)
            assert namespace["_cmd_result"]["name"] == command.split()[0][1:]
    finally:
        connection.close()
