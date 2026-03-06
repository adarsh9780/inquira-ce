from app.v1.services.chat_service import ChatService
from app.services.output_capture import infer_capture_candidate_names


def test_build_run_wrapped_code_uses_real_newlines():
    wrapped = ChatService._build_run_wrapped_code(
        "x = 1",
        "run-1",
        [{"name": "result_df", "kind": "dataframe"}],
    )
    assert "set_active_run('run-1')\nx = 1\n" in wrapped
    assert "\"name\": \"result_df\"" in wrapped
    assert "export_dataframe" in wrapped
    assert "\\n" not in wrapped


def test_finalize_script_uses_real_newlines():
    script = ChatService._assemble_final_script(
        question="q",
        generated_code="x = 1",
        run_id="run-1",
    )
    assert "\\n" not in script
    assert "set_active_run('run-1')" not in script
    assert "finalize_run('run-1')" not in script
    assert "x = 1" in script


def test_normalize_output_contract_accepts_dataframe_aliases_and_filters_invalid_entries():
    normalized = ChatService._normalize_output_contract(
        [
            {"name": "result_df", "kind": "pandas"},
            {"name": "result_df", "kind": "dataframe"},
            {"name": "summary_fig", "kind": "plotly"},
            {"name": "bad name", "kind": "dataframe"},
            {"name": "other", "kind": "unknown"},
            {"name": "arrow_table", "kind": "pyarrow"},
            {"name": "arrow_batch", "kind": "arrow"},
        ]
    )
    assert normalized == [
        {"name": "result_df", "kind": "dataframe"},
        {"name": "summary_fig", "kind": "figure"},
        {"name": "arrow_table", "kind": "dataframe"},
        {"name": "arrow_batch", "kind": "dataframe"},
    ]


def test_auto_capture_code_reports_export_errors_instead_of_swallowing_them():
    code = ChatService._build_auto_capture_result_code(
        [{"name": "result_value", "kind": "scalar"}]
    )
    assert "_inq_capture_errors = []" in code
    assert "_inq_record_error(" in code
    assert "[auto-capture] failed to export" in code
    assert "except Exception:\n        pass" not in code


def test_infer_capture_candidate_names_supports_arbitrary_variable_names():
    names = infer_capture_candidate_names(
        "sample_data = conn.sql('select * from t').df()\n"
        "top_players_df = sample_data.head(10)\n"
        "print(top_players_df)\n"
    )
    assert names == ["sample_data", "top_players_df"]


def test_build_run_wrapped_code_embeds_inferred_fallback_candidate_names():
    wrapped = ChatService._build_run_wrapped_code(
        "sample_data = conn.sql('select * from t').df()\nprint(sample_data)",
        "run-2",
        [],
    )
    assert "_inq_fallback_names" in wrapped
    assert '"sample_data"' in wrapped
    assert "_inq_aliases = ('result', 'final_df', 'df', 'fig', 'figure')" in wrapped
    assert "_inq_kind == 'scalar' and _inq_name in _inq_aliases" in wrapped
