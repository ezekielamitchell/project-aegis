#!/usr/bin/env bash
# Launch the AEGIS pipeline.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
exec python -m aegis.main --config configs/default.yaml "$@"
