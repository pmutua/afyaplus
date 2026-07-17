# AfyaPlus RAG Agent API

## Run Locally on Windows

From the repository root, create and activate the project virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `QDRANT_URL` and `QDRANT_API_KEY` in the gitignored `.env`. Never copy a
real key into `.env.example`.

Install Ollama separately and ensure the required models are available:

```powershell
ollama pull llama3.2
ollama list
```

Ollama commonly runs as a Windows background service. If
`http://127.0.0.1:11434` is already listening, do not start a second
`ollama serve` process.

Start the API:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI documentation is available at
`http://127.0.0.1:8000/docs`; the raw schema is at `/openapi.json`.

## `GET /health`

Returns process liveness:

```json
{
  "status": "ok"
}
```

Status: `200 OK`.

This endpoint does not query Ollama or Qdrant, so it is not a dependency
readiness check.

## `POST /chat`

Submits one conversation turn.

### Request

```json
{
  "message": "Check member AP-123456 maternity waiting-period policy.",
  "thread_id": "demo-session-001"
}
```

| Field | Type | Validation | Meaning |
|---|---|---|---|
| `message` | string | Trimmed, 1-8,000 characters | User question or permitted calculation request |
| `thread_id` | string | Trimmed, 1-128 characters, letters/digits/`_`/`-` only | Non-PII conversation key |

Do not place a phone number, email address, member ID, name, or other personal
identifier in `thread_id`. Unlike `message`, the thread ID is a routing key and
is not passed through the masking function.

### Success Response

```json
{
  "response": "Member AP-123456 is subject to the documented policy. [Source: insurance_verification_policy.txt]",
  "thread_id": "demo-session-001"
}
```

Status: `200 OK`. The exact natural-language answer depends on the request,
retrieved evidence, tool calls, and local model.

### Privacy Behavior

Supported phone numbers, emails, and AfyaPlus IDs in `message` are replaced by
typed placeholders before the agent and model receive the text. If the final
answer includes one of the current request's placeholders, the API restores
the original value immediately before returning the response.

The API never returns the placeholder vault. Unknown placeholders are not
expanded. See [privacy.md](privacy.md) for the complete boundary and known
limitations.

### Conversation Behavior

Reuse the same `thread_id` for related turns. LangGraph stores masked history
in process-local memory and isolates it by thread ID. A process restart clears
history. Multiple application workers do not share history.

Only recent complete turns, bounded by `AGENT_HISTORY_TOKEN_BUDGET`, are sent
to the model on each call. The complete in-process checkpoint remains until
the process ends.

### Validation Error

Malformed JSON, missing fields, empty values, messages longer than 8,000
characters, or invalid thread IDs produce FastAPI's `422 Unprocessable Entity`
response with validation details.

Example invalid request:

```json
{
  "message": "Habari",
  "thread_id": "contains spaces"
}
```

### Service Error

An unhandled agent or model failure produces:

```json
{
  "detail": "The AfyaPlus assistant is temporarily unavailable."
}
```

Status: `503 Service Unavailable`.

The knowledge tool handles its own retrieval exceptions and normally returns
a temporary-unavailability tool result to the agent instead of propagating an
exception to the API.

## Example PowerShell Request

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

## Current Operational Boundaries

The API is a capstone prototype. It currently has no authentication,
authorization, rate limiting, durable/distributed memory, or production audit
sink. Bind it to localhost for development and do not expose it to untrusted
networks or submit real patient data without adding those controls.
