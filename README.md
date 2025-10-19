# AGI Codex

AGI Codex is a modular autonomous agent scaffold designed to operate as a background service on Ubuntu systems. It combines orchestration, memory, tool usage, and learning subsystems to enable proactive assistance and continual improvement. The Phase 2 release deepens autonomy with contextual planning, telemetry-aware tooling, and richer memory capture loops.

## Features
- Multi-agent architecture with planner, executor, verifier, and safety guards
- Context builder that retrieves relevant memories and deterministic embeddings for planning
- Persistent episodic, semantic, and procedural memory stores with automatic outcome logging
- Tool plugin framework with sandboxed terminal, file I/O, and telemetry monitor tools
- Telemetry collection and autonomous task proposals with failure remediation loops
- Feedback analytics that track success metrics and adjust autonomous scheduling heuristics
- Learning pipeline that writes JSONL experience datasets for downstream LoRA/DPO fine-tuning
- Deployment options via systemd or Docker Compose

## Getting Started

### Prerequisites
- Ubuntu 20.04+ (x86_64 or ARM64)
- Python 3.10+
- Git

### Installation
```bash
./install.sh
source .venv/bin/activate
agi-core --once
```

### Development Scripts
- `install.sh`: Create virtual environment and install package locally.
- `bootstrap.sh`: Bootstrap environment and run a single agent iteration.
- `setup.py`: Python packaging entrypoint.

### Running as a Service
1. Copy `systemd/agi-core.service` to `~/.config/systemd/user/` (or `/etc/systemd/system/`).
2. Adjust `WorkingDirectory` and `ExecStart` paths as needed.
3. Reload systemd and enable the service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable agi-core
   systemctl --user start agi-core
   ```

### Docker Compose
```bash
docker compose up --build
```

### Configuration
Default configuration resides in `config/default.yaml`. Override by passing `--config` to `agi-core`.

Key sections include:

- `memory`: File locations for episodic, semantic, and procedural stores.
- `tools`: Sandbox permissions for terminal and file I/O tooling.
- `scheduler`: Task concurrency, autonomous cadence, and idle sleep duration.
- `logging`: Log level and directory paths.
- `learning`: Feedback history size, dataset export path, and optimization thresholds.

### Learning Outputs
- Feedback analytics persist to `storage/analytics/feedback.json` and track success rates over time.
- Fine-tuning datasets accumulate in `storage/learning/dataset.jsonl` (JSONL format) to bootstrap LoRA/DPO pipelines.

## Project Structure
- `src/agi_core/`: Python package containing orchestration, reasoning, memory, tools, and system modules.
- `config/`: YAML configuration files.
- `systemd/`: Systemd unit templates.
- `webui/`: Static assets for placeholder web dashboard.
- `docs/`: Documentation, including architecture overview.

## Roadmap
Phase 1 delivered the scaffolding and baseline autonomy. Phase 2 adds contextual planning, telemetry-driven tooling, automatic memory capture, and follow-up task generation for failed runs. Future phases will expand the learning pipeline, integrate advanced tool plugins, and refine self-optimization loops.
