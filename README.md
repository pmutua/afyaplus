# AfyaPlus Triage Engine

Week 1 capstone prototype for the AfyaPlus health assistant. The app accepts a natural-language patient message, sends it through a defensive AI triage prompt, forces strict JSON output, parses it with Python, and prints a backend routing decision.

## What This Demonstrates

- Secure environment-based model configuration
- Cloud pathway using GPT-4o-mini through an OpenAI-compatible endpoint
- Local fallback pathway using Ollama
- Defensive role-based prompt with reasoning guardrails
- Native JSON mode with `response_format={"type": "json_object"}`
- `json.loads()` parsing and schema validation
- Timeout and provider fallback handling
- Conservative post-parse safety rules for known high-risk patterns
- Cloud-vs-local latency comparison support

## Setup

Install dependencies:

```powershell
py -3 -m pip install -r requirements.txt
```

Create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Configure at least one cloud key:

```text
OPENROUTER_API_KEY=...
MODEL_BASE_URL=https://openrouter.ai/api/v1
CLOUD_MODEL=openai/gpt-4o-mini
```

For local fallback, install Ollama and pull a model:

```powershell
ollama pull llama3.2
```

## Run

Default test case:

```powershell
py -3 app.py
```

Custom patient message:

```powershell
py -3 app.py "My chest hurts and I cannot breathe properly"
```

Demonstrate local fallback:

```powershell
py -3 app.py --simulate-cloud-failure "My child has a fever and is very weak"
```

Compare cloud and local latency:

```powershell
py -3 app.py --compare-latency "I have had a headache for two days"
```

## JSON Schema

The backend expects exactly this structure:

```json
{
  "is_critical_emergency": true,
  "detected_symptoms": ["severe headache", "sudden swelling"],
  "clinical_reasoning_summary": "Third-trimester pregnancy with persistent headache and sudden swelling suggests a high-risk pregnancy warning pattern.",
  "routing_destination": "Emergency Medical Call Team"
}
```

`app.py` validates:

- all required keys are present
- no extra keys are returned
- `is_critical_emergency` is boolean
- `detected_symptoms` is a list of strings
- summary and destination are strings

After parsing, the app also applies conservative safety rules for obvious
high-risk patterns. For example, chest pain plus breathing difficulty is forced
to `Emergency Medical Call Team`, and a child with fever plus weakness/vomiting
cannot remain in `General Queue`. This follows the Week 1 principle that prompts
are not enough; production systems need validation layers.

## Prompt Iteration Log

| Version | Prompt Pattern | Result | Why It Changed |
|---|---|---|---|
| V1 naive | Broad urgency request | Risk of paragraphs and conversational advice | Too hard for backend parsing |
| V2 constrained | Role plus JSON instruction | Better structure, but still weaker safety boundaries | Needed stronger guardrails |
| V3 defensive | Role, internal step checks, no fluff, exact JSON schema | Best fit for backend triage | Forces danger-sign evaluation and machine-readable output |

The final prompt uses a strict operational identity: `AfyaPlus Health triage routing engine`. It treats user input as untrusted data, blocks diagnosis/prescription behavior, checks danger signs before output, and returns only JSON.

## Baseline Latency Table

Fill this table with your own `--compare-latency` run because local hardware and network conditions vary.

Observed local run on July 7, 2026:

| Provider | Status | Latency seconds |
|---|---:|---:|
| cloud | APITimeoutError | n/a |
| local-ollama | success | 9.36 |

The cloud timeout is expected behavior when the request exceeds the capstone's
4-second transit limit. The important production behavior is that the local
fallback completed and returned parseable JSON.

## Sample Outputs

### Scenario 1: Pregnancy Emergency

Command:

```powershell
py -3 app.py
```

Expected behavior:

- detects severe headache and sudden swelling
- marks `is_critical_emergency` as `true`
- routes to `Emergency Medical Call Team`

Observed output:

```json
{
  "is_critical_emergency": true,
  "detected_symptoms": [
    "severe headache",
    "sudden swelling of feet"
  ],
  "clinical_reasoning_summary": "The patient is 7 months pregnant and presents with a severe headache and sudden swelling of feet, which are concerning signs that may indicate a serious condition requiring immediate attention.",
  "routing_destination": "Emergency Medical Call Team"
}
```

### Scenario 2: Breathing Emergency

Command:

```powershell
py -3 app.py "My chest hurts and I cannot breathe properly"
```

Expected behavior:

- detects chest pain and breathing difficulty
- marks critical emergency
- routes immediately

Observed output:

```json
{
  "is_critical_emergency": true,
  "detected_symptoms": [
    "chest pain",
    "breathing difficulty"
  ],
  "clinical_reasoning_summary": "The patient is experiencing chest pain and difficulty breathing, which are critical emergency symptoms.",
  "routing_destination": "Emergency Medical Call Team"
}
```

### Scenario 3: Cloud Failure Fallback

Command:

```powershell
py -3 app.py --simulate-cloud-failure "My child has a fever and is very weak"
```

Expected behavior:

- prints a warning that cloud failed
- calls local Ollama
- returns the same JSON schema if local model is available

Observed output:

```json
{
  "is_critical_emergency": false,
  "detected_symptoms": [
    "fever",
    "weakness"
  ],
  "clinical_reasoning_summary": "Child presents with fever and weakness, may require urgent attention but not immediate emergency.",
  "routing_destination": "Urgent Nurse Callback"
}
```

## Operational Risks

- The app is a prototype, not a clinical device.
- JSON validity does not guarantee clinical correctness.
- Local Ollama quality may be lower than the cloud model.
- The fallback path depends on Ollama running locally.
- High-risk cases should route to qualified human review.
- Real deployment needs logging, monitoring, rate limits, privacy controls, and stronger schema validation.

## Presentation Outline

1. Business problem: unstructured patient messages cannot drive backend routing.
2. Solution: defensive AI triage engine returning strict JSON.
3. Model choice: cloud GPT-4o-mini first, local Ollama fallback for resilience.
4. Safety: no diagnosis, no prescriptions, urgent routing for danger signs.
5. Risks: model errors, outages, local model quality, privacy, and need for human escalation.
