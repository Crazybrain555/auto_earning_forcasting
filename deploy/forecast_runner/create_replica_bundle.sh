#!/usr/bin/env bash
set -euo pipefail

umask 0077

runner_root="${1:-}"
if [[ ! "$runner_root" =~ ^/[A-Za-z0-9_./-]+$ ]]; then
  echo "runner root must be a safe absolute path" >&2
  exit 2
fi

for command_name in rsync sqlite3 tar sha256sum; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is required" >&2
    exit 2
  fi
done

database="$runner_root/backend/state/forecast.db"
if [[ ! -f "$database" ]]; then
  echo "forecast database is missing: $database" >&2
  exit 1
fi

backups_dir="$runner_root/backups"
mkdir -p "$backups_dir"
work_dir="$(mktemp -d "$backups_dir/.replica-export.XXXXXX")"
payload_dir="$work_dir/payload"
snapshot_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
bundle_path="$backups_dir/replica-export-$snapshot_id.tar.gz"

cleanup() {
  rm -rf "$work_dir"
}
trap cleanup EXIT HUP INT TERM

mkdir -p \
  "$payload_dir/training-runs" \
  "$payload_dir/backend/state" \
  "$payload_dir/backend/jobs"

if [[ -d "$runner_root/training-runs" ]]; then
  rsync -a \
    --exclude='.DS_Store' \
    --exclude='.env*' \
    "$runner_root/training-runs/" \
    "$payload_dir/training-runs/"
fi

if [[ -d "$runner_root/backend/state" ]]; then
  # evidence/ holds content-addressed original bytes already present inside the
  # bundled case workspaces; the pg_dump below carries the store metadata.
  rsync -a \
    --exclude='.DS_Store' \
    --exclude='.env*' \
    --exclude='*.db' \
    --exclude='*.db-*' \
    --exclude='evidence/' \
    "$runner_root/backend/state/" \
    "$payload_dir/backend/state/"
fi

if [[ -d "$runner_root/backend/jobs" ]]; then
  rsync -a \
    --include='*/' \
    --include='*.json' \
    --exclude='*' \
    "$runner_root/backend/jobs/" \
    "$payload_dir/backend/jobs/"
fi

sqlite3 "$database" ".backup '$payload_dir/backend/state/forecast.db'"
integrity="$(sqlite3 "$payload_dir/backend/state/forecast.db" 'PRAGMA integrity_check;')"
if [[ "$integrity" != "ok" ]]; then
  echo "replica database integrity check failed: $integrity" >&2
  exit 1
fi

# Evidence store metadata (PostgreSQL). Soft-fail while hosts are still being
# provisioned, but always say so - a silent gap here would hide broken backups.
if command -v pg_dump >/dev/null 2>&1; then
  evidence_dsn="${FORECAST_EVIDENCE_DSN:-postgresql:///forecast_evidence}"
  if ! pg_dump --dbname="$evidence_dsn" --format=custom \
      --file="$payload_dir/backend/state/evidence.pgdump" 2>/dev/null; then
    rm -f "$payload_dir/backend/state/evidence.pgdump"
    echo "WARNING: evidence pg_dump failed or database missing; bundle has no evidence-store backup" >&2
  fi
else
  echo "WARNING: pg_dump not installed; bundle has no evidence-store backup" >&2
fi

root_commit="$(git -C "$runner_root" rev-parse HEAD 2>/dev/null || printf 'unknown')"
site_commit="$(git -C "$runner_root/sites/forecast-ops-console" rev-parse HEAD 2>/dev/null || printf 'unknown')"
file_count="$(find "$payload_dir" -type f | wc -l | tr -d ' ')"
size_bytes="$(du -sk "$payload_dir" | awk '{print $1 * 1024}')"
created_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

printf '%s\n' \
  '{' \
  '  "schema_version": "forecast-replica/v1",' \
  "  \"snapshot_id\": \"$snapshot_id\"," \
  "  \"created_at\": \"$created_at\"," \
  "  \"root_commit\": \"$root_commit\"," \
  "  \"site_commit\": \"$site_commit\"," \
  "  \"file_count_before_manifest\": $file_count," \
  "  \"size_bytes_before_manifest\": $size_bytes" \
  '}' \
  > "$payload_dir/manifest.json"

(
  cd "$payload_dir"
  find . -type f ! -name CHECKSUMS.sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum \
    > CHECKSUMS.sha256
)

tar -C "$payload_dir" -czf "$bundle_path" .
chmod 600 "$bundle_path"
archive_sha256="$(sha256sum "$bundle_path" | awk '{print $1}')"

printf 'SNAPSHOT_ID=%s\n' "$snapshot_id"
printf 'BUNDLE_PATH=%s\n' "$bundle_path"
printf 'SHA256=%s\n' "$archive_sha256"
