import os

# some mobile hotspot like adarsh's iphone 14 plus sends ipv6, we need to force to use ipv4
os.environ["GRPC_DNS_RESOLVER"] = "native"

from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import add_messages, StateGraph, START, END
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
)
from langgraph.graph.state import CompiledStateGraph, Checkpointer
from langchain_core.runnables import RunnableConfig
from dotenv import load_dotenv

from typing import Annotated, Any, cast, Mapping
from collections.abc import Iterator

import json
from pathlib import Path
from .code_guard import guard_code


def get_prompt_path(filename: str) -> Path:
    """Get absolute path to a prompt file"""
    return Path(__file__).parent.parent / "core" / "prompts" / "yaml" / filename


def load_json(filepath: str | Path):
    with open(filepath, "r") as file:
        schema = json.load(file)

    return schema


load_dotenv()


class MetaData(BaseModel):
    is_safe: bool | None = Field(
        default=None,
        description="if the question asked is not malicious or it cannot corrupt data",
    )
    safety_reasoning: str | None = Field(default=None)
    is_relevant: bool | None = Field(
        default=None,
        description="if the question asked is relevant to the active schema",
    )
    require_code: bool | None = Field(default=None)
    relevancy_reasoning: str | None = Field(default=None)


def merge_metadata(
    prev: MetaData | None, new: MetaData | Mapping[str, Any] | None
) -> MetaData | None:
    try:
        if new is None and prev is None:
            return None

        # Helper to convert input to dict safely
        def to_dict(obj):
            if isinstance(obj, MetaData):
                return obj.model_dump()
            if isinstance(obj, dict):
                return obj
            return {}  # Fallback for bad types (strings, etc)

        prev_dict = to_dict(prev)
        new_dict = to_dict(new)

        # Merge
        merged = prev_dict.copy()
        merged.update(new_dict)

        return MetaData(**merged)
    except Exception as e:
        # Fallback to prevent state corruption/crash
        # We return a fresh MetaData to ensure the graph can continue
        return prev if isinstance(prev, MetaData) else MetaData()


class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    metadata: Annotated[MetaData, merge_metadata] = Field(default=MetaData())
    plan: str | None = Field(default=None)
    code: str | None = Field(default=None)
    active_schema: dict[str, Any] | None = Field(default=None)
    previous_code: str = Field(
        default="", description="previous code used as context for generation"
    )
    current_code: str = Field(
        default="", description="current code which can provide LLM more context"
    )
    table_name: str | None = Field(default=None)
    data_path: str | None = Field(default=None)
    code_guard_feedback: str = Field(default="")
    code_guard_retries: int = Field(default=0)
    guard_status: str = Field(default="ok")


