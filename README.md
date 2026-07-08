# AfyaPlus Cumulative Capstone

This repository grows by week. The root README is the project index and current
submission summary. Week-specific notes, presentation scripts, and sample
outputs live in `docs/`.

## Repository Layout

```text
app.py
requirements.txt
.env.example
docs/
  week1.md
  week1_sample_outputs.md
  week1_slide_deck.md
  week1_video_script.md
```

## Week 1: Triage Engine

Implementation: `app.py`

Week 1 builds a Python inference engine that converts unstructured patient
messages into strict JSON for backend routing. It calls a cloud model first,
falls back to local Ollama when the cloud path fails, validates the JSON schema,
and prints a one-line routing decision.

Docs:

- [Week 1 documentation](docs/week1.md)
- [Week 1 sample outputs](docs/week1_sample_outputs.md)
- [Week 1 slide deck source](docs/week1_slide_deck.md)
- [Published Week 1 slides](https://docs.google.com/presentation/d/e/2PACX-1vQD_5HJ-tt-xmST0p_DmFGOLQqflMh_aHLZffcVLEEQtt863cSO5jotVzHmZmXdOg-0SYz39J_Aqr5U/pub?start=false&loop=false&delayms=3000)
- [Week 1 video script](docs/week1_video_script.md)

### Week 1 Prerequisites

- Python 3.11 or newer.
- A virtual environment inside this repository: `.venv`.
- Cloud API key in `.env`: use `OPENROUTER_API_KEY` with OpenRouter settings
  or `OPENAI_API_KEY` with direct OpenAI settings.
- Ollama installed as a system dependency for local fallback.
- Local model pulled with `ollama pull llama3.2`.

### Week 1 Setup And Run

From the repository root, create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create and configure the environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` after copying it. Choose one cloud provider option, then keep the
local Ollama settings for fallback.

Cloud configuration options, choose one:

```text
# Option A: OpenRouter
OPENROUTER_API_KEY=...
MODEL_BASE_URL=https://openrouter.ai/api/v1
CLOUD_MODEL=openai/gpt-4o-mini

# Option B: Direct OpenAI
OPENAI_API_KEY=...
MODEL_BASE_URL=https://api.openai.com/v1
CLOUD_MODEL=gpt-4o-mini
```

Do not configure both cloud options for normal use. The app has one cloud
inference path, and OpenRouter is checked first if both keys are present.
OpenRouter and direct OpenAI are alternatives for reaching a GPT-4o-mini class
cloud model, not two separate cloud fallbacks.

Local Ollama configuration:

```text
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=ollama
LOCAL_TIMEOUT_SECONDS=20.0
```

Keep the local settings because the application is designed to try cloud first
and then fall back to Ollama if the cloud request fails, times out, returns
invalid JSON, or cannot be reached. The cloud path gives stronger and faster
reasoning when the network is healthy. The local path keeps the triage engine
usable during cloud or network failure.

Example final `.env` using OpenRouter:

```text
OPENROUTER_API_KEY=sk-or-your-real-key
MODEL_BASE_URL=https://openrouter.ai/api/v1
CLOUD_MODEL=openai/gpt-4o-mini

OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=ollama
LOCAL_TIMEOUT_SECONDS=20.0
```

Example final `.env` using direct OpenAI:

```text
OPENAI_API_KEY=sk-your-real-openai-key
MODEL_BASE_URL=https://api.openai.com/v1
CLOUD_MODEL=gpt-4o-mini

OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=ollama
LOCAL_TIMEOUT_SECONDS=20.0
```

Never commit the real `.env` file.

Required Python dependencies are listed in `requirements.txt`:

```text
openai
python-dotenv
httpx
```

Ollama is not listed in `requirements.txt` because this app does not import a
Python `ollama` package. It calls Ollama through the local OpenAI-compatible HTTP
endpoint at `http://localhost:11434/v1`.

Install and prepare Ollama separately:

```powershell
ollama --version
ollama pull llama3.2
```

Start Ollama in a separate terminal before testing local fallback or latency
comparison:

```powershell
ollama serve
```

Run the application:

```powershell
python app.py --help
python app.py
python app.py "My chest hurts and I cannot breathe properly"
python app.py --simulate-cloud-failure "My child has a fever and is very weak"
python app.py --compare-latency "I have had a headache for two days"
```

If the virtual environment is not activated, use:

```powershell
.\.venv\Scripts\python.exe app.py
```

### Week 1 Prompt Engineering Log

| Version | Pattern | What happened | Why it changed |
|---|---|---|---|
| V1 | Simple urgency request | Could produce conversational prose | Backend needs predictable structured data |
| V2 | Role plus JSON instruction | Better shape, but weak safety boundaries | Needed stronger protection against hallucination and prompt injection |
| V3 | Defensive triage routing engine | Best fit for automation | Adds untrusted-input handling, private danger-sign checking, no diagnosis, no prescriptions, no markdown, exact JSON |

### Week 1 Guardrail Rationale

- Patient messages are treated as data, not instructions, to reduce prompt
  injection risk.
- The model is blocked from diagnosis, prescriptions, and dosage calculations
  because this prototype only routes cases.
- Conversational openings, apologies, and markdown are banned so the backend can
  parse raw JSON reliably.
- High-risk patterns are checked again after parsing so obvious danger signs are
  not under-routed if the model response is weak.

### Week 1 Baseline Latency

Run:

```powershell
python app.py --compare-latency "I have had a headache for two days"
```

Observed on July 7, 2026 across three runs:

| Run | Cloud status | Cloud seconds | Local status | Local seconds |
|---:|---|---:|---|---:|
| 1 | success | 2.26 | success | 7.75 |
| 2 | success | 2.40 | success | 7.79 |
| 3 | success | 2.17 | success | 7.77 |
| Average | success | 2.28 | success | 7.77 |

This confirms both cloud and local Ollama paths completed successfully. Local
latency depends on Ollama availability, hardware, and selected model.

## Future Weeks

Add each new week as its own README section and keep the full details in
matching docs files, for example:

```text
docs/week2.md
docs/week2_sample_outputs.md
docs/week2_slide_deck.md
docs/week2_video_script.md
```
