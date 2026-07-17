# AfyaPlus RAG Agent System Architecture

## Purpose

The AfyaPlus RAG Agent System answers documented medical-insurance and
clinical-routing questions through a privacy boundary, a tool-using LangChain
agent, and a Qdrant-persisted LlamaIndex knowledge base. It also performs a
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
| Knowledge pipeline | LlamaIndex | Load, sentence-chunk, and represent manuals and results |
| Embedding and storage | Qdrant Cloud Inference | Embed, persist, and search knowledge chunks |
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
Deployment configuration and collection operations are documented in
[deployment.md](deployment.md).

## Grounded Knowledge Pipeline

The knowledge source is the repository's `knowledge/` directory. Ingestion
uses `SimpleDirectoryReader` and LlamaIndex `SentenceSplitter` with 512-token
chunks and 64-token overlap. This avoids local embedding compute; Qdrant Cloud
Inference embeds each chunk during upload.

Vectors live in the `QDRANT_COLLECTION_NAME` collection. The application sends
Qdrant `Document` inference objects using the configured managed model and a
384-dimensional cosine collection. A populated collection is reused without
re-ingesting the manuals. The collection is initialized lazily on the first
knowledge query, and payload metadata is limited to chunk text and source
filename. Source, chunking, model, or dimension changes require a deliberate
new collection or rebuild.

Retrieval uses `similarity_top_k=3`. Qdrant embeds the query and searches the
same collection. The adapter returns LlamaIndex source nodes without asking a
second LLM to synthesize an answer. A
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
not stored in LangGraph memory or Qdrant.

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
or Qdrant is ready. Production deployment should add readiness
checks, authentication, rate limiting, structured PII-safe audit events, and
monitoring. Endpoint details are in [api.md](api.md).

## Runtime Configuration

`app/config.py` implements a provider factory: `MODEL_PROVIDER` selects the
chat transport (`ollama_local` default, or `ollama_cloud`) without any code
changes, failing fast at startup on an invalid provider, a missing cloud
model/API key, or a malformed URL. Qdrant retrieval is configured independently
through `QDRANT_*`; switching chat providers never changes the embedding model
or vector store.

At request time, if a chat call to the configured provider fails (e.g. local
Ollama runs out of memory), `build_fallback_middleware()` retries once
against the *other* provider - but only when that other provider is fully
configured (local always has usable defaults; cloud requires
`OLLAMA_CLOUD_MODEL`/`OLLAMA_CLOUD_API_KEY`), and always logs a `WARNING`
naming both providers so a fallback is never silent or ambiguous about which
provider actually answered. If no fallback is available or it also fails,
the original exception propagates to the existing `503` handling below.

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_PROVIDER` | `ollama_local` | Chat transport: `ollama_local` or `ollama_cloud` |
| `OLLAMA_LOCAL_BASE_URL` | `http://localhost:11434/v1` | Local OpenAI-compatible Ollama endpoint |
| `OLLAMA_LOCAL_MODEL` | `llama3.2` | Local chat model |
| `OLLAMA_LOCAL_API_KEY` | `ollama` | Placeholder value the local endpoint ignores |
| `LOCAL_TIMEOUT_SECONDS` | `20.0` | Local chat request timeout |
| `OLLAMA_CLOUD_BASE_URL` | `https://ollama.com/v1` | Direct Ollama Cloud endpoint |
| `OLLAMA_CLOUD_MODEL` | *(required in cloud mode)* | Cloud chat model, e.g. `gpt-oss:120b` |
| `OLLAMA_CLOUD_API_KEY` | *(required in cloud mode)* | Real Ollama Cloud API key |
| `CLOUD_TIMEOUT_SECONDS` | `30.0` | Cloud chat request timeout |
| `AGENT_HISTORY_TOKEN_BUDGET` | `2048` | Maximum approximate history tokens per model call |
| `QDRANT_URL` | *(required)* | Qdrant Cloud HTTPS endpoint |
| `QDRANT_API_KEY` | *(required)* | Qdrant API key, stored only as a secret |
| `QDRANT_COLLECTION_NAME` | `afyaplus_knowledge_base` | Persistent application collection |
| `QDRANT_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Managed embedding model |
| `QDRANT_EMBEDDING_DIMENSIONS` | `384` | Dense vector dimensions |
| `QDRANT_TIMEOUT_SECONDS` | `30.0` | Cloud request timeout |

`python scripts/verify_provider.py` reports the active chat and Qdrant
model, collection, and host, and confirms both actually connect, without ever
printing secrets.

`.env` and legacy local `storage/` are excluded from Git (this
also covers `triage/.env`, Triage Engine's separate environment file —
see `triage/docs/triage_engine.md`). `.env.example` contains safe example
values only.

## Verification Strategy

The pytest suite covers PII mask/de-mask round trips, API-boundary model input,
sentence-aware ingestion, persistence reuse, retrieval citations and not-found
behavior, tool validation, per-thread memory isolation, token trimming, and API
validation. Stateful Qdrant boundary doubles keep unit tests local; a separate
synthetic-data smoke test verifies the real managed inference path.

## Design Trade-offs and Remaining Risks

- Qdrant Cloud removes local embedding compute but makes retrieval dependent on
  network availability, cloud credentials, region, and provider governance.
- Qdrant's free managed inference models are US-hosted; this synthetic-data
  prototype requires a separate region/contract review before real PHI.
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
