# API Sequence Diagrams

## Table of contents

1. [Purpose](#purpose)
2. [Signup sequence](#signup-sequence)
3. [Login sequence](#login-sequence)
4. [Chat message flow](#chat-message-flow)
5. [Streaming response flow](#streaming-response-flow)
6. [Analytics endpoint flow](#analytics-endpoint-flow)
7. [Related documentation](#related-documentation)

## Purpose

This document centralizes endpoint interaction diagrams. Architectural rationale is kept in [Architecture](architecture.md).

## Signup sequence

```mermaid
sequenceDiagram
    participant Client
    participant Auth
    participant DB
    Client->>Auth: POST /auth/signup
    Auth->>DB: check email uniqueness
    Auth->>Auth: hash password, pseudonymize UUID
    Auth->>DB: insert user + initial emotional state
    Auth-->>Client: JWT bearer token
```

## Login sequence

```mermaid
sequenceDiagram
    participant Client
    participant Auth
    participant DB
    Client->>Auth: POST /auth/login form username/password
    Auth->>DB: select user by email
    Auth->>Auth: verify password hash
    Auth-->>Client: JWT bearer token
```

## Chat message flow

```mermaid
sequenceDiagram
    participant Client
    participant Chat
    participant Engines
    participant DB
    participant Ollama
    Client->>Chat: POST /chat/message
    Chat->>DB: create/load conversation, insert user message
    Chat->>Engines: emotion, symbolic, risk, memory, safety
    Engines->>DB: events, snapshot, trace, memory
    Engines->>Ollama: safety classifier
    alt safe and non-critical
        Chat->>Ollama: generate reply
    else unsafe or critical
        Chat->>Chat: fixed safety reply
    end
    Chat->>DB: insert bot message, commit
    Chat-->>Client: reply + vector
```

## Streaming response flow

```mermaid
sequenceDiagram
    participant Client
    participant Chat
    participant DB
    participant Ollama
    Client->>Chat: GET /chat/stream?message=...
    Chat->>DB: persist user message and derived records
    Chat->>Ollama: generate full reply if allowed
    loop token chunks
        Chat-->>Client: SSE data: {token}
    end
    Chat->>DB: persist completed bot message
    Chat-->>Client: SSE data: {done, conversation_id, vector}
```

## Analytics endpoint flow

```mermaid
sequenceDiagram
    participant Client
    participant Analytics
    participant DB
    Client->>Analytics: GET /analytics/history|trends|risk|events|explain/{id}
    Analytics->>DB: query authenticated user's records
    Analytics->>Analytics: compute trend/momentum/risk when needed
    Analytics-->>Client: typed response
```

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
