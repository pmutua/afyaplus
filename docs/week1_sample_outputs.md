# Week 1 Sample Outputs

These examples demonstrate three required scenarios. Exact wording can vary by
model, but the JSON shape and route values must remain stable.

## 1. Pregnancy Danger Signs

Command:

```powershell
python app.py
```

Expected route: `Emergency Medical Call Team`

Observed output:

```text
Patient message: Hello AfyaPlus, I am 7 months pregnant. I have had a severe headache for two days and my feet are suddenly very swollen. I feel safe waiting until my appointment next week.
Provider used: cloud
Latency seconds: 2.85
Parsed triage dictionary:
```

```json
{
  "is_critical_emergency": true,
  "detected_symptoms": [
    "severe headache",
    "sudden swelling of feet"
  ],
  "clinical_reasoning_summary": "The patient is 7 months pregnant and presents with a severe headache and sudden swelling of feet, which are concerning signs that may indicate a serious condition such as preeclampsia. Delaying care is unsafe.",
  "routing_destination": "Emergency Medical Call Team"
}
```

```text
ROUTE NOW: send case to Emergency Medical Call Team.
```

## 2. Breathing Emergency

Command:

```powershell
python app.py "My chest hurts and I cannot breathe properly"
```

Expected route: `Emergency Medical Call Team`

Observed output:

```text
Patient message: My chest hurts and I cannot breathe properly
Provider used: cloud
Latency seconds: 2.20
Parsed triage dictionary:
```

```json
{
  "is_critical_emergency": true,
  "detected_symptoms": [
    "chest pain",
    "breathing difficulty"
  ],
  "clinical_reasoning_summary": "Patient reports chest pain and difficulty breathing, indicating a potential critical emergency.",
  "routing_destination": "Emergency Medical Call Team"
}
```

```text
ROUTE NOW: send case to Emergency Medical Call Team.
```

## 3. Cloud Failure Fallback

Command:

```powershell
python app.py --simulate-cloud-failure "My child has a fever and is very weak"
```

Expected behavior:

- Cloud path prints a warning.
- The app attempts local Ollama automatically.
- If Ollama is available, provider should be `local-ollama`.
- If Ollama is unavailable, the static safety fallback still returns valid JSON.

Observed output with Ollama running:

```text
Patient message: My child has a fever and is very weak
[WARN] Cloud path failed: RuntimeError. Falling back to Ollama.
Provider used: local-ollama
Latency seconds: 10.24
Parsed triage dictionary:
```

```json
{
  "is_critical_emergency": false,
  "detected_symptoms": [
    "fever",
    "weakness"
  ],
  "clinical_reasoning_summary": "Child presents with fever and weakness, may require urgent attention.",
  "routing_destination": "Urgent Nurse Callback"
}
```

```text
ROUTE: send case to Urgent Nurse Callback.
```

If local Ollama is unavailable or times out, the final safety fallback still
returns the same JSON schema with provider `static-safety-fallback`.
