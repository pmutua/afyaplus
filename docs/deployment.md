# AfyaPlus RAG Deployment Guide

## Deployment Architecture

The deployed RAG application uses three managed boundaries:

```text
Railway
  FastAPI + Chainlit + LangGraph + LlamaIndex orchestration
       |                         |
       | chat                    | managed embedding/search
       v                         v
  Ollama Cloud              Qdrant Cloud
```

Railway runs no embedding model and stores no vectors locally. Qdrant Cloud
Inference embeds knowledge chunks and questions, persists vectors, and performs
semantic search. Ollama Cloud supplies chat completion. Local Ollama remains an
optional development chat provider and fallback.

The current prototype uses only synthetic knowledge documents. It must not
process real patient data without the controls in [Privacy and Production
Readiness](#privacy-and-production-readiness).

## Required Services

- A Qdrant Cloud cluster with Cloud Inference enabled.
- An Ollama Cloud account and API key when `MODEL_PROVIDER=ollama_cloud`.
- A Railway service connected to this repository for hosted deployment.
- Python 3.11 or newer.

Qdrant documents the same managed `Document` inference flow used by AfyaPlus in
its [Cloud quickstart](https://qdrant.tech/documentation/cloud/quickstart-cloud/).
Railway provides an official [FastAPI deployment
guide](https://docs.railway.com/guides/fastapi).

## Environment Variables

Start from `.env.example`. Put real secrets only in the gitignored `.env` for
local use and in Railway's Variables section for deployment.

### Chat

| Variable | Production value | Purpose |
|---|---|---|
| `MODEL_PROVIDER` | `ollama_cloud` | Select direct cloud chat |
| `OLLAMA_CLOUD_BASE_URL` | `https://ollama.com/v1` | OpenAI-compatible chat endpoint |
| `OLLAMA_CLOUD_MODEL` | An enabled cloud model | Chat and tool-calling model |
| `OLLAMA_CLOUD_API_KEY` | Secret | Ollama Cloud authentication |
| `CLOUD_TIMEOUT_SECONDS` | `30.0` | Chat request timeout |
| `AGENT_HISTORY_TOKEN_BUDGET` | `2048` | Approximate history sent per call |

Ollama documents direct cloud access and API-key authentication in its [Cloud
guide](https://docs.ollama.com/cloud). The application uses its documented
[OpenAI-compatible API](https://docs.ollama.com/api/openai-compatibility).

### Retrieval

| Variable | Production value | Purpose |
|---|---|---|
| `QDRANT_URL` | Cluster HTTPS endpoint | Managed vector database |
| `QDRANT_API_KEY` | Secret | Cluster authentication |
| `QDRANT_COLLECTION_NAME` | `afyaplus_knowledge_base` | Application-only collection |
| `QDRANT_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Managed dense model |
| `QDRANT_EMBEDDING_DIMENSIONS` | `384` | Model-compatible vector size |
| `QDRANT_TIMEOUT_SECONDS` | `30.0` | Qdrant request timeout |

Do not reuse the MCP/tooling collection `afyaplus-claude-notes`. Model and
dimension changes require a new or rebuilt collection.

## Local Verification

Install dependencies before running checks:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Verify the configured chat and Qdrant connections without printing keys:

```powershell
.\.venv\Scripts\python.exe scripts/verify_provider.py
```

The verification script opens or creates the configured Qdrant collection.
It does not ingest knowledge or send a sample chat request to Qdrant.

## Collection Lifecycle

The knowledge collection is initialized lazily on the first knowledge-tool
request:

1. The client connects with `cloud_inference=True`.
2. If the collection is absent, AfyaPlus creates a 384-dimensional cosine
   collection and records the embedding model as collection metadata.
3. LlamaIndex reads `knowledge/` and creates sentence-aware 512-token chunks
   with 64-token overlap.
4. Each chunk is uploaded as a Qdrant `Document`, so Qdrant generates the
   vector without local ML compute.
5. Only chunk text and `file_name` are stored as payload metadata.
6. A non-empty collection is reused on subsequent process starts.

Because a non-empty collection is treated as initialized, rebuild it after
changing source documents, chunking, model, or dimensions. Use a new collection
name for a reversible migration. Delete the old collection only after the new
one passes retrieval tests.

## Railway Configuration

Railway can deploy directly from the GitHub repository. Configure the service
variables above and use this start command:

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set the Railway health-check path to `/health`. Railway injects `PORT` and uses
it for health checks, as described in its [health-check
documentation](https://docs.railway.com/deployments/healthchecks).

`GET /health` proves only that the FastAPI process is alive. It does not test
Ollama or Qdrant readiness. Run `scripts/verify_provider.py` during controlled
deployment verification and exercise a synthetic grounded query after deploy.

Chainlit is mounted at `/ui` and uses WebSockets. Railway supports WebSockets
through the same public service, so no second process or port is required. Keep
the Uvicorn worker count at one while conversation checkpoints remain
in-memory; multiple workers can route successive socket or API turns to
different, isolated memory stores. Add a durable shared checkpointer and
session-affinity design before horizontal scaling.

Docker remains deliberately deferred for this capstone. Do not add Dockerfile
or Compose configuration as part of deployment documentation maintenance.

## Post-Deployment Checks

1. Confirm `GET /health` returns `200`.
2. Open `/ui/`, confirm the WebSocket session connects, and send a synthetic
   insurance-policy question.
3. Repeat a related question and confirm conversation context is retained.
4. Send a synthetic insurance-policy question through `POST /chat`.
5. Confirm grounded answers include tracked filename citations.
6. Ask an out-of-scope question and confirm `Information not found.` behavior.
7. Check Qdrant collection count and inference usage in the Cloud console.
8. Check application logs for sanitized provider/fallback warnings only.
9. Run the Postman scenarios in [manual-testing-postman.md](manual-testing-postman.md).

## Failure and Recovery

| Failure | Expected behavior | Operator action |
|---|---|---|
| Missing Qdrant configuration | Knowledge tool returns controlled unavailability | Correct Railway variables and redeploy |
| Qdrant timeout/outage | Retrieval fails without exposing credentials | Check cluster status, networking, and timeout |
| Chat provider failure | Configured fallback is attempted once when available | Review warning and provider health |
| Chainlit socket disconnect | UI reconnects or reports loss of connection | Check Railway service health and WebSocket path |
| Wrong model dimensions | Qdrant rejects incompatible vectors | Use a compatible collection or rebuild |
| Stale knowledge | Existing collection continues serving old chunks | Build and verify a new collection name |

Never log `.env`, API keys, authorization headers, request bodies, the privacy
vault, or full model messages.

## Privacy and Production Readiness

Qdrant Cloud and Ollama Cloud are external processors. Supported PII in user
messages is masked before tool or model processing, but retrieved knowledge is
sent to Qdrant during ingestion and tool results are sent to the chat provider.

The free Qdrant embedding models are US-hosted even when a cluster is in
another region; consult the current [Qdrant Cloud Inference region
documentation](https://qdrant.tech/documentation/cloud/inference/). Synthetic
capstone data is acceptable for this architecture. Before real PHI or patient
records are used:

- obtain legal and security approval for every processor and feature;
- confirm applicable contracts/BAAs and data-processing regions in writing;
- expand PII detection beyond the prototype patterns;
- add authentication, authorization, audit logging, retention, and deletion;
- protect both Chainlit WebSockets and FastAPI routes with the selected access
  controls;
- add encryption, key rotation, readiness monitoring, backups, and incident
  response;
- run retrieval-quality, privacy, prompt-injection, and dependency reviews.

See [privacy.md](privacy.md) and
[deployment-architecture-research.md](deployment-architecture-research.md) for
the complete boundary and decision rationale.

## Official References

- [Qdrant Cloud quickstart](https://qdrant.tech/documentation/cloud/quickstart-cloud/)
- [Qdrant Cloud Inference](https://qdrant.tech/documentation/cloud/inference/)
- [Ollama Cloud](https://docs.ollama.com/cloud)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Railway FastAPI guide](https://docs.railway.com/guides/fastapi)
- [Railway variables](https://docs.railway.com/variables)
- [Railway health checks](https://docs.railway.com/deployments/healthchecks)
- [Chainlit FastAPI integration](https://docs.chainlit.io/integrations/fastapi)
- [Chainlit deployment and WebSockets](https://docs.chainlit.io/deploy/overview)
