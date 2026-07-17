# AfyaPlus Enterprise-Grade RAG-Powered Agent System

AfyaPlus is a privacy-aware medical-insurance verification and
clinical-routing assistant. It combines a FastAPI boundary, a tool-using
LangChain/LangGraph agent, a grounded LlamaIndex knowledge pipeline, local
Ollama models, persistent ChromaDB storage, and Kenyan PII masking.

The system explains documented policy and routing guidance. It does not
diagnose, prescribe, select medication doses, or replace qualified clinical or
insurance review.

## What Is Implemented

- FastAPI endpoints for health checks and stateful chat.
- Kenyan phone, email, and AfyaPlus member-ID masking before model calls.
- Request-local de-masking immediately before an approved response is returned.
- Semantic LlamaIndex chunking with Ollama embeddings.
- Persistent ChromaDB vectors that reload instead of re-ingesting on restart.
- Deterministic source validation, inline citations, and an exact
  `Information not found.` fallback.
- A LangChain agent with exactly two tools: grounded knowledge retrieval and a
  validated medication-volume calculator.
- Per-thread LangGraph memory with bounded model-visible history.
- Automated tests for privacy, retrieval, grounding, tools, memory, and API
  behavior.

## Architecture

```text
Raw request
  -> Pydantic validation
  -> PII masking and request-local vault
  -> LangChain/LangGraph agent and bounded thread memory
       -> LlamaIndex + ChromaDB knowledge tool
       -> validated medication-volume tool
  -> grounded masked response
  -> request-local de-masking
  -> FastAPI response
```

Detailed documentation:

- [Architecture](docs/architecture.md)
- [Sequence diagrams](docs/sequence-diagram.md)
- [Privacy safeguards](docs/privacy.md)
- [API reference](docs/api.md)

## Repository Layout

```text
app/
  agent/                 # Agent, prompt, tools, memory, token trimming
  models/                # Pydantic request and response schemas
  rag/                   # Chunking, embeddings, ingestion, retrieval, grounding
  safeguards/            # PII patterns, masking, de-masking, API dependency
  config.py              # Ollama local/cloud chat-model provider factory
  main.py                # FastAPI application
docs/                    # Primary product documentation
knowledge/               # Local insurance and clinical-routing manuals
tests/                   # Automated test suite
triage/                  # Foundational Week 1 triage engine
  env.example            # Triage's own configuration template
triage_cli.py             # Foundational triage CLI entrypoint
.env.example             # RAG Agent System configuration template
requirements.txt         # Python dependencies
```

Triage Engine and the RAG Agent System each read their own environment file
(`triage/.env` and the repo-root `.env`, respectively) — see "Environment
Configuration" below and [triage/docs/triage_engine.md](triage/docs/triage_engine.md).

## Prerequisites

- Python 3.11 or newer.
- `pip` and Python virtual-environment support.
- Ollama installed on the host operating system.
- Enough local memory to run `llama3.2` and `embeddinggemma`.

Install Ollama from its official platform page:

