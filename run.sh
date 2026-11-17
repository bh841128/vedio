#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONUNBUFFERED=1
PORT="${PORT:-8000}"
echo "Starting vedio backend on port ${PORT} (MOCK_MODE=${MOCK_MODE:-1})"
exec python3 -m backend
