-- Privacy-preserving neuro-symbolic architecture tables.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS emotional_snapshots (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    vector vector(4) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS explanation_records (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    trace JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS system_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
