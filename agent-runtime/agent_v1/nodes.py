from __future__ import annotations

import uuid

from .tools import reply


def build_result(question: str) -> dict:
    explanation = reply(question)
    return {
        "run_id": str(uuid.uuid4()),
        "route": "general_chat",
        "metadata": {"is_safe": True, "is_relevant": False, "tables_used": [], "joins_used": False, "join_keys": []},
        "final_code": "",
        "final_explanation": explanation,
        "result_explanation": explanation,
        "code_explanation": "",
        "output_contract": [],
        "messages": [],
    }
