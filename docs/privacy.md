# Privacy Boundary and Safeguards

## Scope

AfyaPlus masks supported identifiers before any request text reaches the chat
model, agent memory, or tools. It restores the corresponding values only in the
final approved response for the same request.

This control reduces disclosure risk; it is not a complete de-identification
system or a substitute for organizational access controls and governance.

## Supported PII

| Type | Accepted form | Placeholder example |
|---|---|---|
| Kenyan mobile number | Compact `+254` or `0` form whose nine-digit subscriber number begins with `7` or `1` | `<<PHONE_1>>` |
| Email address | Common local-part, domain, and two-or-more-letter suffix | `<<EMAIL_1>>` |
| AfyaPlus member/patient ID | `AP-` followed by six digits | `<<MEMBER_ID_1>>` |

Examples currently detected include `+254712345678`, `0712345678`,
`0112345678`, `patient@example.co.ke`, and `AP-123456`.

## Lifecycle of a Request

1. Chainlit or FastAPI constructs a Pydantic `ChatRequest`, which validates and
   trims the message and non-PII thread key.
2. Both interfaces call `run_chat()`, which immediately creates a
   `PrivacyContext` through `protect_chat_request`.
3. `mask()` scans phone numbers, then emails, then AfyaPlus IDs. Every match is
   replaced by a unique typed placeholder and stored in a request-local vault.
4. The shared service sends only the masked message to the agent; model,
   memory, and tools never receive the request-local vault.
5. The model is instructed to preserve placeholders exactly.
6. The final agent text is passed to `PrivacyContext.restore_output()`.
7. `demask()` replaces only tokens known to the current request's vault.
8. Chainlit displays or FastAPI serializes the restored response. The context
   becomes unreachable after request processing and is not deliberately
   persisted.

## Vault Controls

The vault is a private dataclass field marked `repr=False`, preventing raw PII
from appearing in normal representations. It is not passed into LangGraph,
written to conversation checkpoints, included in Qdrant metadata, or returned
by the API.

Vaults are isolated per request. A placeholder invented by the model or copied
from another request has no mapping in the current vault and therefore remains
unexpanded. Placeholder numbering is an internal implementation detail and
must not be treated as a durable identifier.

Chainlit stores only a generated `ui-<uuid>` routing key in its user session.
The current UI has no authentication or durable chat history. The browser
interface does not bypass masking, but it is still an additional network entry
point and must not be publicly exposed before access controls are added.
Chain-of-thought display and spontaneous file uploads are disabled in
`.chainlit/config.toml` to avoid exposing internal traces or accepting content
the text-only privacy pipeline does not process.

## Data by Component

| Component | Raw PII | Masked text | Persistent |
|---|---:|---:|---:|
| Chainlit/FastAPI request validation | Briefly | Yes | No |
| Request-local privacy vault | Yes | Mapping keys | No |
| Agent and configured chat model | No | Yes | Provider-dependent processing only |
| LangGraph `InMemorySaver` | No | Yes | Process lifetime only |
| Knowledge manuals and Qdrant Cloud | No by design | Masked query transient; synthetic policy chunks | Managed collection |
| Final UI/API response | Restored when referenced | Possibly unknown tokens | Returned to caller |

## Logging Rules

- Do not log request bodies, `ChatRequest`, mask vaults, prompts, or full model
  messages in shared logs.
- Log only operational metadata that is necessary, such as request IDs,
  durations, status codes, tool names, and sanitized error categories.
- Never attach raw exceptions to client responses. The API returns a generic
  503 and Chainlit displays a generic unavailable message for unhandled agent
  failures.
- Treat Qdrant collections, knowledge documents, and any future durable checkpoint
  store as controlled application data with access restrictions and backups.
- Treat Qdrant and Ollama Cloud as external processors. A masked query can
  still contain sensitive clinical context even after supported identifiers
  are removed, so masking alone does not authorize real-PHI processing.

## Prompt and Tool Safeguards

The system prompt treats user and retrieved content as untrusted data and says
that it cannot override system instructions. It prohibits diagnosis,
prescribing, dose selection, and reconstruction of identifiers. The agent is
limited to a grounded knowledge tool and a validated arithmetic tool.

These prompt controls complement the deterministic masking boundary. They are
not relied upon to remove PII: masking happens in application code before the
model call.

## Known Limitations

- Names, physical addresses, national IDs, passport numbers, free-form hospital
  identifiers, and other identifier classes are not currently detected.
- The Kenyan phone expression accepts compact numbers. Formatted values with
  spaces, parentheses, or hyphens are outside the current pattern.
- Regex can produce false positives and false negatives; tests cover the
  specified formats, not every real-world variation.
- PII introduced for the first time by a model or knowledge document has no
  request vault entry and cannot be automatically restored or classified.
- A later turn cannot restore a placeholder created for an earlier turn,
  because each vault is deliberately discarded after its own request.
- In-memory checkpoints are not durable, but masked messages still remain in
  process memory until the process ends.
- The prototype has no authentication, authorization, encryption policy,
  retention scheduler, rate limiting, or production audit-log service.

## Operational Requirements Before Production

- Add authenticated identities and role-based authorization.
- Apply those controls to both `/ui` WebSockets and HTTP API routes.
- Add transport encryption and documented encryption-at-rest controls.
- Expand PII detection from an approved data inventory and measure recall.
- Add PII-safe audit events, access review, retention, and deletion workflows.
- Use a durable memory store only after defining tenant isolation and expiry.
- Add human review for uncertain policy, clinical-risk, and benefits decisions.
- Confirm service-specific contracts, processing regions, retention, and
  deletion behavior for Qdrant Cloud Inference and the selected chat provider.
- Perform privacy, security, prompt-injection, and dependency reviews before
  processing real patient data.

The end-to-end API test records the exact fake-model input and verifies that
all three supported PII classes remain masked while the displayed response is
correctly restored.

The [deployment guide](deployment.md#privacy-and-production-readiness) and
[architecture decision record](deployment-architecture-research.md) document
the cloud-processing boundary and the conditions for reconsidering it.
