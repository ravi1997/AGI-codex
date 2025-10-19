"""CLI entrypoint for AGI system."""
from __future__ import annotations

import argparse

from .config import load_config
from .orchestration.agent_kernel import AgentKernel


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
    args = parser.parse_args()

    config = load_config(args.config)
    agent = AgentKernel(config)

    if args.once:
        agent.run_once()
    else:
        agent.run_forever()


if __name__ == "__main__":
    main()