| Platform | Official installer |
|---|---|
| Windows | [Ollama for Windows](https://ollama.com/download/windows) |
| Linux | [Ollama for Linux](https://ollama.com/download/linux) |
| macOS | [Ollama for macOS](https://ollama.com/download/mac) |

After installation, open a new terminal and verify Ollama:

```text
ollama --version
ollama list
```

Desktop installers normally run Ollama in the background. If it is not
running, start it in a separate terminal with `ollama serve`. If that command
reports that port `11434` is already in use, an Ollama service is already
running; do not start a second instance.

## Quick Start

Run all commands from the repository root—the directory containing
`requirements.txt` and `app/`.

### Windows PowerShell

Create the environment and install dependencies:

```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Pull the local models and start the API:

```powershell
ollama pull llama3.2
ollama pull embeddinggemma
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Without activating the virtual environment, use:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Linux

Create the environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Pull the local models and start the API:

```bash
ollama pull llama3.2
ollama pull embeddinggemma
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Without activating the virtual environment, use:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

If `python3 -m venv` is unavailable, install the virtual-environment package
provided by your Linux distribution, then repeat the command.

### macOS

Create the environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Pull the local models and start the API:

```bash
ollama pull llama3.2
ollama pull embeddinggemma
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Without activating the virtual environment, use:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Environment Configuration

The RAG API works with the safe local defaults in `.env.example`. Set
`MODEL_PROVIDER` to switch the chat transport between local Ollama and
Ollama Cloud without any code changes; an invalid provider, a missing cloud
model/API key, or a malformed URL fails fast at startup (`app/config.py`).

At request time, if the configured provider fails (e.g. local Ollama runs
out of memory), the agent retries once against the other provider - but
only when it's fully configured, and always with a logged `WARNING` naming
both providers, so a fallback is never silent or ambiguous about which
provider actually answered.

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_PROVIDER` | `ollama_local` | Chat transport: `ollama_local` or `ollama_cloud` |
| `OLLAMA_LOCAL_BASE_URL` | `http://localhost:11434/v1` | Local OpenAI-compatible Ollama endpoint |
| `OLLAMA_LOCAL_MODEL` | `llama3.2` | Local chat model |
| `OLLAMA_LOCAL_API_KEY` | `ollama` | Placeholder value the local endpoint ignores |
| `LOCAL_TIMEOUT_SECONDS` | `20.0` | Local chat-model request timeout |
| `OLLAMA_CLOUD_BASE_URL` | `https://ollama.com/v1` | Direct Ollama Cloud endpoint |
| `OLLAMA_CLOUD_MODEL` | *(required in cloud mode)* | Cloud chat model, e.g. `gpt-oss:120b` |
| `OLLAMA_CLOUD_API_KEY` | *(required in cloud mode)* | Real Ollama Cloud API key — never `ollama` |
| `CLOUD_TIMEOUT_SECONDS` | `30.0` | Cloud chat-model request timeout |
| `AGENT_HISTORY_TOKEN_BUDGET` | `2048` | Approximate history tokens sent per model call |
| `EMBEDDING_PROVIDER` | `ollama_local` | Embedding provider — stays local even if chat is cloud |
| `OLLAMA_EMBEDDING_BASE_URL` | `http://localhost:11434` | Embedding host, independent of the chat host |
| `OLLAMA_EMBEDDING_MODEL` | `embeddinggemma` | Semantic chunking and retrieval embedding model |
| `CHROMA_STORAGE_DIR` | `storage/chroma` | Persistent vector-store directory |
| `CHROMA_COLLECTION_NAME` | `afyaplus_knowledge_base` | Chroma collection name |

`CI` is an ambient automation flag, not a local `.env` setting. When present,
it selects a deterministic test embedding instead of contacting Ollama.

Run `python scripts/verify_provider.py` after changing any of the above to
confirm the configured chat and embedding providers actually connect — it
never prints secrets.

The foundational triage engine reads its own `triage/.env`
(from `triage/env.example`), not this file — see
[triage/docs/triage_engine.md](triage/docs/triage_engine.md). Never commit
either real `.env`; Git excludes `.env`/`.env.*` at every directory depth,
plus persisted `storage/` data.

## Verify the API

When Uvicorn reports that it is running on `http://127.0.0.1:8000`, open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- Health endpoint: `http://127.0.0.1:8000/health`

### Windows PowerShell Request

```powershell
$body = @{
    message = "What documents are required for member verification?"
    thread_id = "demo-session-001"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/chat" `
    -ContentType "application/json" `
    -Body $body
```

### Linux and macOS Request

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What documents are required for member verification?",
    "thread_id": "demo-session-001"
  }'
```

Expected response shape:

```json
{
  "response": "A grounded answer with inline source citations.",
  "thread_id": "demo-session-001"
}
```

Reuse a valid non-PII `thread_id` for related turns. A process restart clears
the current in-memory conversation history.

## Run Tests

Install dependencies first, then run the suite from the repository root.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Linux and macOS:

```bash
.venv/bin/python -m pytest -q
```

Tests use deterministic embeddings where `CI` is set and fake chat models for
model-boundary assertions. They do not require real patient information.

## Orchestration and Grounding Decisions

- LangChain provides the agent and typed tool interface; LangGraph provides
  checkpointed state by `thread_id`.
- The agent exposes exactly two narrow tools to reduce tool confusion.
- LlamaIndex performs semantic chunking and returns source nodes without an
  additional synthesis model.
- ChromaDB persists locally generated vectors and reloads a populated
  collection instead of duplicating ingestion.
- Retrieved nodes must share substantive normalized terms with the question.
  Unsupported retrieval returns exactly `Information not found.`
- Every retained policy or routing excerpt includes its source filename.

## Token Management

The local `llama3.2` model uses a 4,096-token context in the current setup.
`AGENT_HISTORY_TOKEN_BUDGET` defaults to 2,048 approximate tokens. Before each
model call, middleware keeps recent complete turns and reserves the remaining
context for the system prompt, tool schemas, retrieved evidence, and output.

The complete masked checkpoint remains in process while only the bounded slice
is sent to the model. Approximate counting is fast and model-independent, but
it is not identical to llama3.2's tokenizer.

## Privacy and Compliance Guardrails

The safeguards are designed to support principles in Kenya's
[Data Protection Act, 2019](https://new.kenyalaw.org/akn/ke/act/2019/24/eng@2022-12-31).
This implementation is a technical prototype, not a legal compliance
certification.

| Principle | AfyaPlus control |
|---|---|
| Data minimization | Supported phone numbers, emails, and member IDs are replaced before agent, model, memory, or tool processing. The request-local vault contains only values needed to restore that request's approved output. |
| Purpose limitation | The prompt and tool descriptions restrict processing to documented insurance verification, clinical routing, and clinician-supplied arithmetic. Diagnosis, prescribing, and dose selection are prohibited. |
| Security safeguards | Ollama and ChromaDB run locally by default; `.env` and vector storage are excluded from Git; the vault is excluded from normal representations; unhandled failures return a generic 503 response. |

Additional controls:

- User and retrieved text are treated as untrusted data, not instructions.
- Unknown placeholders are never expanded.
- Knowledge claims require retrieved evidence and inline citations.
- Invalid calculator inputs return controlled errors instead of crashing.
- Uncertainty and clinical-risk decisions are escalated to qualified humans.
- Tests prove that supported raw PII does not reach the fake model boundary.

Regex masking does not detect every possible identifier or phone formatting
variation. Names, addresses, national IDs, and formatted numbers containing
spaces or hyphens require additional controls before real patient use. See the
[privacy documentation](docs/privacy.md) for the full threat model.

## Current Operational Limitations

- No authentication, authorization, rate limiting, or production audit sink.
- Conversation memory is process-local and is not shared across workers.
- Health checks report process liveness, not Ollama or ChromaDB readiness.
- Local model quality and latency depend on host hardware.
- Human review remains required for clinical risk and benefits decisions.
- Docker and deployment packaging are intentionally deferred until after the
  course capstone.

Do not expose this prototype to untrusted networks or process real patient data
without production security, privacy, retention, monitoring, and governance
controls.

## Foundational Triage Engine

The repository retains its original Week 1 triage prototype in `triage/`, with
`triage_cli.py` as its entrypoint. It calls a configured cloud model first,
falls back to local Ollama, validates strict JSON, and applies conservative
routing checks.

Its cloud settings are the `OPENROUTER_API_KEY` or `OPENAI_API_KEY` option,
`MODEL_BASE_URL`, and `CLOUD_MODEL` values in `triage/env.example` — its own
environment, independent of the RAG API's repo-root `.env.example` above.

Run it from the repository root after installing the shared requirements:

```text
python triage_cli.py --help
python triage_cli.py
python triage_cli.py "My chest hurts and I cannot breathe properly"
python triage_cli.py --simulate-cloud-failure "My child has a fever and is very weak"
```

Foundational component resources:

- [Triage engine documentation](triage/docs/triage_engine.md)
- [Sample outputs](triage/docs/triage_engine_sample_outputs.md)
- [Published slides](https://docs.google.com/presentation/d/e/2PACX-1vQD_5HJ-tt-xmST0p_DmFGOLQqflMh_aHLZffcVLEEQtt863cSO5jotVzHmZmXdOg-0SYz39J_Aqr5U/pub?start=false&loop=false&delayms=3000)
