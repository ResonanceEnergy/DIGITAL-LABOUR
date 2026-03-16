#!/usr/bin/env bash
# Usage: ./propose.sh <repo> <action> <autonomy> <risk> "Description"
set -e
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT="$SCRIPT_DIR/.."
python3 "$ROOT/agents/council.py" propose --repo "$1" --action "$2" --autonomy "${3:-L1}" --risk "${4:-MEDIUM}" --description "$5"
