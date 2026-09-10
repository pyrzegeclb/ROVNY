#!/usr/bin/env sh
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ ! -x "$repo_root/.venv/bin/python" ]; then
  echo 'Run the README setup commands first.' >&2
  exit 1
fi
if [ ! -f "$repo_root/frontend/dist/index.html" ]; then
  echo 'Build frontend first: cd frontend && npm run build' >&2
  exit 1
fi
cd "$repo_root/backend"
exec "$repo_root/.venv/bin/python" -m rovny
