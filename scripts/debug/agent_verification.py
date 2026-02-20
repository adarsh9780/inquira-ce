import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from app.agent.graph import build_graph, InputSchema

# Load env
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

async def test_agent():
    print("Building graph...")
    try:
        agent = build_graph(checkpointer=None)
        print("Graph built successfully.")
    except Exception as e:
        print(f"Failed to build graph: {e}")
        return

    print("Testing invocation...")
    active_schema = {"tables": [{"name": "test_table", "columns": ["id", "val"]}]}
    user_query = "Count the rows in test_table"
    
    current_code_context = """# cell 1: Load and explore data
import pandas as pd
import duckdb as db

# Load data into a table with the filename as table name
table_name = "test_table"

# If a connection object named 'conn' exists, use it as 'db' for .sql calls
try:
    conn  # type: ignore  # noqa
    db = conn
except Exception:
    pass

# cell 2: Quick sample
result = db.sql(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()
"""
    
    state = InputSchema(
        messages=[HumanMessage(content=user_query)],
        active_schema=active_schema,
        current_code=current_code_context,
        table_name="test_table",
        data_path="test_data.csv"
    )
    
    try:
        # We need to make sure API key is set
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("WARNING: GOOGLE_API_KEY not set in env.")
        
        # Pass API key in configurable
        config = {"configurable": {"api_key": api_key}}
        result = await agent.ainvoke(state, config=config)
        
        print("Invocation successful.")
        print("Result keys:", result.keys())
        if "messages" in result:
            print("Last message:", result["messages"][-1].content)
        
        if "code" in result:
            print("\n=== GENERATED CODE ===")
            print(result["code"])
            print("======================\n")
    except Exception as e:
        print(f"Invocation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent())
