#!/usr/bin/env bash
set -euo pipefail

umask 0077

runner_root="${1:-}"
if [[ ! "$runner_root" =~ ^/[A-Za-z0-9_./-]+$ ]]; then
  echo "runner root must be a safe absolute path" >&2
  exit 2
fi

keep_count="${FORECAST_BACKUP_KEEP:-7}"
if [[ ! "$keep_count" =~ ^[0-9]+$ ]] || (( keep_count < 1 )); then
  echo "FORECAST_BACKUP_KEEP must be a positive integer" >&2
  exit 2
fi

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"$script_dir/create_replica_bundle.sh" "$runner_root"

# Keep only the newest bundles; other files in backups/ are left untouched.
backups_dir="$runner_root/backups"
ls -1t "$backups_dir"/replica-export-*.tar.gz 2>/dev/null \
  | tail -n +"$((keep_count + 1))" \
  | while IFS= read -r stale; do
      rm -f -- "$stale"
    done

# Failed exports leave work directories behind; clear the ones older than a day.
find "$backups_dir" -maxdepth 1 -type d -name '.replica-export.*' -mtime +0 \
  -exec rm -rf -- {} +
