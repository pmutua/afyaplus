# Deployment Architecture Research and Decision Record

## Status

**Decision implemented:** issue #32, commit `8d342f8`.

AfyaPlus currently uses:

| Layer | Selected service |
|---|---|
| Application orchestration | Railway-hosted FastAPI, Chainlit, LangGraph, and LlamaIndex |
| Chat inference | Ollama Cloud, with optional local fallback |
| Embedding inference | Qdrant Cloud Inference |
| Vector storage/search | Dedicated Qdrant Cloud collection |

This document records why that architecture was selected and which alternatives
remain relevant. It is not the setup guide; see [deployment.md](deployment.md)
for current configuration and operations.

Issue #33 adds Chainlit as a browser interface mounted inside FastAPI. This is
an interface decision, not a change to the selected inference or persistence
architecture: both `/ui` and `/chat` call the same privacy-safe service and
agent graph.

## Decision Drivers

- Remove embedding-model memory and startup cost from Railway.
- Avoid running an Ollama or FastEmbed sidecar only for embeddings.
- Keep embedding and vector search behind one managed API.
- Preserve the existing LangGraph agent and LlamaIndex document pipeline.
- Keep the capstone inexpensive and simple while it uses synthetic data.
- Retain a credible migration path for future regulated workloads.

## Options Evaluated

| Option | Advantages | Costs and limitations | Decision |
|---|---|---|---|
| Ollama embeddings + Chroma | Local privacy boundary; original rubric alignment | Ollama daemon, local model memory, persistent disk | Superseded |
| FastEmbed + Chroma | No daemon; efficient CPU inference | Still consumes Railway CPU/RAM and local storage | Superseded by #32 |
| Self-hosted Qdrant + local embedding | Full infrastructure control | More services, backups, scaling, and monitoring | Future regulated option |
| Qdrant Cloud Inference | One API for embedding, storage, and search; no local ML | External processor, network dependency, curated models | Selected for synthetic capstone |
| PostgreSQL + pgvector | Relational joins and vectors in one database | Requires a relational use case and more embedding plumbing | Revisit if Postgres becomes core |
| AWS/Azure/GCP managed stack | Mature enterprise governance and consolidated procurement | Higher complexity and cost | Future production option |

## Selected Qdrant Design

The official Qdrant client is initialized with `cloud_inference=True`.
Ingestion and retrieval pass text as `Document` inference objects using
`sentence-transformers/all-MiniLM-L6-v2`. The collection uses 384-dimensional
cosine vectors.

Qdrant stores one point per LlamaIndex chunk. Payload data is deliberately
minimal:

```text
text
metadata.file_name
```

No absolute filesystem path, API key, user message, privacy vault, or raw
patient identifier belongs in the collection.

The application collection is `afyaplus_knowledge_base`. Keep it dedicated to
the deployed application and separate from unrelated workloads or external
tools.

## Chunking Trade-off

The original implementation used LlamaIndex `SemanticSplitterNodeParser`,
which requires an embedding model that returns vectors to the application.
Qdrant Cloud Inference embeds inside Qdrant vector operations and does not
provide the LlamaIndex `BaseEmbedding` interface used by that parser.

To achieve the primary deployment goal—zero local embedding-model compute—the
pipeline now uses LlamaIndex `SentenceSplitter` with 512-token chunks and
64-token overlap. Retrieval remains semantic because Qdrant embeds both chunks
and queries. If embedding-dependent semantic chunk boundaries become a quality
requirement, evaluate a managed embedding API that returns vectors or an
offline ingestion worker rather than adding model compute to the web process.

## Model Considerations

MiniLM is small, inexpensive, and available through Qdrant's free managed
inference path. Its 384-dimensional output is sufficient for the small
synthetic knowledge base, but model choice should be validated with a golden
query set before production.

Future evaluation should compare:

- policy and clinical-routing recall;
- citation precision and `Information not found.` accuracy;
- English and Swahili query behavior;
- latency at expected concurrency;
- cost, region, retention, and contractual requirements.

Changing the embedding model or dimensions requires a new/rebuilt collection.
Never mix vectors from different models in the same unnamed vector space.

## Privacy and Compliance Boundary

Patient text and clinical records can be regulated data. Sending text to
Qdrant Cloud Inference, Ollama Cloud, or another hosted provider makes that
provider part of the data-processing chain.

The current capstone uses synthetic knowledge and test data. A badge or general
compliance statement is not evidence that a specific service, region, plan, or
inference feature is covered by a required agreement. Before real PHI:

- confirm data classification and allowed processing purposes;
- obtain the necessary provider agreements and legal approval;
- verify inference and storage regions;
- document retention, deletion, backup, access, and incident procedures;
- test that masking covers the approved data inventory;
- ensure chat prompts and retrieval payloads contain only necessary data.

Qdrant currently notes that free hosted inference models are US-hosted. Region
and model availability can change, so verify the cluster's Inference tab and
official documentation during every production review.

## When to Reconsider the Decision

Revisit this architecture when any of these becomes true:

- AfyaPlus begins processing real PHI or patient records.
- A signed agreement does not cover Cloud Inference specifically.
- A required embedding model is unavailable through Qdrant.
- Retrieval evaluation shows MiniLM quality is inadequate.
- The product adopts PostgreSQL as a core transactional database.
- Network latency or Qdrant availability violates service objectives.
- Enterprise procurement requires a single AWS, Azure, or Google Cloud stack.

## Future Architecture Paths

### Self-hosted privacy-first

```text
Railway/private compute -> FastEmbed or Ollama embedding -> self-hosted Qdrant
```

This restores infrastructure control but also restores model compute,
operations, backups, and scaling responsibility.

### Relational consolidation

```text
Application -> managed embedding API -> PostgreSQL + pgvector
```

Choose this when relational data and SQL joins are already central to the
product. Do not add PostgreSQL solely to replace a working small Qdrant
collection.

### Single hyperscaler

AWS Bedrock/OpenSearch, Azure OpenAI/AI Search, or Vertex AI/Vector Search can
consolidate identity, audit, networking, and contracting. This can simplify an
enterprise compliance story but is unnecessary complexity for the synthetic
capstone.

## Open Evaluation Work

- Build a versioned golden query set with expected sources.
- Measure retrieval recall, citation precision, and not-found correctness.
- Test English/Swahili and policy-specific terminology.
- Define a safe blue/green collection rebuild procedure.
- Confirm provider agreements before any real patient-data pilot.
- Add external readiness monitoring and key-rotation procedures.

## Official Sources

- [Qdrant Cloud quickstart and managed `Document` inference](https://qdrant.tech/documentation/cloud/quickstart-cloud/)
- [Qdrant Cloud Inference availability and regions](https://qdrant.tech/documentation/cloud/inference/)
- [Qdrant inference options](https://qdrant.tech/documentation/inference/)
- [Ollama Cloud](https://docs.ollama.com/cloud)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Railway FastAPI deployment](https://docs.railway.com/guides/fastapi)
- [Railway variables and secrets](https://docs.railway.com/variables)
- [Chainlit FastAPI integration](https://docs.chainlit.io/integrations/fastapi)
- [Chainlit deployment overview](https://docs.chainlit.io/deploy/overview)
