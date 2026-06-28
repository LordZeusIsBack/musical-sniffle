# Deployment Guide

## Table of contents

1. [Purpose](#purpose)
2. [Local deployment](#local-deployment)
3. [Docker deployment](#docker-deployment)
4. [Environment variables](#environment-variables)
5. [Database initialization](#database-initialization)
6. [pgvector setup](#pgvector-setup)
7. [Ollama setup](#ollama-setup)
8. [Production considerations](#production-considerations)
9. [Current implementation and future extension](#current-implementation-and-future-extension)
10. [Related documentation](#related-documentation)

## Purpose

This guide explains how the backend is configured and what infrastructure it expects.

## Local deployment

Typical local commands are:

```bash
make install
make dev
```

PostgreSQL with pgvector and a local Ollama-compatible endpoint are expected.

## Docker deployment

### Current Implementation

No Dockerfile or Compose file is present in the repository.

### Future Extension

A production-ready Compose setup should include the API, PostgreSQL with pgvector, Ollama, persistent volumes, health checks, and migration execution.

## Environment variables

| Variable                  | Default                       | Purpose                                    |
| ------------------------- | ----------------------------- | ------------------------------------------ |
| `APP_NAME`                | Therapy Chatbot Backend       | Application label.                         |
| `JWT_SECRET`              | change-me                     | Signing secret; must change in production. |
| `JWT_ALGORITHM`           | HS256                         | JWT algorithm.                             |
| `JWT_EXPIRES_MINUTES`     | 120                           | Token lifetime.                            |
| `DATABASE_URL`            | local asyncpg URL             | Application database connection.           |
| `DATABASE_ADMIN_URL`      | unset                         | Optional admin connection.                 |
| `OLLAMA_BASE_URL`         | `http://localhost:11434/v1`   | OpenAI-compatible Ollama API.              |
| `GENERATOR_MODEL`         | `llama3.1:8b-instruct-q4_K_M` | Generator model.                           |
| `SAFETY_MODEL`            | `shieldgemma:2b`              | Safety classifier model.                   |
| `DECAY_LAMBDA`            | 0.1                           | Emotional decay.                           |
| `SENSITIVITY_ALPHA`       | 0.3                           | Emotional sensitivity.                     |
| `ENABLE_DP`               | false                         | Enables vector noise.                      |
| `DP_NOISE_SIGMA`          | 0.01                          | Noise standard deviation.                  |
| `HIGH_RISK_THRESHOLD`     | 0.60                          | State-machine high threshold.              |
| `CRITICAL_RISK_THRESHOLD` | 0.85                          | State-machine critical threshold.          |
| `PSEUDONYM_HMAC_KEY`      | pseudonym-key                 | HMAC key for pseudonyms.                   |

## Database initialization

The application uses SQLAlchemy models and includes a migration file for neuro-symbolic tables. Development startup may create tables automatically depending on `app/database.py` behavior.

## pgvector setup

The migration runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The database user must have permission to create or use the extension.

## Ollama setup

Ollama must expose an OpenAI-compatible `/chat/completions` endpoint at `OLLAMA_BASE_URL`. Pull or configure the generator and safety models named by environment variables.

## Production considerations

Change default secrets, enforce HTTPS, use a managed migration process, restrict database privileges, define retention policies, configure observability, and decide whether raw chat persistence is acceptable.

## Current implementation and future extension

### Current Implementation

Local deployment is documented; container deployment is not yet implemented in repository files.

### Future Extension

Add Docker assets, migration tooling, health endpoints, and deployment-specific security hardening.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
