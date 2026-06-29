
import asyncio
import argparse
import aiosqlite
import pickle
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Monkey patch aiosqlite.Connection
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

def parse_args():
    parser = argparse.ArgumentParser(description="Inspect a local LangGraph checkpoint database.")
    parser.add_argument("--db-path", default=None, help="Path to chat_history.db. Defaults to ~/.inquira/chat_history.db.")
    parser.add_argument("--thread-id", default="", help="Optional checkpoint thread id to inspect.")
    return parser.parse_args()


async def inspect_db():
    args = parse_args()
    # Path found in main.py logs or standard location
    # User's home / .inquira / chat_history.db
    import pathlib
    db_path = pathlib.Path(args.db_path).expanduser() if args.db_path else pathlib.Path.home() / ".inquira" / "chat_history.db"
    
    print(f"Inspecting DB at: {db_path}")
    
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        # We need to list threads to find the right one
        # AsyncSqliteSaver doesn't expose list easily, but we can query the raw table
        
        async with aiosqlite.connect(db_path) as db:
            print("\n--- Checkpoints Found ---")
            # Table name is typically 'checkpoints'
            try:
                async with db.execute("SELECT thread_id, checkpoint_id, checkpoint FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 5") as cursor:
                    rows = await cursor.fetchall()
                    for thread_id, checkpoint_id, checkpoint_blob in rows:
                        print(f"Thread: {thread_id} | ID: {checkpoint_id}")
                        # Checkpoint blob is internal format, let's use checkpointer to read it if possible
                        # Or just read state using checkpointer.aget
            except Exception as e:
                print(f"Error querying table: {e}")
                
        thread_id = str(args.thread_id or "").strip()
        if not thread_id:
            print("\nNo --thread-id provided; skipping targeted checkpoint read.")
            return
        print(f"\nTargeting Thread ID: {thread_id}")
        
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)
        
        if checkpoint:
            print("\n--- Latest Checkpoint ---")
            print("Checkpoint Values:")
            # 'channel_values' usually holds the state
            channel_values = checkpoint.get("channel_values", {})
            for k, v in channel_values.items():
                if k == "plan":
                    print(f"  plan: {repr(v)}")
                elif k == "code":
                    print(f"  code: {repr(v)}")
                elif k == "messages":
                    print(f"  messages: (List of {len(v)} items)")
                else:
                    print(f"  {k}: ...")
            
            if "plan" not in channel_values:
                print("!! 'plan' key is MISSING from channel_values !!")
        else:
            print("No checkpoint found for this thread.")

if __name__ == "__main__":
    asyncio.run(inspect_db())
