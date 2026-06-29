
import asyncio
import argparse
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from src.app.agent.graph import build_graph

# Monkey patch aiosqlite.Connection
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

def parse_args():
    parser = argparse.ArgumentParser(description="Inspect LangGraph state history for a thread.")
    parser.add_argument("--db-path", default=None, help="Path to chat_history.db. Defaults to ~/.inquira/chat_history.db.")
    parser.add_argument("--thread-id", required=True, help="Checkpoint thread id to inspect.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum snapshots to print.")
    return parser.parse_args()


async def inspect_full_history():
    args = parse_args()
    import pathlib
    db_path = pathlib.Path(args.db_path).expanduser() if args.db_path else pathlib.Path.home() / ".inquira" / "chat_history.db"

    thread_id = str(args.thread_id).strip()
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
                
            if count >= max(1, int(args.limit)):
                print(f"... stopping after {max(1, int(args.limit))} snapshots ...")
                break

if __name__ == "__main__":
    asyncio.run(inspect_full_history())
