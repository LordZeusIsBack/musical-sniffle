# Design Decisions

## Table of contents

1. [Purpose](#purpose)
2. [Decision summary](#decision-summary)
3. [FastAPI](#fastapi)
4. [PostgreSQL](#postgresql)
5. [pgvector](#pgvector)
6. [Ollama](#ollama)
7. [Symbolic reasoning](#symbolic-reasoning)
8. [Event sourcing style records](#event-sourcing-style-records)
9. [Privacy-preserving summaries](#privacy-preserving-summaries)
10. [Trade-offs](#trade-offs)
11. [Current implementation and future extension](#current-implementation-and-future-extension)
12. [Related documentation](#related-documentation)

## Purpose

This document records major architectural choices and alternatives considered.

## Decision summary

| Choice                       | Reason                                                               |
| ---------------------------- | -------------------------------------------------------------------- |
| FastAPI                      | Async Python API with strong typing and simple dependency injection. |
| PostgreSQL                   | Reliable relational persistence for user-scoped safety data.         |
| pgvector                     | Stores vectors in the same transactional database as metadata.       |
| Ollama                       | Local-first model serving compatible with privacy goals.             |
| Symbolic reasoning           | Deterministic safety override for crisis phrases.                    |
| Event records                | Auditable request milestones and analytics support.                  |
| Privacy-preserving summaries | Reduce memory subsystem dependence on raw transcripts.               |

## FastAPI

Alternatives included Flask and Django. FastAPI fits the project because request validation, async endpoints, dependency injection, and OpenAPI generation are available with minimal boilerplate.

## PostgreSQL

Alternatives included SQLite and document stores. PostgreSQL supports relational integrity, JSONB fields, vector extension support, and mature deployment tooling.

## pgvector

Keeping vectors in PostgreSQL simplifies consistency and backup. A separate vector database could scale independently but would add operational complexity and cross-store consistency concerns.

## Ollama

Ollama supports local inference and an OpenAI-compatible API shape. This aligns with privacy requirements. The trade-off is that latency and model availability depend on local hardware.

## Symbolic reasoning

A pure model-based classifier may be opaque and nondeterministic. Explicit symbolic rules make crisis overrides inspectable. The trade-off is limited linguistic coverage.

## Event sourcing style records

The system records events for important milestones. This is not full event sourcing because core state is still stored in current-state tables, but it provides audit and debugging value.

## Privacy-preserving summaries

Memory summaries reduce the amount of raw text used for long-term personalization. The trade-off is loss of detail and possible summarization error.

## Trade-offs

The design prioritizes inspectability, local-first operation, and implementation simplicity over maximum semantic accuracy, full formal privacy guarantees, and large-scale distributed processing.

## Current implementation and future extension

### Current Implementation

The repository implements these choices in a compact monolithic backend.

### Future Extension

Evolve toward typed event schemas, calibrated risk models, formal privacy accounting, production migrations, and optional service decomposition only when operational evidence requires it.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
