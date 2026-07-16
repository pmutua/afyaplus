# Week 1 Slide Deck: AfyaPlus Triage Engine

Use this document as the source content for a 5-minute non-technical PowerPoint
presentation. The deck should focus on the business problem, the solution, why
the model choices make sense, and the operational risks.

Published presentation:
[Week 1 AfyaPlus Triage Engine slides](https://docs.google.com/presentation/d/e/2PACX-1vQD_5HJ-tt-xmST0p_DmFGOLQqflMh_aHLZffcVLEEQtt863cSO5jotVzHmZmXdOg-0SYz39J_Aqr5U/pub?start=false&loop=false&delayms=3000)

## Slide 1: Title

Title:
AfyaPlus Triage Engine

Subtitle:
Week 1 AI Engineering Capstone

On-slide bullets:

- Converts patient messages into structured routing decisions
- Cloud-first AI inference with local Ollama fallback
- Strict JSON output for backend automation

Speaker notes:
This presentation explains the Week 1 AfyaPlus triage prototype. The goal is to
take messy patient messages and convert them into a predictable routing decision
that a backend system can consume.

Visual suggestion:
Simple flow: Patient message -> AI triage engine -> JSON routing output.

## Slide 2: Business Problem

Title:
Unstructured Messages Block Reliable Routing

On-slide bullets:

- Patients write conversational messages, not clean categories
- Backend systems need predictable machine-readable inputs
- Poor routing can delay urgent care or overload clinical staff

Example messages:

```text
"My chest hurts and I cannot breathe properly"
"My child has a fever and is very weak"
"I am 7 months pregnant and my feet are suddenly swollen"
```

Speaker notes:
AfyaPlus receives patient messages in natural language. That is normal for
patients, but difficult for backend systems. Without structure, urgent cases can
sit in the wrong queue and routine messages can consume clinical attention.

Visual suggestion:
Show three messy message bubbles entering a routing bottleneck.

## Slide 3: Week 1 Objective

Title:
Build A Production-Style Triage Prototype

On-slide bullets:

- Accept a patient message from the command line
- Run cloud AI first
- Fall back to local Ollama if cloud fails
- Return one exact JSON object
- Print a one-line route

Speaker notes:
The Week 1 objective was not to build a full clinical system. It was to build a
safe inference engine that demonstrates prompt engineering, JSON enforcement,
timeouts, fallback, and operational resilience.

Visual suggestion:
Checklist with the five implementation goals.

## Slide 4: Key Terms

Title:
What The Triage Engine Is Doing

On-slide bullets:

- Preeclampsia detection: recognizing pregnancy danger-sign patterns
- Urgency classification: deciding how quickly care is needed
- General symptom triage: assessing symptoms and choosing the next route
- This prototype routes cases; it does not diagnose patients

Speaker notes:
The app combines three Week 1 concepts. It recognizes possible preeclampsia
danger signs, such as severe headache and sudden swelling in pregnancy, but it
does not diagnose preeclampsia. It classifies urgency and performs general
symptom triage by choosing the right backend route.

Visual suggestion:
Three connected blocks: Preeclampsia danger signs -> urgency classification ->
general triage route.

## Slide 5: System Architecture

Title:
Cloud First, Local Fallback

On-slide bullets:

- Primary path: GPT-4o-mini through an OpenAI-compatible API
- Fallback path: local Ollama using `llama3.2`
- Final safety fallback: deterministic keyword routing if both models fail

Flow:

```text
Patient message
  -> Cloud model
  -> Local Ollama fallback
  -> Static safety fallback
  -> JSON route
```

Speaker notes:
The app tries the cloud path first because it is faster and stronger for
language understanding. If that path fails, times out, or returns invalid JSON,
the app tries local Ollama. If both model paths fail, the app still returns a
safe structured result instead of crashing.

Visual suggestion:
Horizontal flow diagram with three fallback stages.

## Slide 6: Model Choice

Title:
Why Cloud Plus Local?

On-slide bullets:

- Cloud model: faster average response and stronger reasoning
- Local Ollama: keeps service usable during cloud or network failure
- OpenRouter and direct OpenAI are alternative cloud configurations
- Ollama is a system dependency, not a pip package

Speaker notes:
The cloud model gives better speed and reasoning when the network is healthy.
The local model gives resilience. OpenRouter and direct OpenAI are not two
separate fallbacks in this app; they are two ways to configure the same cloud
path.

Visual suggestion:
Two-column comparison: Cloud strengths vs Local strengths.

## Slide 7: Prompt Engineering

Title:
From Naive Prompt To Defensive Routing Engine

On-slide table:

| Version | Pattern | Why it changed |
|---|---|---|
| V1 | Simple urgency request | Could produce prose |
| V2 | Role plus JSON instruction | Better structure, limited safety |
| V3 | Defensive routing engine | Adds guardrails and exact JSON |

Speaker notes:
The final prompt gives the model a strict role: AfyaPlus Health triage routing
engine. It treats patient input as untrusted data, blocks diagnosis and
prescriptions, bans markdown and greetings, and asks the model to privately
check danger signs before returning JSON.

Visual suggestion:
Three-step prompt evolution ladder.

## Slide 8: Safety Guardrails

Title:
Safety Is More Than Prompting

On-slide bullets:

- Native JSON mode: `response_format={"type": "json_object"}`
- `json.loads()` parses raw model output
- Schema validation rejects missing, extra, or wrong-type fields
- Route validation allows only three destinations
- Post-parse rules prevent obvious under-routing

Allowed routes:

- `Emergency Medical Call Team`
- `Urgent Nurse Callback`
- `General Queue`

Speaker notes:
The app does not trust the model blindly. It validates the JSON shape and then
applies conservative safety rules for danger signs such as chest pain with
breathing difficulty, pregnancy with severe headache and swelling, severe
bleeding, confusion, and serious child illness.

Visual suggestion:
Layered safety stack: prompt, JSON mode, validation, conservative rules.

## Slide 9: Output Contract

Title:
Backend-Ready JSON

On-slide code:

```json
{
  "is_critical_emergency": true,
  "detected_symptoms": ["chest pain", "breathing difficulty"],
  "clinical_reasoning_summary": "Patient reports chest pain and difficulty breathing, indicating a potential critical emergency.",
  "routing_destination": "Emergency Medical Call Team"
}
```

Speaker notes:
The downstream backend is not being built this week, but this output is designed
for backend automation. It has a stable set of keys, strict types, and one of
three known routing destinations.

Visual suggestion:
Show JSON on one side and a route label on the other.

## Slide 10: Demo Scenario 1

Title:
Pregnancy Danger Signs

Command:

```powershell
python app.py
```

Observed result:

- Provider: `cloud`
- Latency: `2.85` seconds
- Detected symptoms: severe headache, sudden swelling of feet
- Route: `Emergency Medical Call Team`

Speaker notes:
The default test case is a 7-month pregnancy with severe headache and sudden
swelling. The app does not diagnose preeclampsia, but it treats this as a
high-risk pregnancy danger-sign pattern and routes to the emergency team.

Visual suggestion:
Small terminal screenshot or four result chips: provider, latency, symptoms,
route.

## Slide 11: Demo Scenario 2

Title:
Breathing Emergency

Command:

```powershell
python app.py "My chest hurts and I cannot breathe properly"
```

Observed result:

- Provider: `cloud`
- Latency: `2.20` seconds
- Detected symptoms: chest pain, breathing difficulty
- Route: `Emergency Medical Call Team`

Speaker notes:
Chest pain plus breathing difficulty is an obvious emergency pattern. The app
marks it as critical and routes immediately.

Visual suggestion:
Route decision callout: `ROUTE NOW: Emergency Medical Call Team`.

## Slide 12: Demo Scenario 3

Title:
Cloud Failure Fallback

Command:

```powershell
python app.py --simulate-cloud-failure "My child has a fever and is very weak"
```

Observed result:

- Cloud path prints warning
- Provider: `local-ollama`
- Latency: `10.24` seconds
- Detected symptoms: fever, weakness
- Route: `Urgent Nurse Callback`

Speaker notes:
This demonstrates the resilience requirement. The cloud path is forced to fail,
the app automatically reroutes to local Ollama, and the system still returns
valid JSON plus a routing decision.

Visual suggestion:
Warning icon over cloud, arrow to local machine, then JSON route.

## Slide 13: Latency Comparison

Title:
Cloud Is Faster, Local Keeps Running

Command:

```powershell
python app.py --compare-latency "I have had a headache for two days"
```

Observed results:

| Run | Cloud seconds | Local seconds |
|---:|---:|---:|
| 1 | 2.26 | 7.75 |
| 2 | 2.40 | 7.79 |
| 3 | 2.17 | 7.77 |
| Average | 2.28 | 7.77 |

Speaker notes:
Across three runs, the cloud path averaged 2.28 seconds and local Ollama
averaged 7.77 seconds. The cloud path is faster, but the local path gives the
system a working fallback when cloud access is unavailable.

Visual suggestion:
Simple bar chart: cloud average vs local average.

## Slide 14: Risks And Constraints

Title:
Operational Risks

On-slide bullets:

- Prototype only, not a clinical device
- JSON validity does not guarantee clinical correctness
- Local model quality may be weaker than cloud model quality
- Cloud use creates privacy and data governance requirements
- Production needs audit logs, monitoring, human review, and rate limits

Speaker notes:
This is a routing prototype. It should help organize patient messages, not
replace clinical judgment. Real deployment would require privacy controls,
monitoring, audit trails, and qualified human review for high-risk cases.

Visual suggestion:
Risk checklist with mitigation notes.

## Slide 15: Submission Summary

Title:
What Week 1 Delivered

On-slide bullets:

- `app.py`: executable triage engine
- `requirements.txt`: direct Python dependencies
- `.env.example`: cloud and local configuration
- `docs/week1.md`: implementation documentation
- `docs/week1_sample_outputs.md`: three demo scenarios
- `docs/week1_slide_deck.md`: slide deck source content
- `docs/week1_video_script.md`: five-minute narration script

Speaker notes:
The Week 1 submission includes the working app, the setup files, sample outputs,
latency evidence, and supporting presentation material. The repo is structured
so Week 2 can be added without mixing its documentation into Week 1.

Visual suggestion:
Folder tree or deliverables checklist.

## Optional Appendix: Full Run Commands

Use these if the presentation includes a live terminal demo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull llama3.2
ollama serve
python app.py --help
python app.py
python app.py "My chest hurts and I cannot breathe properly"
python app.py --simulate-cloud-failure "My child has a fever and is very weak"
python app.py --compare-latency "I have had a headache for two days"
```

## Optional Appendix: Final `.env` Shape

OpenRouter option:

```text
OPENROUTER_API_KEY=sk-or-your-real-key
MODEL_BASE_URL=https://openrouter.ai/api/v1
CLOUD_MODEL=openai/gpt-4o-mini

OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=ollama
LOCAL_TIMEOUT_SECONDS=20.0
```

Direct OpenAI option:

```text
OPENAI_API_KEY=sk-your-real-openai-key
MODEL_BASE_URL=https://api.openai.com/v1
CLOUD_MODEL=gpt-4o-mini

OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=ollama
LOCAL_TIMEOUT_SECONDS=20.0
```

Do not commit the real `.env` file.
