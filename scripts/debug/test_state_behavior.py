
import asyncio
from langgraph.graph import StateGraph, START, END
from src.app.agent.graph import State, InputSchema, OutputSchema
from langchain_core.messages import HumanMessage

# We will use the EXACT State definition from src.app.agent.graph
# which we import above.

def node_a_plan(state: State):
    print("--- Node A: Setting Plan ---")
    return {"plan": "THE PLAN WAS SET HERE"}

def node_b_code(state: State):
    print("--- Node B: Setting Code (Not touching Plan) ---")
    return {"code": "print('THE CODE')"}

async def test_state_persistence():
    workflow = StateGraph(State, input_schema=InputSchema, output_schema=OutputSchema)
    
    workflow.add_node("node_a", node_a_plan)
    workflow.add_node("node_b", node_b_code)
    
    workflow.add_edge(START, "node_a")
    workflow.add_edge("node_a", "node_b")
    workflow.add_edge("node_b", END)
    
    # Compile WITHOUT checkpointer first to test in-memory state passing
    app = workflow.compile()
    
    print("\nRunning Graph...")
    final_state = await app.ainvoke(
        {"messages": [HumanMessage(content="Start")]}
    )
    
    print("\n--- Final State ---")
    print(f"Plan: {final_state.get('plan')}")
    print(f"Code: {final_state.get('code')}")
    
    if final_state.get("plan") == "THE PLAN WAS SET HERE":
        print("RESULT: Plan WAS preserved.")
    else:
        print("RESULT: Plan WAS LOST.")
        
    # Now lets try WITH checkpointer (MemorySaver) to see if serialization affects it
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    app_w_chk = workflow.compile(checkpointer=checkpointer)
    
    thread_id = "test_thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    print("\nRunning Graph WITH Checkpointer...")
    await app_w_chk.ainvoke(
        {"messages": [HumanMessage(content="Start")]},
        config=config
    )
    
    state_snapshot = await app_w_chk.aget_state(config)
    print("\n--- Final Checkpoint State ---")
    print(f"Plan: {state_snapshot.values.get('plan')}")
    
    if state_snapshot.values.get("plan") == "THE PLAN WAS SET HERE":
        print("RESULT: Plan WAS preserved in checkpoint.")
    else:
        print("RESULT: Plan WAS LOST in checkpoint.")

if __name__ == "__main__":
    asyncio.run(test_state_persistence())
