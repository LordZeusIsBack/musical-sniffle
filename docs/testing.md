# Testing Strategy

## Table of contents

1. [Purpose](#purpose)
2. [Unit testing strategy](#unit-testing-strategy)
3. [Integration testing](#integration-testing)
4. [Safety testing](#safety-testing)
5. [Example test cases](#example-test-cases)
6. [Expected outputs](#expected-outputs)
7. [Current implementation and future extension](#current-implementation-and-future-extension)
8. [Related documentation](#related-documentation)

## Purpose

This document defines how to test deterministic engines, API routes, persistence, safety gating, and privacy-sensitive behavior.

## Unit testing strategy

Unit tests should cover emotion scoring, vector updates, risk thresholds, symbolic conclusions, state-machine precedence, memory summarization, privacy noise disablement, and analytics calculations.

## Integration testing

Integration tests should exercise signup, login, authenticated chat, analytics endpoints, event persistence, explanation retrieval, and message history access. Database-backed tests should isolate data per test user.

## Safety testing

Safety tests must verify that explicit crisis language triggers `CRISIS_PROTOCOL`, critical risk bypasses generation, and safety-classifier failures fail closed by returning unsafe.

## Example test cases

| Test               | Input                              | Expected output                         |
| ------------------ | ---------------------------------- | --------------------------------------- |
| Risk low           | `[0,0,0,0]`                        | score `0`, level `LOW`                  |
| Risk critical edge | `[0.8,0.9,0.95,0.4]`               | score `0.85`, level `CRITICAL`          |
| Symbolic crisis    | phrase containing `suicide`        | conclusion `CRISIS_PROTOCOL`            |
| State anxious      | anxiety above `0.70` with low risk | mode `ANXIOUS`                          |
| Memory summary     | message about sleep                | summary mentions sleep-related distress |

## Expected outputs

Successful full test runs should complete without live Ollama calls unless those calls are mocked. Safety and LLM tests should use fakes or monkeypatching to avoid nondeterministic external behavior.

## Current implementation and future extension

### Current Implementation

The repository includes tests for engines, services, and routers.

### Future Extension

Add property-based tests for score bounds, migration tests, load tests, and golden-file tests for explanation trace schema versions.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
