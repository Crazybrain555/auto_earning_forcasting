#!/usr/bin/env bash
set -euo pipefail

# Pull a fresh verified replica from the runner, then prune old local
# snapshots. The snapshot replica/current points to is never deleted.
# Usage: pull_and_prune.sh [keep_count]   (env: FORECAST_REPLICA_KEEP, default 14)

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"

keep_count="${1:-${FORECAST_REPLICA_KEEP:-14}}"
if [[ ! "$keep_count" =~ ^[0-9]+$ ]] || (( keep_count < 1 )); then
  echo "keep count must be a positive integer" >&2
  exit 2
fi

# One pull at a time, across the dashboard, cron, and manual shells alike.
# mkdir is the portable atomic lock (macOS has no flock); a lock whose recorded
# pid is dead is stale (e.g. the backend was killed mid-pull) and is taken over.
lock_dir="$project_root/replica/.pull.lock"
mkdir -p "$project_root/replica"
if ! mkdir "$lock_dir" 2>/dev/null; then
  holder="$(cat "$lock_dir/pid" 2>/dev/null || true)"
  if [[ -n "$holder" ]] && kill -0 "$holder" 2>/dev/null; then
    echo "another pull is already running (pid $holder)" >&2
    exit 3
  fi
  rm -rf "$lock_dir"
  if ! mkdir "$lock_dir" 2>/dev/null; then
    echo "another pull grabbed the lock first" >&2
    exit 3
  fi
fi
printf '%s\n' "$$" > "$lock_dir/pid"
trap 'rm -rf "$lock_dir"' EXIT HUP INT TERM

"$script_dir/pull_replica.sh" --apply

snapshots_dir="$project_root/replica/snapshots"
current_target="$(readlink "$project_root/replica/current" 2>/dev/null || true)"
current_name="$(basename -- "${current_target:-none}")"

ls -1t "$snapshots_dir" 2>/dev/null \
  | tail -n +"$((keep_count + 1))" \
  | while IFS= read -r name; do
      if [[ "$name" == "$current_name" ]]; then
        continue
      fi
      rm -rf -- "${snapshots_dir:?}/$name"
    done
