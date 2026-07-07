# Week 1 Video Script: AfyaPlus Triage Engine

Target length: 5 minutes.

## 0:00-0:45 Business Problem

AfyaPlus Health receives patient messages written in everyday language. Patients
do not send clean categories. They say things like "my chest hurts", "my child
has a fever", or "I am pregnant and my feet are swollen."

That is a business problem because the backend routing system needs predictable
machine-readable input. Without structure, critical cases can wait in the wrong
queue, routine cases can overload nurses, and engineers end up trying to parse
free text manually.

## 0:45-1:45 Solution

The Week 1 prototype is a Python triage engine. It accepts a patient message,
sends it to an AI model, and forces the response into one JSON object. That JSON
contains four fields: whether the case is a critical emergency, the detected
symptoms, a short reasoning summary, and the routing destination.

The app prints both the parsed dictionary and a one-line routing decision, so it
can be consumed by a future backend service.

## 1:45-2:45 Model Choice

The primary model path is GPT-4o-mini through an OpenAI-compatible API. It is
appropriate for this prototype because it is fast, affordable, and strong enough
to interpret short patient messages.

The backup model path is local Ollama using llama3.2. This matters because a
health routing system should not stop completely when the network is slow or a
cloud provider is unavailable. If the cloud call fails, the application
automatically tries local inference.

## 2:45-3:45 Safety Controls

The prompt is defensive. It tells the model to treat the patient message as
untrusted data, not instructions. It also blocks diagnosis, prescriptions,
dosage calculations, greetings, apologies, and markdown.

The app uses native JSON mode, then parses the raw model response with
`json.loads()`. After parsing, it validates every required field and rejects
unknown route values.

There is also a conservative safety layer in Python. If the message contains
obvious danger signs such as chest pain with breathing difficulty, pregnancy
with severe headache and swelling, severe bleeding, or serious child illness,
the app upgrades the route instead of relying only on the model.

## 3:45-4:35 Demo

First, I run the default pregnancy example:

```powershell
python app.py
```

The cloud model responds in 2.85 seconds. It detects severe headache and sudden
swelling of feet in a 7-month pregnancy, marks the case as a critical emergency,
and routes it to `Emergency Medical Call Team`.

Second, I run a breathing emergency: "My chest hurts and I cannot breathe
properly."

```powershell
python app.py "My chest hurts and I cannot breathe properly"
```

The cloud model responds in 2.20 seconds. It detects chest pain and breathing
difficulty, marks the case as critical, and routes immediately to
`Emergency Medical Call Team`.

Third, I simulate cloud failure. The app prints a warning, attempts local Ollama,
and still returns valid JSON.

```powershell
python app.py --simulate-cloud-failure "My child has a fever and is very weak"
```

With Ollama running, the fallback provider is `local-ollama`. It responds in
10.24 seconds, detects fever and weakness, and routes the child to
`Urgent Nurse Callback`. If Ollama is unavailable, the app uses a static safety
fallback rather than crashing.

Finally, I compare cloud and local latency:

```powershell
python app.py --compare-latency "I have had a headache for two days"
```

Across three runs, the cloud path averages 2.28 seconds and local Ollama
averages 7.77 seconds. This shows the cloud path is faster, while the local path
is a working resilience option.

## 4:35-5:00 Risks and Next Steps

This is not a clinical device. It is a routing prototype. JSON validity does not
guarantee clinical correctness, and high-risk cases still need qualified human
review.

For production, AfyaPlus would need audit logs, privacy controls, monitoring,
rate limits, and regular evaluation against real triage outcomes.
