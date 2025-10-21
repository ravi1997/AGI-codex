"""CLI entrypoint for AGI system."""
from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .orchestration.agent_kernel import AgentKernel
from .web.server import run_web


def main() -> None:
    parser = argparse.ArgumentParser(description="AGI Core Service")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single iteration instead of continuous loop",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the web UI and WebSocket bridge instead of CLI loop",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host for the web server (when --web is used)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for the web server (when --web is used)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # Ensure essential directories exist
    for p in [
        config.tools.sandbox_root,
        config.memory.episodic_db_path.parent,
        config.memory.semantic_db_path.parent,
        config.memory.procedural_repo_path,
        config.learning.feedback_path.parent,
        config.learning.dataset_path.parent,
        config.learning.training_output_dir,
        config.learning.training_metadata_path.parent,
    ]:
        Path(p).mkdir(parents=True, exist_ok=True)

    if args.web and not args.once:
        static_dir = Path(__file__).resolve().parents[2] / "webui"
        run_web(config, static_dir=static_dir, host=args.host, port=args.port)
        return

    agent = AgentKernel(config)

    try:
        if args.once:
            agent.run_once()
        else:
            agent.run_forever()
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
