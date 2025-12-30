
import asyncio
import aiosqlite
import pickle
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Monkey patch aiosqlite.Connection
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

async def inspect_db():
    # Path found in main.py logs or standard location
    # User's home / .inquira / chat_history.db
    import pathlib
    db_path = pathlib.Path.home() / ".inquira" / "chat_history.db"
    
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
                
        # Let's try to guess the thread_id based on logs or standard format
        # User ID: 12e2bcd0-ce81-4cec-8272-12bca7d0b7dc
        # Data Path: /Users/adarshmaurya/Downloads/data/Spotify Youtube Dataset.csv
        thread_id = "12e2bcd0-ce81-4cec-8272-12bca7d0b7dc:/Users/adarshmaurya/Downloads/data/Spotify Youtube Dataset.csv"
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
