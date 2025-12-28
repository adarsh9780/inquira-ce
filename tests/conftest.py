import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import tempfile
import os
from inquira.main import app
from inquira.config_models import AppConfig

@pytest_asyncio.fixture(scope="function")
async def client():
    # Use a temporary directory for tests
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override config paths to use tmpdir
        original_home = Path.home
        
        # Mock Path.home() to return tmpdir just for config resolution if needed,
        # but easier is just to patch the config object after app startup if possible,
        # or rely on dependency overrides.
        
        # Since AppConfig uses Path.home() in class methods, we might want to patch it.
        # However, for a simple integration test, we can just let it run if it doesn't break things.
        # Ideally we inject a test config.
        
        # NOTE: For this initial harness, we will trust the default config 
        # but beware it uses ~/.inquira. 
        # TODO: Mock AppConfig.get_user_config_path to use tmpdir
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
