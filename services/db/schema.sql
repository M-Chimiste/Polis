-- POLIS Postgres schema v0 (Nyx, pgvector enabled).
-- Apply: psql -h nyx -U polis -d polis -f services/db/schema.sql
-- Idempotent; safe to re-run.
--
-- Embedding dimension 384 assumes a sentence-transformers MiniLM-class
-- embedder (techContext: "small embedder ... sentence-transformers class").
-- Revisit before P2 if a different embedder is chosen — changing it is a
-- migration, not an edit.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS runs (
    run_id        uuid PRIMARY KEY,
    experiment_id text        NOT NULL,
    config        jsonb       NOT NULL, -- full experiment_config document
    config_hash   text        NOT NULL, -- covers sampling params by construction
    seed          bigint      NOT NULL,
    status        text        NOT NULL DEFAULT 'running', -- running|finished|failed|non_conforming
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz
);

CREATE TABLE IF NOT EXISTS agents (
    run_id   uuid  NOT NULL REFERENCES runs(run_id),
    agent_id text  NOT NULL,
    seed     jsonb NOT NULL, -- agent_seed document as instantiated for this run
    PRIMARY KEY (run_id, agent_id)
);

-- The permanent wall: append-only, byte-equal across replays.
CREATE TABLE IF NOT EXISTS ledger_events (
    run_id   uuid   NOT NULL REFERENCES runs(run_id),
    seq      bigint NOT NULL,
    tick     bigint NOT NULL,
    kind     text   NOT NULL,
    agent_id text,
    data     jsonb  NOT NULL,
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX IF NOT EXISTS ledger_events_run_tick ON ledger_events (run_id, tick);
CREATE INDEX IF NOT EXISTS ledger_events_run_kind ON ledger_events (run_id, kind);

CREATE TABLE IF NOT EXISTS memory_records (
    id         uuid  PRIMARY KEY,
    run_id     uuid  NOT NULL REFERENCES runs(run_id),
    agent_id   text  NOT NULL,
    kind       text  NOT NULL, -- observation|plan|reflection|conversation_summary
    tick       bigint NOT NULL,
    text       text  NOT NULL,
    importance smallint NOT NULL CHECK (importance BETWEEN 1 AND 10),
    citations  uuid[] NOT NULL DEFAULT '{}', -- citation edges (belief-divergence data)
    embedding  vector(384),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS memory_records_run_agent ON memory_records (run_id, agent_id, tick);

-- Plans are memory records (systemPatterns); this table holds plan structure
-- (day agenda -> hour chunks -> action steps) keyed to its memory record.
CREATE TABLE IF NOT EXISTS plans (
    id               uuid PRIMARY KEY,
    run_id           uuid NOT NULL REFERENCES runs(run_id),
    agent_id         text NOT NULL,
    memory_record_id uuid NOT NULL REFERENCES memory_records(id),
    level            text NOT NULL, -- daily|hourly|action_step
    parent_plan_id   uuid REFERENCES plans(id),
    tick_start       bigint NOT NULL,
    tick_end         bigint NOT NULL,
    body             jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS plans_run_agent ON plans (run_id, agent_id, tick_start);

-- Verbatim request+response for logged-completion replay.
CREATE TABLE IF NOT EXISTS completions (
    run_id     uuid   NOT NULL REFERENCES runs(run_id),
    agent_id   text   NOT NULL, -- '_world' for non-agent call sites
    call_site  text   NOT NULL,
    sequence   bigint NOT NULL,
    role       text   NOT NULL, -- gateway role (dialogue, reflection, ...)
    model      text   NOT NULL,
    request    jsonb  NOT NULL,
    response   jsonb  NOT NULL,
    latency_ms integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, agent_id, call_site, sequence)
);

-- Probe traffic is invisible to the sim: rows here, zero diff anywhere else.
CREATE TABLE IF NOT EXISTS probes (
    probe_id         uuid PRIMARY KEY,
    run_id           uuid NOT NULL REFERENCES runs(run_id),
    agent_id         text NOT NULL,
    kind             text NOT NULL, -- interview|fact_check
    tick             bigint NOT NULL,
    question         text NOT NULL,
    response         text NOT NULL,
    category         text,
    scores           jsonb,
    frozen_state_ref text,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS probes_run_agent ON probes (run_id, agent_id, tick);

CREATE TABLE IF NOT EXISTS metrics (
    run_id      uuid  NOT NULL REFERENCES runs(run_id),
    name        text  NOT NULL, -- e.g. diffusion_curve, graph_density, cost_per_agent_hour
    tick        bigint,         -- null for whole-run metrics
    value       jsonb NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, name, computed_at)
);
