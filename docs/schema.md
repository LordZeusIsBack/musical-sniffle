# Database Schema

## Table of contents

1. [Purpose](#purpose)
2. [Complete ER diagram](#complete-er-diagram)
3. [Table descriptions](#table-descriptions)
4. [Foreign keys](#foreign-keys)
5. [Indexes](#indexes)
6. [JSONB fields](#jsonb-fields)
7. [Vector fields](#vector-fields)
8. [Relationship explanations](#relationship-explanations)
9. [Current implementation and future extension](#current-implementation-and-future-extension)
10. [Related documentation](#related-documentation)

## Purpose

This document describes the persistent data model implemented by the SQLAlchemy ORM and migration file.

## Complete ER diagram

```mermaid
erDiagram
    users ||--o{ conversations : owns
    conversations ||--o{ messages : contains
    users ||--|| emotional_states : has_current
    users ||--o{ emotional_snapshots : has_history
    users ||--o{ explanation_records : has_traces
    users ||--o{ system_events : has_events
    users ||--o{ memory_embeddings : has_memories

    users {
      uuid id PK
      string pseudonym_id UK
      string email UK
      string password_hash
      timestamptz created_at
    }
    conversations {
      uuid id PK
      uuid user_id FK
      string title
      timestamptz created_at
      timestamptz updated_at
    }
    messages {
      uuid id PK
      uuid conversation_id FK
      string role
      text content
      timestamptz created_at
    }
    emotional_states {
      uuid id PK
      uuid user_id FK_UK
      vector4 vector
      timestamptz updated_at
    }
    emotional_snapshots {
      uuid id PK
      uuid user_id FK
      timestamptz timestamp
      vector4 vector
      string mode
      float risk_score
    }
    explanation_records {
      uuid id PK
      uuid user_id FK
      timestamptz created_at
      jsonb trace
    }
    system_events {
      uuid id PK
      uuid user_id FK
      timestamptz timestamp
      string event_type
      jsonb payload
    }
    memory_embeddings {
      uuid id PK
      uuid user_id FK
      vector768 embedding
      string summary
      timestamptz created_at
    }
```

## Table descriptions

| Table                 | Purpose                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------- |
| `users`               | Authentication identity, password hash, email, pseudonym.                                   |
| `conversations`       | User-owned chat threads with title and update timestamp.                                    |
| `messages`            | Ordered user/bot messages for each conversation. Current implementation stores raw content. |
| `emotional_states`    | One current emotional vector per user.                                                      |
| `emotional_snapshots` | Historical emotional vectors with state mode and risk score.                                |
| `explanation_records` | JSONB traces explaining each processed message.                                             |
| `system_events`       | Audit-style event log for chat processing milestones.                                       |
| `memory_embeddings`   | Privacy-oriented memory summaries and vector embeddings.                                    |

## Foreign keys

All user-owned analytic/memory/event tables reference `users(id)` with cascade delete. `messages` references `conversations(id)` with cascade delete, and `conversations` references `users(id)`.

## Indexes

The ORM marks several columns as indexed: `users.email`, `users.pseudonym_id`, user foreign keys, snapshot timestamp, snapshot mode, event timestamp, event type, and memory creation time. The migration shown in the repository creates tables and pgvector extension but does not explicitly create every ORM-declared index.

## JSONB fields

- `explanation_records.trace`: structured explanation metadata including message analysis, signal vector, previous/updated state, momentum, risk, mode, and safety check.
- `system_events.payload`: event-specific metadata. Payload shape varies by event type.

## Vector fields

- `emotional_states.vector`: `Vector(4)` for `[depression, self_harm, suicidality, anxiety]`.
- `emotional_snapshots.vector`: `Vector(4)` historical state.
- `memory_embeddings.embedding`: `Vector(768)` for memory retrieval.

## Relationship explanations

A user has one current state but many snapshots. Conversations and messages provide chat history. Explanation records and events are parallel audit/interpretability records. Memory embeddings support retrieval-augmented generation scoped to each user.

## Current implementation and future extension

### Current Implementation

The app can create ORM tables during development startup. The migration enables pgvector and creates the neuro-symbolic tables.

### Future Extension

Add explicit migration coverage for all base tables and indexes, vector ANN indexes, retention fields, and encryption metadata for sensitive content.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
