# Deployment Guide

This guide covers provisioning the persistence services required for vector-backed
memories and configuring the core service to connect to them.

## Services Overview

The Docker Compose stack in this repository provisions both a relational and a
vector database:

- **`memory-db`** – PostgreSQL with the pgvector extension for similarity search.
- **`vector-db`** – Chroma REST server for embedding-based retrieval.

Both services are optional at runtime. When the vector backend is unavailable or
misconfigured the orchestrator automatically falls back to the local JSON
persistence stores.

## Docker Compose

1. Ensure Docker and Docker Compose are installed on the host.
2. Select the desired configuration profile:
   - `config/docker.yaml` targets the bundled Chroma service.
   - `config/docker.pgvector.yaml` points to the PostgreSQL + pgvector service.
3. Launch the stack:

```bash
# Chroma-backed deployment
docker compose up --build

# pgvector-backed deployment
cp config/docker.pgvector.yaml config/docker.yaml
docker compose up --build
```

The core container waits for both database services to become reachable before
starting the application.

## Bare-Metal Installations

When installing directly on a host (e.g., via `install.sh` or systemd), use the
`AGI_CORE_INSTALL_VECTOR=1` flag to pull in the optional dependencies and ensure
that either Chroma or PostgreSQL/pgvector is reachable from the configured
connection strings.

Update the `memory` section in your active configuration profile with the
appropriate endpoints:

```yaml
memory:
  vector_backend: "chromadb"          # or "pgvector"
  chroma_connection: "http://localhost:8000"
  pgvector_dsn: "postgresql://user:pass@localhost:5432/agi_memory"
  vector_episodic_collection: "agi_episodic"
  vector_semantic_collection: "agi_semantic"
```

If the configured backend cannot be initialised the orchestrator logs a warning
and reverts to the bundled file-backed stores, allowing the system to operate in
an offline-only mode.
