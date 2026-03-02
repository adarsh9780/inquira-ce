from app.v1.services.chat_service import ChatService


def test_build_run_wrapped_code_uses_real_newlines():
    wrapped = ChatService._build_run_wrapped_code("x = 1", "run-1")
    assert "set_active_run('run-1')\nx = 1\n" == wrapped
    assert "\\n" not in wrapped


def test_finalize_script_uses_real_newlines():
    script = ChatService._assemble_final_script(
        question="q",
        generated_code="x = 1",
        run_id="run-1",
    )
    assert "\\n" not in script
    assert "set_active_run('run-1')" in script
    assert "finalize_run('run-1')" in script
