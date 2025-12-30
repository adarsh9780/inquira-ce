
import asyncio
import os
import pickle
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Monkey patch aiosqlite
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

from src.inquira.agent.graph import State, MetaData
# We don't need local merge_metadata anymore as it is defined in the module

async def test_corruption():
    db_path = "reproduce_crash.db" # Use the one populated by previous script
    if not os.path.exists(db_path):
        print("Run debug_state_schema.py first!")
        return

    print(f"Corrupting DB: {db_path}")

    # We want to manually modify the checkpoint blob to have "bad" metadata
    # that matches the error: "Input should be a valid dictionary or instance of MetaData"
    # This implies the data stored might be of a wrong type, e.g. a string or list.
    
    thread_id = "test_crash"
    config = {"configurable": {"thread_id": thread_id}}
    
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        # First verify it works
        s = await checkpointer.aget(config)
        print(f"Pre-corruption Plan: {s['channel_values']['plan']}")
        
        # Now let's corrupt the metadata in the DB
        # We need to find the latest checkpoint and modify its blob
        # AsyncSqliteSaver stores state in 'checkpoints' table usually serialized with pickle or json
        # default is pickle-like
        
        # Actually LangGraph v2+ uses msgpack or json usually.
        # Let's try to just insert a "Bad" state using checkpointer internally if possible
        # Or just simulate the validation error by changing the State definition to be STRICTER
        
        # Alternative: We can try to reproduce the validation error by passing a STRING to metadata
        # in the node, and see if it saves but fails to load.
        
        pass

async def reproduce_bad_type():
    db_path = "reproduce_bad_type.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        from langgraph.graph import StateGraph, START, END
        
        # Define a node that returns BAD metadata (e.g. a string instead of dict/obj)
        def node_bad_meta(state: State):
            return {"metadata": "THIS IS NOT A DICT"} 
            
        def node_plan(state: State):
             return {"plan": "PLAN EXISTS"}
             
        workflow = StateGraph(State)
        workflow.add_node("bad_meta", node_bad_meta)
        workflow.add_node("plan", node_plan)
        workflow.add_edge(START, "bad_meta")
        workflow.add_edge("bad_meta", "plan")
        workflow.add_edge("plan", END)
        
        app = workflow.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "bad_type"}}
        
        print("\n--- Running Graph with Bad Metadata ---")
        try:
            # This might crash during execution if merge_metadata fails immediately
            await app.ainvoke({"metadata": {}}, config=config) 
        except Exception as e:
            print(f"Execution Error (Expected?): {e}")
            
        print("\n--- Retrieving State ---")
        try:
            state = await app.aget_state(config)
            print("State Retrieved.")
            print("Plan:", state.values.get("plan"))
        except Exception as e:
            print(f"Retrieval Error: {e}")
            if "ValidationError" in str(e):
                print("SUCCESS: Reproduced ValidationError!")

if __name__ == "__main__":
    asyncio.run(reproduce_bad_type())
