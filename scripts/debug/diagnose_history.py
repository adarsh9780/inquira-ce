
import asyncio
import os
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

# Monkey patch aiosqlite.Connection
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return True
    aiosqlite.Connection.is_alive = is_alive

from src.inquira.agent.graph import State, InputSchema

async def simulate_get_chat_history_logic(state_values):
    """
    Exact logic from src/inquira/api/chat.py:get_chat_history
    """
    print("\n--- Simulating get_chat_history Logic ---")
    messages = state_values.get("messages", [])
    current_code = state_values.get("current_code", "")
    
    # Serialize messages
    history = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content
        if isinstance(content, list):
            content = "\\n".join([str(p) for p in content])
        
        history.append({
            "role": role,
            "content": str(content),
            "type": msg.type
        })
        
    print("Initial History (from messages):")
    for h in history:
        print(f" - {h['role']}: {h['content']}")

    # Reconstruction Logic
    if history and history[-1]["role"] == "assistant":
        print("Last message is assistant. Attempting reconstruction...")
        plan = state_values.get("plan")
        code = state_values.get("code") or state_values.get("current_code")
        metadata = state_values.get("metadata", {})
        
        # Handle metadata as dict or object
        if hasattr(metadata, "dict"):
             metadata = metadata.dict()
        elif hasattr(metadata, "model_dump"):
             metadata = metadata.model_dump()
        
        print(f"State Values - Plan: '{plan}'")
        print(f"State Values - Code: '{code}'")
        
        explanation = ""
        if plan:
            print("Plan present. Using Plan.")
            explanation = plan
        else:
            print("Code or Plan missing. attempting metadata fallback.")
            is_safe_reason = metadata.get("safety_reasoning", "")
            is_relevant_reason = metadata.get("relevancy_reasoning", "")
            
            parts = []
            if is_safe_reason:
                parts.append(f"Safety Analysis: {is_safe_reason}")
            if is_relevant_reason:
                parts.append(f"Relevancy Analysis: {is_relevant_reason}")
            
            if parts:
                explanation = "\n\n".join(parts)
        
        if explanation:
            print(f"Explanation constructed: '{explanation}'")
            history[-1]["content"] = explanation
        else:
            print("No explanation constructed.")

    return history

async def diagnose():
    db_path = "diagnose.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        # 1. Create a dummy state that mimics the "Broken" state 
        # (Safety+Relevancy messages present, Plan+Code in state)
        
        # We manually save this state to the checkpointer to strictly test RETRIEVAL
        thread_id = "user:test"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Simulate state after graph execution
        final_state = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Safety Check Passed"),
                AIMessage(content="Relevancy Check Passed")
            ],
            "plan": "THIS IS THE PLAN THAT SHOULD APPEAR",
            "code": None, # SIMULATE MISSING CODE
            "current_code": "",
            "metadata": {"is_safe": True, "is_relevant": True}
        }
        
        # We can't just 'put' state easily without a graph run in LangGraph usually,
        # but we can simulate the graph run or just run a mock graph.
        
        from src.inquira.agent.graph import State, OutputSchema
        from langgraph.graph import StateGraph, START, END
        
        def mock_node(state: State):
            return {
                "messages": [
                    AIMessage(content="Safety Check Passed"), 
                    AIMessage(content="Relevancy Check Passed")
                ],
                "plan": "THIS IS THE PLAN THAT SHOULD APPEAR",
                "code": "print('hello')",
                "current_code": "print('hello')"
            }
            
        workflow = StateGraph(State, input_schema=InputSchema, output_schema=OutputSchema)
        workflow.add_node("mock_node", mock_node)
        workflow.add_edge(START, "mock_node")
        workflow.add_edge("mock_node", END)
        app = workflow.compile(checkpointer=checkpointer)
        
        print("Running Mock Graph to populate State...")
        await app.ainvoke(
            {"messages": [HumanMessage(content="Hello")]}, 
            config=config
        )
        
        print("Fetching State...")
        state_snapshot = await app.aget_state(config)
        state_values = state_snapshot.values
        
        # Run diagnosis
        final_history = await simulate_get_chat_history_logic(state_values)
        
        print("\n--- Final Result ---")
        last_msg = final_history[-1]['content']
        print(f"Last Message Content: '{last_msg}'")
        
        if last_msg == "THIS IS THE PLAN THAT SHOULD APPEAR":
            print("DIAGNOSIS: Logic WORKS locally. The issue is likely subtly different state in production.")
        else:
            print("DIAGNOSIS: Logic FAILED locally.")

if __name__ == "__main__":
    asyncio.run(diagnose())