class InputSchema(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    active_schema: dict[str, Any] | None = Field(default=None)
    previous_code: str = Field(
        default="", description="previous code used as context for generation"
    )
    current_code: str = Field(
        default="", description="current code which can provide LLM more context"
    )
    table_name: str | None = Field(default=None)
    data_path: str | None = Field(default=None)


class OutputSchema(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    metadata: MetaData | None = Field(default=None)
    plan: str | None = Field(default=None)
    code: str | None = Field(default=None)
    # We might want to pass these through
    table_name: str | None = Field(default=None)
    data_path: str | None = Field(default=None)


class InquiraAgent:
    def __init__(self) -> None:
        self.counter = 0

    def _get_model(self, config: RunnableConfig, model_name: str = "gemini-2.5-flash"):
        """Get model instance with API key from config"""
        api_key = config.get("configurable", {}).get("api_key")

        # If API key is provided, set it in env for Google GenAI to pick up
        # or pass it if the specific init_chat_model supports it.
        # google-genai usually looks at GOOGLE_API_KEY env var.
        if api_key:
            import os

            os.environ["GOOGLE_API_KEY"] = api_key

        return init_chat_model(f"google_genai:{model_name}")

    def check_relevancy(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class IsRelevant(BaseModel):
            is_relevant: bool | None = Field(
                default=None,
                description="if the question asked is relevant to the active schema",
            )
            relevancy_reasoning: str | None = Field(default=None)

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("is_relevant_prompt.yaml"), input_variables=["schema"]
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(IsRelevant)

        response = chain.invoke(
            {"messages": state.messages, "schema": state.active_schema}
        )
        response = cast(IsRelevant, response)

        return {
            "metadata": {
                "is_relevant": response.is_relevant,
                "relevancy_reasoning": response.relevancy_reasoning,
            },
        }

    def check_safety(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class IsSafe(BaseModel):
            is_safe: bool | None = Field(
                default=None,
                description="if the question asked is not malicious or it cannot corrupt data",
            )
            safety_reasoning: str | None = Field(default=None)

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("is_safe_prompt.yaml"), input_variables=[]
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(IsSafe)

        response = chain.invoke({"messages": state.messages})
        response = cast(IsSafe, response)

        return {
            "metadata": {
                "is_safe": response.is_safe,
                "safety_reasoning": response.safety_reasoning,
            },
        }

    def require_code(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class RequireCode(BaseModel):
            require_code: bool | None

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("require_code_prompt.yaml"), input_variables=["schema"]
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(RequireCode)

        response = chain.invoke(
            {"messages": state.messages, "schema": state.active_schema}
        )
        response = cast(RequireCode, response)

        return {
            "metadata": {
                "require_code": response.require_code,
            }
        }

    def create_plan(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class Plan(BaseModel):
            plan: str | None

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("create_plan_prompt.yaml"),
            input_variables=["schema", "current_code"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(Plan)

        response = chain.invoke(
            {
                "messages": state.messages,
                "schema": state.active_schema,
                "current_code": state.previous_code,
            }
        )
        response = cast(Plan, response)

        return {"plan": response.plan}

    def code_generator(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class Code(BaseModel):
            code: str | None

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("codegen_prompt.yaml"),
            input_variables=[
                "plan",
                "current_code",
                "table_name",
                "schema",
                "data_path",
            ],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        # Serialize schema to string for the prompt
        schema_str = (
            json.dumps(state.active_schema, indent=2) if state.active_schema else "{}"
        )

        # Create the HTTP download URL for the web assembly duckdb client
        download_url = (
            f"/api/datasets/{state.table_name}/download"
            if state.table_name
            else "data.csv"
        )

        # Upgrade model to ensure code generation capability
        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model.with_structured_output(Code)

        response = chain.invoke(
            {
                "messages": state.messages,
                "plan": state.plan,
                "current_code": state.previous_code,
                "table_name": state.table_name or "data_table",
                "schema": schema_str,
                "data_path": download_url,
            }
        )
        response = cast(Code, response)

        updates = {"code": response.code}
        if response.code and response.code.strip():
            updates["current_code"] = response.code

        return updates

    def retry_code_generator(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class Code(BaseModel):
            code: str | None

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("codegen_prompt.yaml"),
            input_variables=[
                "plan",
                "current_code",
                "table_name",
                "schema",
                "data_path",
            ],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        schema_str = (
            json.dumps(state.active_schema, indent=2) if state.active_schema else "{}"
        )
        download_url = (
            f"/api/datasets/{state.table_name}/download"
            if state.table_name
            else "data.csv"
        )

        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model.with_structured_output(Code)
        retry_feedback = state.code_guard_feedback or (
            "Ensure code is valid."
        )
        retry_messages = list(state.messages) + [
            HumanMessage(
                content=(
                    "Code validation failed. Regenerate code.\n"
                    f"Validator feedback: {retry_feedback}"
                )
            )
        ]
        response = chain.invoke(
            {
                "messages": retry_messages,
                "plan": state.plan,
                "current_code": state.code or state.previous_code,
                "table_name": state.table_name or "data_table",
                "schema": schema_str,
                "data_path": download_url,
            }
        )
        response = cast(Code, response)

        updates = {"code": response.code}
        if response.code and response.code.strip():
            updates["current_code"] = response.code
        return updates

    def noncode_generator(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("noncode_prompt.yaml"),
            input_variables=["schema", "current_code"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model

        response = chain.invoke(
            {
                "messages": state.messages,
                "schema": state.active_schema,
                "current_code": state.previous_code,
            }
        )

        return {"messages": [AIMessage(content=response.content)]}

    def code_guard(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        result = guard_code(state.code or "", table_name=state.table_name)
        if not result.blocked:
            return {
                "code": result.code,
                "current_code": result.code,
                "guard_status": "ok",
                "code_guard_feedback": "",
            }

        retries = int(state.code_guard_retries or 0)
        if retries < 1 and result.should_retry:
            return {
                "guard_status": "retry",
                "code_guard_retries": retries + 1,
                "code_guard_feedback": result.reason or "",
            }

        return {
            "code": result.code,
            "current_code": result.code,
            "guard_status": "ok",
            "code_guard_feedback": result.reason or "",
        }

    def general_purpose(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        system_prompt_template = """You are the AI assistant for **Inquira**, a data analysis platform.

## About Inquira
Inquira helps users analyze their uploaded data (CSV, Excel, Parquet, JSON) through natural language queries.
The platform uses DuckDB for efficient querying, Pandas for transformations, and Plotly for visualizations.

## Your Capabilities
- Answer questions about the user's uploaded data
- Generate Python code for data analysis and visualization
- Provide statistical insights, aggregations, and business intelligence
- Create charts and dashboards using Plotly

## Guidelines
- Be helpful, friendly, and concise
- If asked about your capabilities, explain what Inquira can do
- For questions unrelated to data analysis, politely redirect to data-focused tasks
- Keep responses brief (2-4 sentences) unless more detail is genuinely needed"""

        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model

        response = chain.invoke({"messages": state.messages})

        return {"messages": [AIMessage(content=response.content)]}

    def unsafe_rejector(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        reasoning = (
            state.metadata.safety_reasoning
            or "The request was flagged as potentially unsafe."
        )

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("unsafe_rejection_prompt.yaml"),
            input_variables=["safety_reasoning"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model

        response = chain.invoke(
            {
                "messages": state.messages,
                "safety_reasoning": reasoning,
            }
        )

        return {"messages": [AIMessage(content=response.content)]}

    def compile(self, checkpointer=None) -> CompiledStateGraph:
        builder = StateGraph(
            State, input_schema=InputSchema, output_schema=OutputSchema
        )

        builder.add_node("check_relevancy", self.check_relevancy)
        builder.add_node("check_safety", self.check_safety)
        builder.add_node("require_code", self.require_code)
        builder.add_node("create_plan", self.create_plan)
        builder.add_node("code_generator", self.code_generator)
        builder.add_node("retry_code_generator", self.retry_code_generator)
        builder.add_node("code_guard", self.code_guard)
        builder.add_node("noncode_generator", self.noncode_generator)
        builder.add_node("general_purpose", self.general_purpose)
        builder.add_node("unsafe_rejector", self.unsafe_rejector)

        builder.add_edge(START, "check_safety")

        def safety_router(state: State):
            if state.metadata.is_safe:
                return "safe"
            else:
                return "unsafe"

        builder.add_conditional_edges(
            "check_safety",
            safety_router,
            {"safe": "check_relevancy", "unsafe": "unsafe_rejector"},
        )

        def relevancy_router(state: State):
            if state.metadata.is_relevant:
                return "relevant"
            else:
                return "irrelevant"

        builder.add_conditional_edges(
            "check_relevancy",
            relevancy_router,
            {"relevant": "require_code", "irrelevant": "general_purpose"},
        )

        def code_router(state: State):
            if state.metadata.require_code:
                return "yes"
            else:
                return "no"

        builder.add_conditional_edges(
            "require_code",
            code_router,
            {"yes": "create_plan", "no": "noncode_generator"},
        )

        builder.add_edge("create_plan", "code_generator")
        builder.add_edge("code_generator", "code_guard")
        def code_guard_router(state: State):
            if state.guard_status == "retry":
                return "retry"
            return "ok"

        builder.add_conditional_edges(
            "code_guard",
            code_guard_router,
            {"retry": "retry_code_generator", "ok": END},
        )
        builder.add_edge("retry_code_generator", "code_guard")
        builder.add_edge("general_purpose", END)
        builder.add_edge("unsafe_rejector", END)

        # builder.add_edge(["check_relevancy", "check_safety"], "router")

        # builder.add_edge("check_relevancy", END)
        # builder.add_edge("check_safety", END)

        return builder.compile(checkpointer=checkpointer)


def build_graph(checkpointer: Checkpointer = None) -> CompiledStateGraph:
    graph = InquiraAgent()
    agent = graph.compile(checkpointer=checkpointer)
    return agent


def execute(
    agent: CompiledStateGraph,
    user_query: str,
    thread_id: str = "adarsh9780:deliveries_schema.json",
):
    cfg: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    _, _, schema_path = thread_id.partition(":")

    if schema_path:
        active_schema = load_json(schema_path)
        state = InputSchema(
            messages=[HumanMessage(content=user_query)],
            active_schema=active_schema,
            current_code="",
        )

        state = agent.invoke(state, config=cfg)

        return state
    else:
        raise ValueError(f"No active schema is provided. current thread: {thread_id}")


def stream_nodes(
    agent: CompiledStateGraph,
    user_query: str,
    thread_id="adarsh9780:deliveries_schema.json",
) -> Iterator:
    cfg: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    _, _, schema_path = thread_id.partition(":")
    init_state = InputSchema(
        messages=[HumanMessage(content=user_query)],
        active_schema=load_json(schema_path),
        current_code="",
    )
    for step in agent.stream(init_state, config=cfg):
        for node_name, payload in step.items():
            # print("STREAM:", node_name, "keys:", list(payload.keys()))
            # print(payload["messages"])
            yield node_name, payload


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [_stringify_content(part) for part in content]
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        if content.get("type") == "text":
            return content.get("text", "")
        return json.dumps(content)
    return str(content)


def convert_ai_messages_to_buffer_string(messages: list[AnyMessage]) -> str:
    msgs: list[str] = []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _stringify_content(msg.content)
            if text:
                msgs.append(text)
        else:
            break
    return "\n".join(reversed(msgs))


if __name__ == "__main__":
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langchain_core.runnables import RunnableConfig

    with SqliteSaver.from_conn_string("test.db") as memory:
        agent = build_graph(checkpointer=None)

    while True:
        user_query = input("You: ")
        if user_query in ("exit", "quit", "kill", "q", "qut", "qt", "ext"):
            break

        for node_name, payload in stream_nodes(agent, user_query):
            if "messages" in payload:
                text = convert_ai_messages_to_buffer_string(payload["messages"])
                print(f"{node_name}: {text}")
            if "plan" in payload:
                print(f"{node_name} plan:\n{payload['plan']}")
            if "code" in payload:
                print(f"{node_name} plan:\n{payload['code']}")
