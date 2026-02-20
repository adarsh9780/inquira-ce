
import asyncio
import os
import json
from pathlib import Path

import asyncio
import os
import json
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

# Monkey patch aiosqlite.Connection to add is_alive method
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

from src.app.agent.graph import build_graph, InputSchema

# Mock environment variables if needed
os.environ["GOOGLE_API_KEY"] = "fake_key"

async def test_persistence():
    print("Initializing Graph with AsyncSqliteSaver...")
    db_path = "test_persistence.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        
        # Actually, simpler: define a minimal graph with the SAME State class to test persistence behavior.
        from src.app.agent.graph import State, OutputSchema, MetaData
        from langgraph.graph import StateGraph, START, END
        
        def node_a(state: State):
            print("Node A running, setting plan and message")
            return {
                "plan": "Plan A",
                "messages": [AIMessage(content="Relevancy Check Passed")]
            }
            
        def node_b(state: State):
            print("Node B running, setting code")
            return {"code": "print('Hello')"}
            
        workflow = StateGraph(State, input_schema=InputSchema, output_schema=OutputSchema)
        workflow.add_node("node_a", node_a)
        workflow.add_node("node_b", node_b)
        workflow.add_edge(START, "node_a")
        workflow.add_edge("node_a", "node_b")
        workflow.add_edge("node_b", END)
        
        app = workflow.compile(checkpointer=checkpointer)
        
        thread_id = "test_user:test_file.csv"
        config = {"configurable": {"thread_id": thread_id}}
        
        input_state = InputSchema(
            messages=[HumanMessage(content="Calculate average age")],
            active_schema={},
            current_code="",
        )
        
        print("Invoking graph...")
        result = await app.ainvoke(input_state, config=config)
        print("Invocation Result Keys:", result.keys())
        print("Plan in result:", result.get("plan"))
        print("Code in result:", result.get("code"))
        
        # Now check state from checkpointer
        print("Fetching state from checkpointer...")
        state_snapshot = await app.aget_state(config)
        print("Snapshot Values Keys:", state_snapshot.values.keys())
        print("Plan in snapshot:", state_snapshot.values.get("plan"))
        print("Code in snapshot:", state_snapshot.values.get("code"))
        print("Messages in snapshot:", state_snapshot.values.get("messages"))
        
        if result.get("plan") == "Plan A" and state_snapshot.values.get("plan") == "Plan A":
            print("SUCCESS: 'plan' persisted.")
        else:
            print("FAILURE: 'plan' lost.")
            
        if result.get("code") == "print('Hello')" and state_snapshot.values.get("code") == "print('Hello')":
            print("SUCCESS: 'code' persisted.")
        else:
            print("FAILURE: 'code' lost.")
            
    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    try:
        # Import needs to handle the src path
        import sys
        sys.path.append(os.getcwd())
        asyncio.run(test_persistence())
    except ImportError as e:
        print(f"Import Error: {e}")
        # Fallback to run locally if needed
