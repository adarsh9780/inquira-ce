
import asyncio
import os
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from src.inquira.agent.graph import State, InputSchema, OutputSchema
from langgraph.graph import StateGraph, START, END

async def test_kwargs_persistence():
    print("Testing persistence of additional_kwargs...")
    
    checkpointer = MemorySaver()
    
    def node_with_code(state: State):
        code = "print('PERSISTED CODE')"
        return {
            "messages": [
                AIMessage(
                    content="Here is the plan.", 
                    additional_kwargs={"generated_code": code}
                )
            ]
        }
    
    workflow = StateGraph(State, input_schema=InputSchema, output_schema=OutputSchema)
    workflow.add_node("node_gen", node_with_code)
    workflow.add_edge(START, "node_gen")
    workflow.add_edge("node_gen", END)
    
    app = workflow.compile(checkpointer=checkpointer)
    
    thread_id = "test_kwarg_thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    await app.ainvoke({"messages": []}, config=config)
    
    print("Retrieving state...")
    state = await app.aget_state(config)
    
    msgs = state.values.get("messages", [])
    if not msgs:
        print("FAIL: No messages found.")
        return

    last_msg = msgs[-1]
    print(f"Last Message Content: {last_msg.content}")
    print(f"Last Message Kwargs: {last_msg.additional_kwargs}")
    
    if last_msg.additional_kwargs.get("generated_code") == "print('PERSISTED CODE')":
        print("SUCCESS: Code persisted in additional_kwargs.")
    else:
        print("FAIL: Code NOT found in additional_kwargs.")

if __name__ == "__main__":
    asyncio.run(test_kwargs_persistence())
