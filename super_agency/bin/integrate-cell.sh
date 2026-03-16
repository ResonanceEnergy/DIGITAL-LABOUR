#!/usr/bin/env bash
# convenience wrapper for agents/integrate_cell.py
# usage: ./bin/integrate-cell.sh --repo NAME [--org ORG] [--clone]
set -e
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT="$SCRIPT_DIR/.."
python3 "$ROOT/agents/integrate_cell.py" "$@"
