#!/bin/sh
set -eu

backend_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
project_root="$(CDPATH= cd -- "$backend_dir/.." && pwd)"
replica_current="${FORECAST_REPLICA_CURRENT:-$project_root/replica/current}"

if [ ! -d "$replica_current/training-runs" ] || \
   [ ! -f "$replica_current/backend/state/forecast.db" ]; then
  echo "No verified replica at $replica_current" >&2
  echo "Run deploy/forecast_runner/pull_replica.sh --apply first." >&2
  exit 1
fi

export FORECAST_RUNS_ROOT="$replica_current/training-runs"
export FORECAST_JOBS_DIR="$replica_current/backend/jobs"
export FORECAST_DB_PATH="$replica_current/backend/state/forecast.db"

exec "$backend_dir/run.sh"
