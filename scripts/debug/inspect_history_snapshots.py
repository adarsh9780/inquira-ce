
import asyncio
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from src.app.agent.graph import build_graph

# Monkey patch aiosqlite.Connection
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

async def inspect_full_history():
    import pathlib
    db_path = pathlib.Path.home() / ".inquira" / "chat_history.db"
    
    # Target thread from previous inspection
    thread_id = "12e2bcd0-ce81-4cec-8272-12bca7d0b7dc:/Users/adarshmaurya/Downloads/data/Spotify Youtube Dataset.csv"
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"Inspecting Full History for: {thread_id}")
    
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        agent = build_graph(checkpointer=checkpointer)
        
        print("\n--- State History ---")
        # aget_state_history is an async generator
        count = 0
        async for state in agent.aget_state_history(config):
            count += 1
            print(f"\nSnapshot #{count}")
            print(f"Config: {state.config}")
            # print(f"Created By: {state.created_by}") # Attribute might be missing in some versions
            # print(f"Parent Config: {state.parent_config}")
            
            values = state.values
            print("Values:")
            if "plan" in values:
                print(f"  PLAN: {values['plan']}")
            else:
                print("  PLAN: [MISSING]")
                
            if "code" in values:
                print(f"  CODE: {values['code']}")
                
            if "messages" in values:
                print(f"  MESSAGES: {len(values['messages'])} msgs")
                
            if count >= 10:
                print("... stopping after 10 snapshots ...")
                break

if __name__ == "__main__":
    asyncio.run(inspect_full_history())
