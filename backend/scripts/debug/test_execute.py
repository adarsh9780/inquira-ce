import asyncio
import os
import sys

# Add backend to sys path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.code_executor import execute_code

async def test():
    code = """
import pandas as pd
import duckdb
print("Hello World!")
    """
    result = await execute_code(code)
    print("Execution Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
