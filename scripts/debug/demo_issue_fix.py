
import asyncio
from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import AIMessage, HumanMessage, AnyMessage

# --- 1. THE CURRENT SITUATION (The Issue) ---
# In the current implementation, 'code_generator' updates the state ('plan', 'code')
# but DOES NOT add a message to the 'messages' list.

class CurrentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    plan: str | None = None
    code: str | None = None

def current_relevancy_node(state: CurrentState):
    # This node adds a message
    return {"messages": [AIMessage(content="RELEVANCY CHECK PASSED")]}

def current_code_generator_node(state: CurrentState):
    # This node updates state but NO messages
    return {"plan": "Here is the plan...", "code": "print('hello')"}

async def demo_current_issue():
    workflow = StateGraph(CurrentState)
    workflow.add_node("relevancy", current_relevancy_node)
    workflow.add_node("codegen", current_code_generator_node)
    workflow.add_edge(START, "relevancy")
    workflow.add_edge("relevancy", "codegen")
    workflow.add_edge("codegen", END)
    
    app = workflow.compile()
    
    result = await app.ainvoke({"messages": [HumanMessage(content="Hello")]})
    
    print("\n--- CURRENT BEHAVIOR ---")
    print(f"Final Messages Count: {len(result['messages'])}")
    print("Messages:")
    for m in result['messages']:
        print(f" - [{m.type}]: {m.content}")
    print(f"Plan in State: {result['plan']}")
    print(f"Code in State: {result['code']}")
    print("ISSUE: The 'messages' list MISSES the final explanation/plan.")
    print("       'GET /history' only sees the messages list.")
    print("       It tries to hack the last message (Relevancy) to show the plan, which is fragile.")

# --- 2. THE PROPOSED FIX ---
# We modify 'code_generator' to Explicitly return an AIMessage.

def fixed_code_generator_node(state: CurrentState):
    plan_text = "Here is the plan..."
    return {
        "plan": plan_text, 
        "code": "print('hello')",
        # FIX: Add the explanation as a message!
        "messages": [AIMessage(content=plan_text)] 
    }

async def demo_proposed_fix():
    workflow = StateGraph(CurrentState)
    workflow.add_node("relevancy", current_relevancy_node)
    workflow.add_node("codegen", fixed_code_generator_node)
    workflow.add_edge(START, "relevancy")
    workflow.add_edge("relevancy", "codegen")
    workflow.add_edge("codegen", END)
    
    app = workflow.compile()
    
    result = await app.ainvoke({"messages": [HumanMessage(content="Hello")]})
    
    print("\n--- PROPOSED FIX ---")
    print(f"Final Messages Count: {len(result['messages'])}")
    print("Messages:")
    for m in result['messages']:
        print(f" - [{m.type}]: {m.content}")
        
    print("BENEFIT: Now the 'Explanation/Plan' is a real message.")
    print("         'GET /history' will naturally retrieve it without hacking.")

if __name__ == "__main__":
    asyncio.run(demo_current_issue())
    asyncio.run(demo_proposed_fix())
