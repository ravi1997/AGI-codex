#!/usr/bin/env bash
set -euo pipefail

if [ ! -d .venv ]; then
  ./install.sh
fi

source .venv/bin/activate
python -m agi_core.app --once
