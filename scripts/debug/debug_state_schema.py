
import asyncio
import os
import shutil
from typing import Annotated, Any, Mapping
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

# Monkey patch aiosqlite
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

# --- EXACT CODE COPIED FROM src/inquira/agent/graph.py FOR REPRODUCTION ---

class MetaData(BaseModel):
    is_safe: bool | None = Field(default=None)
    safety_reasoning: str | None = Field(default=None)
    is_relevant: bool | None = Field(default=None)
    require_code: bool | None = Field(default=None)
    relevancy_reasoning: str | None = Field(default=None)

def merge_metadata(
    prev: MetaData | None, new: MetaData | Mapping[str, Any] | None
) -> MetaData | None:
    if new is None and prev is None:
        return None
    if prev is None:
        return new if isinstance(new, MetaData) else MetaData(**(new or {}))

    new_dict = new.model_dump() if isinstance(new, MetaData) else dict(new or {})
    merged = prev.model_dump() if isinstance(prev, MetaData) else dict(prev or {})
    merged.update(new_dict)
    return MetaData(**merged)

class State(BaseModel):
    # Simplified State for reproduction (removed unrelated fields like messages for clarity if possible, 
    # but let's keep it close to original to be sure)
    metadata: Annotated[MetaData, merge_metadata] = Field(default=MetaData())
    plan: str | None = Field(default=None)

# --- REPRODUCTION SCRIPT ---

async def reproduce():
    db_path = "reproduce_crash.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print(f"Using DB: {db_path}")

    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        workflow = StateGraph(State)
        
        def node_update_meta(state: State):
            print("Step 1: Updating Metadata")
            # Return dict, which merge_metadata should handle
            return {"metadata": {"is_safe": True, "safety_reasoning": "Safe"}}
            
        def node_update_plan(state: State):
            print("Step 2: Updating Plan")
            return {"plan": "MY PERSISTENT PLAN"}
            
        workflow.add_node("step_1", node_update_meta)
        workflow.add_node("step_2", node_update_plan)
        workflow.add_edge(START, "step_1")
        workflow.add_edge("step_1", "step_2")
        workflow.add_edge("step_2", END)
        
        app = workflow.compile(checkpointer=checkpointer)
        
        thread_id = "test_crash"
        config = {"configurable": {"thread_id": thread_id}}
        
        print("\n--- Running Graph ---")
        try:
            await app.ainvoke({"metadata": {}}, config=config)
            print("Graph run finished successfully.")
        except Exception as e:
            print(f"Graph Run Failed: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n--- Retrieving State ---")
        try:
            snapshot = await app.aget_state(config)
            print("Snapshot retrieved.")
            print("Values:", snapshot.values)
            
            if snapshot.values.get("plan") == "MY PERSISTENT PLAN":
                print("SUCCESS: Plan is present.")
            else:
                print("FAIL: Plan is MISSING or incorrect.")
                
        except Exception as e:
            print(f"State Retrieval Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce())
