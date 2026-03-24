# System Architecture

Inquira CE operates as a robust local-first desktop application. To guarantee data privacy and execution stability, the architecture is decoupled into four distinct layers:

## 1. Presentation Layer (Tauri + Vue)
The user interface is a Vue.js single-page application wrapped in a lightweight **Tauri** desktop shell (written in Rust). 
- **Purpose**: Provides native OS integrations (like file pickers) and renders the interactive workspace (streaming chat, AG Grid tables, Plotly charts).
- **Control**: The UI communicates strictly with the local backend API and never touches the database layers directly.

## 2. Orchestration Layer (FastAPI)
The central nervous system of Inquira is a local **FastAPI** server that starts automatically when the desktop app launches.
- **Purpose**: Manages REST API endpoints, handles server-sent events (SSE) for streaming chat tokens, and tracks the lifecycle of local Jupyter kernels.
- **Workspace Isolation**: Ensures each analysis session has its own dedicated directory on disk, completely isolating persistence layers across projects.

## 3. Data Engine (DuckDB)
Instead of relying on fragile in-memory dataframes that crash the app when sized incorrectly, Inquira translates raw files (CSV, Excel, JSON, Parquet) into robust local relational databases.
- **Purpose**: Uses **DuckDB** for lightning-fast analytics queries capable of scanning out-of-memory datasets natively.
- **Persistence**: File ingestions and schema generations are saved to disk instantly, allowing users to close the app and perfectly resume their session states later without re-importing data.

## 4. Agent Execution Layer (LangGraph API + Jupyter)
Inquira strictly separates the "Thinking" (the Planner Agent) from the "Doing" (the Code Runner) for maximum reliability.
- **Standalone Agent Service**: Built on **LangGraph** (`agent_v2`), the agent runs entirely decoupled from the core FastAPI backend as a standalone API service. This highly modular design means the Frontend communicates with the Backend, which then streams negotiated executions with the distinct Langgraph Agent process over the local network via `AgentClient`.
- **Jupyter Kernel**: Generated Python code is executed in an actively monitored, isolated Jupyter runtime managed by the Backend orchestrator—**not** locally inside the LangGraph agent process. This guarantees that if user-generated code crashes or memory-limits are hit, the orchestrating agent survives to report the failure.

---

## Deep Dives
Understand the specific execution sequences by exploring the diagrams below.
*(Prefer side-by-side studying? Open the standalone [Agent Workflow](./workflow_diagram.md) or [Data Pipeline](./data_pipeline_diagram.md) pages).*

---

### Inquira Workflow Diagram

This sequence shows the current end-to-end request flow from the desktop UI to the backend workspace kernel and the `agent_v2` LangGraph graph.

#### End-to-End Request Flow

```mermaid
sequenceDiagram
    participant User as User
    participant Frontend as Vue Frontend
    participant API as FastAPI V1 Chat API
    participant AgentService as LangGraph API Server
    participant Agent as LangGraph agent_v2
    participant Planner as Planner LLM
    participant ToolExec as CustomToolNode
    participant Kernel as Workspace Kernel

    User->>Frontend: Ask a data question
    Frontend->>API: POST /v1/chat
    API->>AgentService: AgentClient Proxy
    AgentService->>Agent: execute_graph(question, workspace, context)

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

#### Current LangGraph Node Flow

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

---

### Data Processing Workflow

This explicitly explains how raw CSV/Excel files are transformed into queryable data within Inquira.

#### Data Ingestion Pipeline

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant System as 💻 OS / Key
    participant API as 🌐 FastAPI
    participant DuckDB as 🦆 DuckDB Manager
    participant LLM as 🧠 Google Gemini
    participant Storage as 💾 File System

    Note over User, System: 1. File Selection
    User->>API: POST /system/open-file-dialog
    API->>System: Open Native File Picker
    System-->>API: Returns "/path/to/data.csv"
    API-->>User: Returns Path

    Note over User, API: 2. Set Active Data
    User->>API: PUT /settings/set/filepath
    API->>DuckDB: get_connection(user_id, file_path)
    
    rect rgb(230, 240, 255)
        Note left of DuckDB: 🏗️ Ingestion (Lazy Loading)
        DuckDB->>Storage: Check if .duckdb exists?
        
        alt New File or Modified
            DuckDB->>DuckDB: CREATE TABLE t_data AS FROM 'data.csv'
            DuckDB->>Storage: Save to ~/.inquira/databases/...
            DuckDB->>Storage: Upsert metadata (row count, mtime)
        else Exists & Current
            DuckDB->>DuckDB: Reuse existing table
        end
    end
    
    API-->>User: { success: true, row_count: 1000 }

    Note over User, API: 3. Schema Generation
    User->>API: POST /schemas/generate
    
    API->>DuckDB: DESCRIBE table;
    DuckDB-->>API: Columns [id, amount, date]
    API->>DuckDB: SELECT DISTINCT values LIMIT 10
    DuckDB-->>API: Samples ["A1", 100.50, "2023-01-01"]
    
    API->>LLM: "Generate description for these columns..."
    LLM-->>API: JSON { "amount": "Transaction value in USD" }
    
    API->>Storage: Save ~/.inquira/schemas/.../schema.json
    API-->>User: Returns Schema JSON
```

#### Storage Architecture

```mermaid
graph TD
    Source["📄 Original CSV/Excel"] -->|Read Only| Ingestion["⚙️ DatabaseManager"]
    Ingestion -->|Creates| DB["🦆 DuckDB File"]
    
    subgraph HomeDir ["User Home (~/.inquira)"]
        DB -->|Stored in| DBDir["📂 /databases/{user_id}/"]
        Schema["📜 schema.json"] -->|Stored in| SchemaDir["📂 /schemas/{user_id}/"]
    end
    
    Agent["🤖 Agent"] -->|Queries| DB
    Agent -->|Reads| Schema
```
