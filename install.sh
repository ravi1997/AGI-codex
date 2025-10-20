#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
extras_suffix=""
if [[ "${AGI_CORE_INSTALL_VECTOR:-0}" == "1" ]]; then
  echo "Installing vector store extras"
  extras_suffix="[vector]"
fi

pip install -e ".${extras_suffix}"
