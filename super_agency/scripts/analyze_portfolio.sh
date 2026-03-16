#!/usr/bin/env bash
set -e
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT="$SCRIPT_DIR/.."
python3 "$ROOT/agents/portfolio_intel.py"
