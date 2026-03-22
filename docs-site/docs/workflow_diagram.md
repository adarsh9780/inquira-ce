# Inquira Workflow Diagram

This document shows the current end-to-end request flow from the desktop UI to the backend workspace kernel and the `agent_v2` LangGraph graph.

## End-to-End Request Flow

```mermaid
sequenceDiagram
    participant User as User
    participant Frontend as Vue Frontend
    participant API as FastAPI V1 Chat API
    participant Agent as LangGraph agent_v2
    participant Planner as Planner LLM
    participant ToolExec as CustomToolNode
    participant Kernel as Workspace Kernel

    User->>Frontend: Ask a data question
    Frontend->>API: POST /v1/chat
    API->>Agent: stream(question, workspace_id, schema, context)

    Agent->>Agent: prepare_input
    Agent->>Agent: route

    alt Analysis route
        Agent->>Agent: analysis_collect_context
        Agent->>Planner: analysis_enrich_context
        Planner-->>Agent: structured plan { tools, explanation }

        opt More context needed
            Agent->>ToolExec: analysis_enrich_context_tools
            ToolExec->>ToolExec: run search_schema / scan_schema_chunks / sample_data
            ToolExec-->>Agent: ToolMessage + tool result metadata
            Agent->>Planner: analysis_enrich_context
        end

        Agent->>Agent: analysis_finalize_context_enrichment
        Agent->>Agent: analysis_prepare_sample_tool

        opt Runtime sample needed
            Agent->>ToolExec: analysis_runtime_tools
            ToolExec->>Kernel: sample_data_runtime
            Kernel-->>ToolExec: sampled rows
            ToolExec-->>Agent: ToolMessage + tool result metadata
        end

        Agent->>Planner: analysis_generate_code
        Agent->>Agent: analysis_guard_code
        Agent->>ToolExec: analysis_runtime_tools
        ToolExec->>Kernel: execute_python_runtime
        Kernel-->>ToolExec: stdout / stderr / artifacts / execution summary
        ToolExec-->>Agent: ToolMessage + tool result metadata

        Agent->>ToolExec: analysis_runtime_tools
        ToolExec->>Kernel: validate_result_runtime
        Kernel-->>ToolExec: normalized execution summary
        ToolExec-->>Agent: ToolMessage + tool result metadata

        Agent->>Agent: analysis_retry_decider
        alt Valid result
            Agent->>Agent: analysis_finalize_success
        else Retry or fail
            Agent->>Agent: analysis_enrich_context or analysis_finalize_failure
        end
    else General chat / unsafe
        Agent->>Agent: chat or reject
    end

    Agent-->>API: streamed status, tool events, final answer
    API-->>Frontend: SSE response
    Frontend-->>User: tool activity + final response + artifacts
```

## Current LangGraph Node Flow

```mermaid
flowchart TD
    Start([Start]) --> Prepare[prepare_input]
    Prepare --> Route[route]

    Route -->|analysis| Collect[analysis_collect_context]
    Route -->|general_chat| Chat[chat]
    Route -->|unsafe| Reject[reject]

    Collect --> Enrich[analysis_enrich_context]
    Enrich -->|pending_tools| EnrichTools[analysis_enrich_context_tools\nCustomToolNode]
    EnrichTools --> Enrich
    Enrich -->|enough_context| FinalizeContext[analysis_finalize_context_enrichment]

    FinalizeContext --> PrepareSample[analysis_prepare_sample_tool]
    PrepareSample -->|needs sample| RuntimeToolsA[analysis_runtime_tools\nCustomToolNode]
    PrepareSample -->|sample already cached| Generate[analysis_generate_code]
    RuntimeToolsA --> CaptureSample[analysis_capture_sample_tool_result]
    CaptureSample --> Generate

    Generate -->|needs more context| Enrich
    Generate -->|code ready| Guard[analysis_guard_code]
    Generate -->|generation failed| Retry[analysis_retry_decider]

    Guard -->|execute| RequestExecute[analysis_request_execute_tool]
    Guard -->|reject code| Retry
    RequestExecute --> RuntimeToolsB[analysis_runtime_tools\nCustomToolNode]
    RuntimeToolsB -->|execute stage| CaptureExecute[analysis_capture_execute_tool_result]

    CaptureExecute --> RequestValidate[analysis_request_validate_result_tool]
    RequestValidate --> RuntimeToolsC[analysis_runtime_tools\nCustomToolNode]
    RuntimeToolsC -->|validate stage| Validate[analysis_validate_result]
    RuntimeToolsC -->|sample stage| CaptureSample
    RuntimeToolsC -->|tool failure| Retry

    Validate -->|good result| Success[analysis_finalize_success]
    Validate -->|retry/fail| Retry
    Retry -->|enrich more| Enrich
    Retry -->|regenerate code| Generate
    Retry -->|fail| Failure[analysis_finalize_failure]

    Success --> Finalize[finalize]
    Failure --> Finalize
    Chat --> Finalize
    Reject --> Finalize
    Finalize --> End([End])
```

## Notes

- The planner no longer relies on raw `model.bind_tools(...)` output for the main analysis loop. It emits structured tool plans with a short operational explanation.
- `CustomToolNode` is the canonical executor for graph-managed tools. It emits `ToolMessage` objects into graph state and also emits tool call/result events for the UI and tracing backends.
- Generated Python runs through the backend workspace kernel, not inside the agent process. That keeps package availability and artifact generation aligned with the active workspace.
- Code generation now instructs the model to use meaningful figure variable names such as `strike_rate_by_batter_fig` instead of generic names like `fig`.
