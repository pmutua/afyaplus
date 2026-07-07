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

First, I run the default pregnancy example. The expected destination is
`Emergency Medical Call Team`.

Second, I run a breathing emergency: "My chest hurts and I cannot breathe
properly." The system should again route immediately to the emergency team.

Third, I simulate cloud failure. The app prints a warning, attempts local Ollama,
and still returns valid JSON. If Ollama is unavailable, it uses a static safety
fallback rather than crashing.

## 4:35-5:00 Risks and Next Steps

This is not a clinical device. It is a routing prototype. JSON validity does not
guarantee clinical correctness, and high-risk cases still need qualified human
review.

For production, AfyaPlus would need audit logs, privacy controls, monitoring,
rate limits, and regular evaluation against real triage outcomes.
