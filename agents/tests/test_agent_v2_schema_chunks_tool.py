from __future__ import annotations

from agent_v2.tools.schema_chunks import scan_schema_chunks


def test_scan_schema_chunks_returns_relevant_columns_from_aliases_and_descriptions() -> None:
    schema = {
        "tables": [
            {
                "table_name": "ball_by_ball",
                "context": "Ball-level IPL data",
                "columns": [
                    {"name": "striker", "dtype": "VARCHAR", "description": "Batsman name", "aliases": ["batter"]},
                    {"name": "batsman_runs", "dtype": "INTEGER", "description": "Runs scored", "aliases": ["runs"]},
                ],
            },
            {
                "table_name": "songs",
                "context": "Music data",
                "columns": [
                    {"name": "track_name", "dtype": "VARCHAR", "description": "Song title", "aliases": []},
                ],
            },
        ]
    }

    result = scan_schema_chunks(
        schema=schema,
        query_terms=["top batsman", "runs", "batter"],
        table_names=["ball_by_ball", "songs"],
        chunk_size=2,
        max_chunks=4,
    )
    assert int(result.get("relevant_table_count") or 0) >= 1
    columns = result.get("columns") if isinstance(result, dict) else []
    assert isinstance(columns, list)
    names = {str(item.get("name") or "").strip().lower() for item in columns if isinstance(item, dict)}
    assert "striker" in names
    assert "batsman_runs" in names
