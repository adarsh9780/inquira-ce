import json

import pytest
from starlette.requests import Request

from app.main import global_exception_handler


@pytest.mark.asyncio
async def test_global_exception_handler_hides_internal_exception_text():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "scheme": "http",
    }
    request = Request(scope)
    response = await global_exception_handler(request, RuntimeError("secret internals"))

    assert response.status_code == 500
    payload = json.loads(response.body.decode("utf-8"))
    assert payload == {"detail": "Internal Server Error"}
