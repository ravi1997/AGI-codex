# AGI System Architecture

## System Overview
- **Purpose**: Persistent autonomous assistant operating as a background service on Ubuntu, capable of human-like reasoning, multi-modal interaction, and continual self-improvement.
- **Key Characteristics**:
  - Background execution via `systemd` or Docker Compose services.
  - Modular microservice-inspired design with clear separation of orchestration, perception, memory, tooling, and learning subsystems.
  - Multi-agent reasoning core combining planner, executor, verifier, and reflection agents.
  - Persistent memory layers (episodic, semantic, procedural) backed by vector and relational stores.
  - Secure permission and safety guardrails controlling tool access and user data handling.
  - Extensible plugin framework for new tools, sensors, and communication interfaces.

## Core Modules
1. **Orchestration Layer**
   - *Agent Kernel*: Coordinates planner/executor/verifier loop, manages context windows, and handles interrupts.
   - *Task Scheduler*: Maintains task queue, priority scoring, and autonomous task generation.
   - *Dialogue Manager*: Interfaces with CLI/web UI, handles reactive queries, session state, and multi-modal inputs.
2. **Reasoning & Planning Layer**
   - *Planning Agent*: Generates multi-step plans using chain/tree-of-thought reasoning and tool affordance graph.
   - *Execution Agent*: Invokes tool plugins, monitors progress, emits telemetry to memory subsystem.
   - *Verifier/Reflection Agent*: Evaluates outputs, detects failures, and triggers retries or refinements.
3. **Memory Layer**
   - *Episodic Store*: Recent interactions stored in vector DB (ChromaDB/pgvector) with recency decay.
   - *Semantic Store*: Curated knowledge base with embedding + metadata (PostgreSQL + pgvector).
   - *Procedural Store*: Repository of scripts, workflows, and automation policies versioned in Git.
   - *Memory Orchestrator*: Handles retrieval augmentation, consolidation, summarization, and memory hygiene.
4. **Tooling Layer**
   - *Terminal Tool*: Executes shell commands via sandbox with safety policies.
   - *File I/O Tool*: Reads/writes local files with audit logging.
   - *Browser Automation Tool*: Playwright/Selenium driver for web actions.
   - *API Tooling*: Generic REST/GraphQL client with credential vault integration.
   - *System Monitor Tool*: Collects CPU, memory, process metrics for self-optimization.
5. **Learning & Adaptation Layer**
   - *Feedback Collector*: Aggregates user ratings, implicit feedback, success metrics.
   - *Policy Updater*: Adjusts prompts, planner heuristics, and tool configuration based on feedback.
   - *Fine-tuning Pipeline*: LoRA/DPO training scripts for incremental model refinement (offline batch).
   - *Skill Discovery Module*: Detects repetitive tasks and proposes automation scripts.
6. **Infrastructure & Deployment**
   - *Service Manager*: systemd units and health checks ensuring uptime.
   - *Containerization*: Optional Docker images with Compose for multi-service deployment.
   - *Configuration Service*: Centralized settings via YAML/TOML with environment overrides.
   - *Logging & Observability*: Structured logging, OpenTelemetry traces, and alert hooks.

## Control Flow Cycle
1. **Perception & Input Gathering**
   - Accept user requests (CLI/web), scheduled tasks, and autonomous triggers (system events).
   - Retrieve relevant memories (episodic, semantic, procedural) and system telemetry.
2. **Deliberation & Planning**
   - Planner constructs task graph using tool affordances and constraints.
   - Verifier evaluates plan sanity; memory orchestrator augments context.
3. **Execution & Tool Use**
   - Executor dispatches plan steps to tool plugins with sandboxing.
   - Outputs streamed to dialogue manager and logged for monitoring.
4. **Reflection & Learning**
   - Verifier checks outcomes, triggers corrective actions, and records lessons.
   - Memory orchestrator summarizes episodes, updates semantic/procedural stores.
   - Feedback collector updates metrics; policy updater adjusts configurations.
5. **Autonomous Task Generation**
   - Scheduler analyzes telemetry + habits to propose new tasks or optimizations.
   - Safety layer enforces permission checks before execution.

## Deployment Blueprint
- **Base OS**: Ubuntu 20.04+ (ARM64/x86_64 support).
- **Runtime Options**:
  - *Bare-metal*: Python virtualenv managed by `systemd` service `agi-core.service`.
  - *Containerized*: Docker Compose stack with services: `core`, `memory-db`, `vector-db`, `web-ui`, `learning-pipeline`.
- **Dependencies**:
  - Python 3.11 runtime, Poetry/virtualenv for package management.
  - PostgreSQL + pgvector extension or ChromaDB for embeddings.
  - Redis for task queue and pub/sub events.
  - Playwright with Chromium binaries for browser automation.
  - OpenTelemetry collector for metrics/log aggregation.
- **Security**:
  - Secrets managed via `.env` + optional Hashicorp Vault integration.
  - AppArmor/SELinux profiles for sandboxed tool execution.
  - Audit logging stored in `logs/` with retention policies.

## Phase 1 Delivery Plan
1. **Foundational Codebase**
   - Repository scaffold with `src/` modules for orchestration, memory, tooling, interfaces.
   - Configuration schema (`config/`) and default profiles.
   - Core agent loop with planner, executor, verifier stubs.
2. **Persistence Layer Setup**
   - Integration with SQLite + local ChromaDB for initial persistence (PostgreSQL optional later).
   - Memory orchestrator skeleton with CRUD operations.
3. **Tool Plugin Framework**
   - Base tool interface, command execution tool, file I/O tool.
4. **Deployment Scripts**
   - `install.sh`, `bootstrap.sh`, `setup.py`, and `systemd` unit templates.
   - Docker Compose skeleton for optional container deployment.
5. **Observability & Logging**
   - Structured logging utilities and basic telemetry collectors.
6. **Documentation**
   - Developer onboarding guide, architecture overview, runbooks.

Phase 1 focuses on scaffolding and minimal viable autonomy (task scheduling, basic reasoning loop). Subsequent phases will expand learning pipelines, advanced tool plugins, and self-optimization heuristics.
