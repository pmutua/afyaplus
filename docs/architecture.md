# AfyaPlus RAG Agent System Architecture

## Purpose

The AfyaPlus RAG Agent System answers documented medical-insurance and
clinical-routing questions through a privacy boundary, a tool-using LangChain
agent, and a locally persisted LlamaIndex knowledge base. It also performs a
limited medication-volume calculation when a qualified clinician supplies
both required inputs.

The system supports routing and policy explanation. It does not diagnose,
prescribe, choose a dose, or replace qualified clinical or insurance review.

## System Context

| Area | Implementation | Responsibility |
|---|---|---|
| HTTP boundary | FastAPI in `app/main.py` | Validate requests and return typed responses |
| Privacy boundary | `app/safeguards/` | Mask PII before downstream processing and restore approved output |
| Orchestration | LangChain agent and LangGraph | Select tools and maintain per-thread state |
| Chat model | `ChatOpenAI` over Ollama | Interpret requests and compose responses |
| Knowledge pipeline | LlamaIndex | Load, semantically chunk, embed, and retrieve local manuals |
| Vector storage | ChromaDB | Persist vectors across application restarts |
| Functional tool | LangChain `@tool` | Calculate clinician-supplied dose/concentration volume safely |

## Request Flow

1. FastAPI validates `message` and `thread_id` with Pydantic.
2. The `protect_chat_request` dependency masks supported PII and creates a
   request-local `PrivacyContext`.
3. The route sends only `privacy.masked_message` to the agent.
4. LangGraph loads the checkpoint associated with the validated `thread_id`.
5. Memory middleware trims the model-visible history to recent complete turns.
6. The model either answers within its allowed scope or selects one of the two
   registered tools.
7. Knowledge questions retrieve local source nodes without a second synthesis
   model inside LlamaIndex.
8. The agent produces its final masked response.
9. The privacy context restores only placeholders present in that request's
   vault immediately before FastAPI serializes the response.

Detailed call ordering is shown in [sequence-diagram.md](sequence-diagram.md).

## Grounded Knowledge Pipeline

The knowledge source is the repository's `knowledge/` directory. Ingestion
uses `SimpleDirectoryReader` and `SemanticSplitterNodeParser`, configured with
a buffer size of 1 and a 95th-percentile semantic breakpoint. Chunk boundaries
therefore depend on embedding similarity rather than fixed token counts.

Local execution uses the Ollama embedding model selected by
`OLLAMA_EMBEDDING_MODEL`, defaulting to `embeddinggemma`. Continuous
integration uses `DeterministicHashEmbedding`, a network-free signed hashing
embedding that preserves useful lexical overlap for reproducible tests.

Vectors are stored under `CHROMA_STORAGE_DIR` in the
`CHROMA_COLLECTION_NAME` collection. Chroma's own embedding function is
disabled; LlamaIndex supplies every vector. If the collection already has
nodes, `build_index()` reloads it instead of re-ingesting the manuals.

Retrieval uses `similarity_top_k=3` and `response_mode="no_text"`. LlamaIndex
returns source nodes but does not ask an LLM to synthesize an answer. A second
deterministic relevance check retains only nodes that share substantive,
normalized terms with the question. Each retained excerpt receives an inline
filename citation. If none remain, retrieval returns exactly:

```text
Information not found.
```

This validation prevents a nearest vector from being treated as evidence when
the indexed manuals do not actually address the question.

## Agent and Tool Design

`app/agent/agent.py` builds one LangChain agent graph with exactly two tools:

- `search_afyaplus_knowledge` for documented insurance and routing facts.
- `calculate_medication_volume` for `dose_mg / concentration_mg_per_ml` when
  both values were supplied by a qualified clinician.

Both tools have narrow names, typed parameters, explicit docstrings, and
defensive exception handling. Knowledge failures return a temporary
unavailability message. The calculator rejects non-finite, zero, and negative
values and never selects or validates a clinical dose.

The system prompt treats user and retrieved text as untrusted data, requires
citations for policy claims, preserves PII placeholders, prohibits diagnosis
and prescribing, and directs uncertain or high-risk decisions to human review.

## Conversation Memory and Token Management

LangGraph's `InMemorySaver` stores conversation state by `thread_id`. IDs are
restricted to 1-128 letters, digits, underscores, or hyphens so callers cannot
accidentally use free-form PII as a session key. Separate IDs produce isolated
histories.

Before every model call, middleware uses LangChain `trim_messages` with an
approximate token counter and a default history budget of 2,048 tokens. It
keeps recent complete turns, starts on a human message, and ends on a human or
tool message. The full checkpoint remains available in process; only the slice
sent to the model is bounded. The remaining portion of llama3.2's 4,096-token
context is reserved for the system prompt, tool schemas, retrieved evidence,
and output.

`InMemorySaver` is intentionally process-local. Restarting the application
clears conversation memory, and multiple workers do not share it. A durable
checkpointer is required before horizontal production scaling.

## Privacy and Trust Boundaries

The raw message is accepted only by the FastAPI dependency. Downstream route,
agent, memory, and model inputs use placeholder-bearing text. The vault is
request-local and excluded from the privacy context's representation. It is
not stored in LangGraph memory or ChromaDB.

De-masking is deliberately last: only the final response is restored, using
only mappings created for the current request. Unknown or invented placeholder
tokens are not expanded. See [privacy.md](privacy.md) for supported patterns,
guarantees, and limitations.

## API and Failure Behavior

The service exposes `GET /health` and `POST /chat`. Invalid request schemas
return FastAPI's HTTP 422 response. Agent, model, and tool-loop exceptions are
translated to HTTP 503 with a generic message so internal details are not
returned to the caller.

The health endpoint is a process liveness check; it does not prove that Ollama
or the knowledge index is ready. Production deployment should add readiness
checks, authentication, rate limiting, structured PII-safe audit events, and
monitoring. Endpoint details are in [api.md](api.md).

## Runtime Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Chat model |
| `OLLAMA_API_KEY` | `ollama` | Required client value for local compatibility |
| `LOCAL_TIMEOUT_SECONDS` | `20.0` | Chat request timeout |
| `AGENT_HISTORY_TOKEN_BUDGET` | `2048` | Maximum approximate history tokens per model call |
| `OLLAMA_EMBEDDING_MODEL` | `embeddinggemma` | Local embedding model |
| `CHROMA_STORAGE_DIR` | `storage/chroma` | Persistent vector directory |
| `CHROMA_COLLECTION_NAME` | `afyaplus_knowledge_base` | Persistent collection name |

`.env` and `storage/` are excluded from Git. `.env.example` contains safe
example values only.

## Verification Strategy

The pytest suite covers PII mask/de-mask round trips, API-boundary model input,
semantic ingestion, persistence reload, retrieval citations and not-found
behavior, tool validation, per-thread memory isolation, token trimming, and API
validation. Fake chat models and deterministic CI embeddings keep tests local
and repeatable without weakening retrieval-shaped assertions.

## Design Trade-offs and Remaining Risks

- Local Ollama and Chroma keep sensitive workloads under operator control, but
  availability and latency depend on the host machine.
- Approximate token counting is fast and model-independent but not identical to
  llama3.2 tokenization.
- Lexical source validation is deterministic and conservative but can reject a
  relevant synonym that shares no normalized keyword with the question.
- Regex masking covers specified identifiers, not every possible personal or
  clinical identifier.
- The current service has no authentication, authorization, rate limiting,
  durable memory, distributed locking, or production audit sink.
- Human review remains required for uncertainty, clinical risk, coverage
  decisions, and any action affecting patient care or benefits.
