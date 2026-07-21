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
