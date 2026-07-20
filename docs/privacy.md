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

## Not Currently Masked - a Real Gap, Not Just a Future Nice-to-Have

Masking is a fixed whitelist of three regex patterns. Everything outside
that whitelist passes through unmasked. For this domain (Kenyan insurance
verification), that gap includes identifiers that come up routinely in
real conversations:

| Not masked | Why it matters here |
|---|---|
| Full names | The single most common identifier in any message - never caught |
| Kenyan National ID (7-8 digits) | Standard KYC identifier - arguably more central to real verification than the member ID pattern that *is* covered |
| KRA PIN (e.g. `A012345678Z`) | Used for tax/billing-linked verification |
| Passport number | Alternative ID for dependents/expatriate members |
| Physical/postal address | Common in claims and dependents-coverage context |
| Date of birth | Routinely given alongside an ID for verification |
| M-Pesa transaction codes | Distinct from the phone number itself; appears in payment/claims disputes |
| Next-of-kin name/contact | Comes up in dependents-coverage questions |
| Free-text quasi-identifiers | e.g. "the only diabetic patient in my family in Kilimani" - no regex pattern can ever catch this category |

**This is a structural limitation, not just a missing-pattern list.** A
fixed regex whitelist can only ever catch identifiers with a known, fixed
format - it has no way to catch novel free-text identifying information
(names, addresses, quasi-identifying combinations) no matter how many
patterns are added. National ID and KRA PIN are good candidates for
*incremental* regex coverage, since they're fixed-format like the existing
three. Names, addresses, and free-text quasi-identifiers need a
fundamentally different approach - e.g. NER-based (Named Entity
Recognition) detection or a hybrid regex + small classifier model - before
this system's masking claim extends to "personal data" in the broader
sense the Kenya Data Protection Act (2019) uses, rather than just the
three identifier types actually implemented.

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

## Observability: Verifying Masking From Application Logs

`app/safeguards/middleware.py` logs both halves of the mask/demask round
trip at `INFO` level, so a reviewer can directly confirm the privacy
boundary is doing its job by reading application logs, without needing to
read source code or trust an unverified claim:

- On masking (`protect_chat_request`): logs the **masked** message (e.g.
  `Masked 1 PII item(s) for thread <id>: My phone is <<PHONE_1>>`) only
  when at least one identifier was found. The raw value never appears in
  this log line - only the placeholder token, by construction, since the
  logged string is `masked.masked_text`, not the original request text.
- On de-masking (`PrivacyContext.restore_output`): logs only a **count** of
  placeholders restored (e.g. `Restored 1 placeholder(s) for thread <id>.`)
  - never the restored text itself, since that is precisely the point in
    the pipeline where real PII reappears for the user.

Process-wide logging is configured once in `app/utils/logging.py` (called
from `create_app()`), covering both the FastAPI `/chat` route and the
Chainlit UI mounted in the same process. `tests/test_middleware.py`
includes regression tests asserting raw PII never appears in a captured
log record for either log line.

Vaults are isolated per request. A placeholder invented by the model or copied
from another request has no mapping in the current vault and therefore remains
unexpanded. Placeholder numbering is an internal implementation detail and
must not be treated as a durable identifier.

Chainlit stores only a generated `ui-<uuid>` routing key in its user session.
The current UI has no authentication or durable chat history. The browser
interface does not bypass masking, but it is still an additional network entry
point and must not be publicly exposed before access controls are added.
Spontaneous file uploads are disabled in `.chainlit/config.toml` because the
text-only privacy pipeline does not process uploaded content.

Chain-of-thought display defaults to hidden (`.chainlit/config.toml`'s `cot`
setting) and is overridable per environment with `CHAINLIT_COT_MODE`
(`hidden`, `tool_call`, or `full`) - keep it `hidden` in any shared or
production environment; only raise it for local debugging. The LangChain
callback handler that powers this display observes the same
`privacy.masked_message` sent to the model, so raw PII is never exposed even
when tool-call steps are visible - only masked placeholders, retrieved
knowledge excerpts, and calculator inputs/outputs ever appear in a step.

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
- The rate limiter retains salted client/session hashes and timestamps only;
  raw client identifiers are not used as stored keys.
- The prototype has no authentication, authorization, encryption policy,
  retention scheduler, distributed limiter, or production audit-log service.
- Rate-limit state resets on restart, and an unauthenticated user can evade the
  Chainlit session limit by opening a new chat session.

## Operational Requirements Before Production

- Add authenticated identities and role-based authorization.
- Apply those controls to both `/ui` WebSockets and HTTP API routes.
- Replace the in-process limiter with a shared Redis-backed implementation
  before running multiple workers or replicas.
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
