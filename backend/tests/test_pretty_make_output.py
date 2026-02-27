import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "maintenance" / "pretty_make.py"


def _load_pretty_make_module():
    spec = importlib.util.spec_from_file_location("pretty_make", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wrap_block_applies_clean_text_wrapping():
    module = _load_pretty_make_module()
    wrapped = module._wrap_block(
        "This is a long sentence for wrapping quality checks in terminal output formatting.",
        width=36,
    )

    assert "\n" in wrapped
    assert "wrapping quality checks" in wrapped


def test_format_output_block_truncates_and_marks_large_output():
    module = _load_pretty_make_module()
    raw = "\n".join(f"line-{idx}" for idx in range(120))
    formatted = module._format_output_block(raw, width=80, max_lines=20)

    assert "... output truncated to last 20 lines ..." in formatted
    assert "line-0" not in formatted
    assert "line-119" in formatted
