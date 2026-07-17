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

The collection is application-only and distinct from MCP/tooling collections.
Only chunk text and source filename metadata are uploaded.

## Grounded Chat Request

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI /chat
    participant Privacy as Privacy dependency
    participant Agent as LangChain/LangGraph agent
    participant Memory as InMemorySaver
    participant Model as Ollama llama3.2
    participant Tool as Knowledge tool
    participant RAG as LlamaIndex + Qdrant Cloud

    User->>API: POST message and thread_id
    API->>Privacy: Validate ChatRequest
    Privacy->>Privacy: Mask phone, email, and member ID
    Privacy-->>API: PrivacyContext with masked message
    API->>Agent: Invoke masked message and thread config
    Agent->>Memory: Load thread checkpoint
    Memory-->>Agent: Masked conversation history
    Agent->>Agent: Trim model-visible history
    Agent->>Model: System prompt, masked history, tool schemas
    Model-->>Agent: Call search_afyaplus_knowledge
    Agent->>Tool: Execute masked policy question
    Tool->>RAG: Query top 3 source nodes
    RAG->>RAG: Validate relevance and add citations
    RAG-->>Tool: Grounded excerpts or Information not found.
    Tool-->>Agent: Tool result
    Agent->>Model: Tool result with source citations
    Model-->>Agent: Final masked answer
    Agent->>Memory: Save masked turn
    Agent-->>API: Final masked message
    API->>Privacy: Restore current request placeholders
    Privacy-->>API: Approved de-masked output
    API-->>User: ChatResponse
```

The privacy vault never enters the agent, model, memory, knowledge tool, or
vector store. Only the final API response crosses back through the vault.

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
    participant API as FastAPI
    participant Agent as Agent graph
    participant Knowledge as Knowledge tool
    participant Backend as Ollama/Qdrant

    alt Invalid message or thread_id
        User->>API: Invalid POST /chat
        API-->>User: HTTP 422 validation response
    else Knowledge backend failure handled by tool
        Agent->>Knowledge: Search policy
        Knowledge->>Backend: Retrieve/embed
        Backend--xKnowledge: Unavailable
        Knowledge-->>Agent: Temporary unavailability text
    else Unhandled agent or model failure
        Agent--xAPI: Exception
        API-->>User: HTTP 503 generic response
    end
```

Handled knowledge failures remain inside the tool loop. Unhandled graph or
model errors become a generic 503 response without internal exception details.
