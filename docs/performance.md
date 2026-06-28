# Performance and Scalability

## Table of contents

1. [Purpose](#purpose)
2. [Latency measurements](#latency-measurements)
3. [Throughput](#throughput)
4. [Bottlenecks](#bottlenecks)
5. [Scaling considerations](#scaling-considerations)
6. [Benchmark tables](#benchmark-tables)
7. [Current implementation and future extension](#current-implementation-and-future-extension)
8. [Related documentation](#related-documentation)

## Purpose

This document identifies expected performance characteristics and records benchmark placeholders where measurements are not yet available.

## Latency measurements

| Operation                   | Measurement | Notes                                                   |
| --------------------------- | ----------: | ------------------------------------------------------- |
| Signup                      |         TBD | Depends on database latency and password hashing.       |
| Login                       |         TBD | Database lookup plus password verification.             |
| Chat without generation     |         TBD | Engines and database writes.                            |
| Chat with Ollama generation |         TBD | Dominated by local model inference.                     |
| Memory retrieval            |         TBD | Depends on memory table size and vector index strategy. |

## Throughput

Throughput is expected to be limited by Ollama generation and database write volume for chat requests. Analytics read endpoints should be cheaper than generation endpoints.

## Bottlenecks

- Synchronous event inserts inside the request transaction.
- Local LLM generation latency.
- pgvector exact cosine scans if memory table grows without ANN indexes.
- Raw message and audit-table growth without retention policies.

## Scaling considerations

Use multiple FastAPI workers for CPU-light orchestration, separate Ollama capacity planning for inference, add PostgreSQL connection-pool tuning, introduce vector indexes after benchmarking, and move noncritical event consumers to background workers.

## Benchmark tables

| Scenario                        | p50 | p95 | p99 | Environment                                           |
| ------------------------------- | --: | --: | --: | ----------------------------------------------------- |
| `/auth/login`                   | TBD | TBD | TBD | TBD                                                   |
| `/chat/message` safe generation | TBD | TBD | TBD | TBD                                                   |
| `/chat/stream` first token      | TBD | TBD | TBD | Current streaming is simulated after full generation. |
| `/analytics/trends`             | TBD | TBD | TBD | TBD                                                   |

## Current implementation and future extension

### Current Implementation

No benchmark results are stored in the repository documentation. This file intentionally uses placeholders rather than invented measurements.

### Future Extension

Add reproducible benchmark scripts, dataset sizes, hardware descriptions, and regression thresholds in CI.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
