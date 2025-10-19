# AGI Codex

AGI Codex is a modular autonomous agent scaffold designed to operate as a background service on Ubuntu systems. It combines orchestration, memory, tool usage, and learning subsystems to enable proactive assistance and continual improvement.

## Features
- Multi-agent architecture with planner, executor, verifier, and safety guards
- Persistent episodic, semantic, and procedural memory stores
- Tool plugin framework with sandboxed terminal and file I/O tools
- Telemetry collection and autonomous task proposals
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

## Project Structure
- `src/agi_core/`: Python package containing orchestration, reasoning, memory, tools, and system modules.
- `config/`: YAML configuration files.
- `systemd/`: Systemd unit templates.
- `webui/`: Static assets for placeholder web dashboard.
- `docs/`: Documentation, including architecture overview.

## Roadmap
Phase 1 delivers scaffolding and baseline autonomy. Future phases will expand the learning pipeline, integrate advanced tool plugins, and refine self-optimization loops.
