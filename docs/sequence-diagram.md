# Request Sequence Diagrams

## Knowledge Collection Initialization

```mermaid
sequenceDiagram
    autonumber
    participant Tool as Knowledge tool
    participant Llama as LlamaIndex
    participant Qdrant as Qdrant Cloud Inference

    Tool->>Qdrant: Open application collection
    alt Collection missing
        Qdrant->>Qdrant: Create 384-d cosine collection
    end
    Qdrant-->>Tool: Point count
    alt Collection empty
        Tool->>Llama: Load documents and sentence-aware chunks
        Llama-->>Tool: Text nodes with source filenames
        Tool->>Qdrant: Upload Document inference points
        Qdrant->>Qdrant: Embed and persist vectors
    else Collection populated
        Tool->>Tool: Reuse persisted knowledge
    end
```

The application collection is dedicated and not shared with unrelated
workloads or external tools. Only chunk text and source filename metadata are
uploaded.

## Grounded Chat Request

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Interface as Chainlit /ui or FastAPI /chat
    participant Service as Shared chat service
    participant Privacy as Privacy context
    participant Agent as LangChain/LangGraph agent
    participant Memory as InMemorySaver
    participant Model as Ollama llama3.2
    participant Tool as Knowledge tool
    participant RAG as LlamaIndex + Qdrant Cloud

    User->>Interface: UI message or POST message/thread_id
    Interface->>Service: Validated ChatRequest
    Service->>Privacy: Create request-local privacy context
    Privacy->>Privacy: Mask phone, email, and member ID
    Privacy-->>Service: PrivacyContext with masked message
    Service->>Agent: Invoke masked message and thread config
    Agent->>Memory: Load thread checkpoint
    Memory-->>Agent: Masked conversation history
    Agent->>Agent: Trim model-visible history
    Agent->>Model: System prompt, masked history, tool schemas
    Model-->>Agent: Call search_afyaplus_knowledge
    Agent->>Tool: Execute masked policy question
    Tool->>RAG: Query top 5 source nodes
    RAG->>RAG: Validate relevance and add citations
    RAG-->>Tool: Grounded excerpts or Information not found.
    Tool-->>Agent: Tool result
    Agent->>Model: Tool result with source citations
    Model-->>Agent: Final masked answer
    Agent->>Memory: Save masked turn
    Agent-->>Service: Final masked message
    Service->>Privacy: Restore current request placeholders
    Privacy-->>Service: Approved de-masked output
    Service-->>Interface: ChatResponse
    Interface-->>User: Browser message or JSON response
```

The privacy vault never enters the agent, model, memory, knowledge tool, or
vector store. Only the final interface response crosses back through the vault.

## Calculator Tool Request

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI /chat
    participant Privacy as Privacy dependency
    participant Agent as LangChain agent
    participant Model as Ollama llama3.2
    participant Calculator as Medication volume tool

    User->>API: Dose and concentration supplied by clinician
    API->>Privacy: Mask supported PII
    Privacy-->>API: Masked request context
    API->>Agent: Invoke masked message
    Agent->>Model: Allowed tools and safety prompt
    Model-->>Agent: Calculator call with two numeric inputs
    Agent->>Calculator: prescribed_dose_mg, concentration_mg_per_ml
    Calculator->>Calculator: Validate finite positive inputs
    Calculator-->>Agent: Volume in mL or calculation error
    Agent->>Model: Exact tool result
    Model-->>Agent: Final response
    Agent-->>API: Masked response
    API->>Privacy: Restore current request placeholders
    API-->>User: ChatResponse
```

The calculator performs arithmetic only. It does not choose a dose, validate a
prescription, diagnose a condition, or decide treatment safety.

## Failure Paths

```mermaid
sequenceDiagram
    actor User
    participant Interface as FastAPI or Chainlit
    participant Agent as Agent graph
    participant Knowledge as Knowledge tool
    participant Backend as Ollama/Qdrant

    alt Invalid message or thread_id
        User->>Interface: Invalid POST /chat
        Interface-->>User: HTTP 422 validation response
    else Knowledge backend failure handled by tool
        Agent->>Knowledge: Search policy
        Knowledge->>Backend: Retrieve/embed
        Backend--xKnowledge: Unavailable
        Knowledge-->>Agent: Temporary unavailability text
    else Unhandled agent or model failure
        Agent--xInterface: Exception
        Interface-->>User: HTTP 503 generic response
    else Unhandled UI agent or model failure
        Agent--xInterface: Exception
        Interface-->>User: Generic unavailable chat message
    end
```

Handled knowledge failures remain inside the tool loop. Unhandled graph or
model errors become a generic 503 API response or generic UI message without
internal exception details.
