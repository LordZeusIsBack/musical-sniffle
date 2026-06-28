# Threat Model

## Table of contents

1. [Purpose](#purpose)
2. [Assets](#assets)
3. [Threat actors](#threat-actors)
4. [Attack vectors](#attack-vectors)
5. [Security assumptions](#security-assumptions)
6. [Mitigations](#mitigations)
7. [STRIDE-style threat analysis](#stride-style-threat-analysis)
8. [Current implementation and future extension](#current-implementation-and-future-extension)
9. [Related documentation](#related-documentation)

## Purpose

This document identifies security risks for a mental-health backend handling highly sensitive data.

## Assets

Primary assets are account credentials, JWTs, emails, raw messages, emotional vectors, risk scores, memory summaries, explanation traces, event logs, and Ollama prompts/responses.

## Threat actors

- External attacker targeting APIs.
- Malicious or careless operator with database access.
- Compromised client device.
- Misconfigured remote LLM provider.
- Authenticated user attempting cross-user access.

## Attack vectors

Credential stuffing, token theft, SQL injection, insecure CORS/deployment configuration, database leakage, prompt disclosure to remote inference endpoints, and authorization bypasses.

## Security assumptions

The database and Ollama endpoint are assumed to be controlled by the deployer. JWT secrets are assumed to be strong in production. TLS termination is assumed outside the app when deployed publicly.

## Mitigations

Current mitigations include password hashing, JWT authentication, authenticated user scoping in queries, SQLAlchemy query construction, safety fail-closed behavior, and per-user memory retrieval filters.

## STRIDE-style threat analysis

| STRIDE                 | Example                        | Current mitigation                     | Remaining work                                 |
| ---------------------- | ------------------------------ | -------------------------------------- | ---------------------------------------------- |
| Spoofing               | Stolen JWT                     | Expiring JWTs, logout blacklist        | Persistent token store, refresh-token strategy |
| Tampering              | Modify event records           | Application inserts events             | DB immutability controls absent                |
| Repudiation            | User/operator denies action    | Timestamped events                     | Strong audit integrity absent                  |
| Information disclosure | Database leak exposes messages | Password hashing, summaries for memory | Raw `messages.content` still sensitive         |
| Denial of service      | Slow LLM calls exhaust workers | Async HTTP calls                       | Rate limits and circuit breakers absent        |
| Elevation of privilege | Cross-user data access         | User-scoped queries                    | Broader authorization tests recommended        |

## Current implementation and future extension

### Current Implementation

The codebase has basic application security controls but not full production hardening.

### Future Extension

Add rate limiting, audit immutability, encryption, secret management, security headers, centralized logging, and dependency scanning.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
