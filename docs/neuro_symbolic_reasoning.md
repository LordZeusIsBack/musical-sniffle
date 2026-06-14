# neuro symbolic reasoning

This backend is evolved into a Privacy-Preserving Neuro-Symbolic Mental Health Assistant while preserving the no-raw-conversation-persistence boundary.

```mermaid
graph TD
User --> Safety[Safety Layer]
Safety --> Reasoner[Neuro-Symbolic Reasoner]
Reasoner --> Emotion[Hybrid Emotion Classifier]
Emotion --> State[Emotional State Machine]
State --> Risk[Risk Engine]
Risk --> Events[Event Stream]
Risk --> Memory[PGVector Semantic Memory]
Memory --> LLM[Local Ollama LLM]
LLM --> Response
```

## Privacy invariant
Raw messages are used transiently for local inference, safety checks, symbolic reasoning, and summary generation. Persistent tables store only vectors, summaries, event metadata, and explanation metadata.

## Mathematical core
Emotional update: `V_next = (1 - lambda)V_current + alpha*S`.
Risk: `0.40*suicidality + 0.30*self_harm + 0.20*depression + 0.10*anxiety`.
Momentum: `M_t = V_t - V_{t-1}`.
