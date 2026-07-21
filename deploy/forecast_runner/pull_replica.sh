#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
runner_host="${RUNNER_HOST:-aws-sg}"
runner_root="${RUNNER_ROOT:-/srv/forecast-ops-runner}"
runner_user="${RUNNER_USER:-forecastops}"
replica_root="${REPLICA_ROOT:-$source_root/replica}"
mode="--dry-run"

if [[ "${1:-}" == "--apply" ]]; then
  mode="--apply"
elif [[ -n "${1:-}" && "${1:-}" != "--dry-run" ]]; then
  echo "usage: $0 [--dry-run|--apply]" >&2
  exit 2
fi

if [[ ! "$runner_host" =~ ^[A-Za-z0-9_.@-]+$ ]]; then
  echo "RUNNER_HOST contains unsafe characters" >&2
  exit 2
fi
if [[ ! "$runner_root" =~ ^/[A-Za-z0-9_./-]+$ ]]; then
  echo "RUNNER_ROOT must be a safe absolute path" >&2
  exit 2
fi
if [[ ! "$runner_user" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; then
  echo "RUNNER_USER is invalid" >&2
  exit 2
fi
if [[ "$replica_root" != /* ]]; then
  echo "REPLICA_ROOT must be absolute" >&2
  exit 2
fi

if [[ "$mode" == "--dry-run" ]]; then
  printf 'DRY RUN: pull production replica from %s:%s\n' "$runner_host" "$runner_root"
  printf 'Destination: %s/snapshots/<snapshot-id>\n' "$replica_root"
  printf 'No remote command, download, or local switch was performed. Use --apply explicitly.\n'
  exit 0
fi

for command_name in ssh tar sqlite3 python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is required" >&2
    exit 2
  fi
done

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

verify_checksums() {
  local snapshot_dir="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$snapshot_dir" && sha256sum -c CHECKSUMS.sha256)
  else
    (cd "$snapshot_dir" && shasum -a 256 -c CHECKSUMS.sha256)
  fi
}

ssh_args=(-o ProxyCommand=none -o BatchMode=yes -o ConnectTimeout=8)
remote_helper="$runner_root/deploy/forecast_runner/create_replica_bundle.sh"
remote_output="$(
  ssh "${ssh_args[@]}" "$runner_host" \
    "sudo -u $runner_user env --chdir='$runner_root' '$remote_helper' '$runner_root'"
)"

snapshot_id=""
bundle_path=""
expected_sha256=""
while IFS='=' read -r key value; do
  case "$key" in
    SNAPSHOT_ID) snapshot_id="$value" ;;
    BUNDLE_PATH) bundle_path="$value" ;;
    SHA256) expected_sha256="$value" ;;
  esac
done <<< "$remote_output"

if [[ ! "$snapshot_id" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9]+$ ]]; then
  echo "runner returned an invalid snapshot id" >&2
  exit 1
fi
if [[ "$bundle_path" != "$runner_root/backups/replica-export-$snapshot_id.tar.gz" ]]; then
  echo "runner returned an unexpected bundle path" >&2
  exit 1
fi
if [[ ! "$expected_sha256" =~ ^[0-9a-f]{64}$ ]]; then
  echo "runner returned an invalid SHA-256" >&2
  exit 1
fi

mkdir -p "$replica_root/snapshots"
local_temp="$(mktemp -d "${TMPDIR:-/tmp}/forecast-replica.XXXXXX")"
incoming="$replica_root/snapshots/.incoming-$snapshot_id"
local_bundle="$local_temp/replica.tar.gz"
next_link=""

cleanup() {
  rm -rf "$local_temp"
  if [[ -n "${incoming:-}" && -d "$incoming" ]]; then
    rm -rf "$incoming"
  fi
  if [[ -n "${next_link:-}" && -L "$next_link" ]]; then
    rm -f "$next_link"
  fi
}
trap cleanup EXIT HUP INT TERM

if [[ -e "$incoming" ]]; then
  echo "incoming snapshot path already exists: $incoming" >&2
  exit 1
fi
ssh "${ssh_args[@]}" "$runner_host" \
  "sudo -u $runner_user env --chdir='$runner_root' cat '$bundle_path'" \
  > "$local_bundle"

actual_sha256="$(sha256_file "$local_bundle")"
if [[ "$actual_sha256" != "$expected_sha256" ]]; then
  echo "replica archive SHA-256 mismatch" >&2
  exit 1
fi

mkdir "$incoming"
tar -C "$incoming" -xzf "$local_bundle"
verify_checksums "$incoming" >/dev/null
integrity="$(sqlite3 "$incoming/backend/state/forecast.db" 'PRAGMA integrity_check;')"
if [[ "$integrity" != "ok" ]]; then
  echo "local replica database integrity check failed: $integrity" >&2
  exit 1
fi

final_snapshot="$replica_root/snapshots/$snapshot_id"
if [[ -e "$final_snapshot" ]]; then
  echo "snapshot already exists: $final_snapshot" >&2
  exit 1
fi
mv "$incoming" "$final_snapshot"
incoming=""

if [[ -e "$replica_root/current" && ! -L "$replica_root/current" ]]; then
  echo "replica/current exists but is not a symlink" >&2
  exit 1
fi
next_link="$replica_root/.current-$snapshot_id"
if [[ -e "$next_link" || -L "$next_link" ]]; then
  echo "temporary current link already exists: $next_link" >&2
  exit 1
fi
ln -s "snapshots/$snapshot_id" "$next_link"
python3 -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' \
  "$next_link" "$replica_root/current"

ssh "${ssh_args[@]}" "$runner_host" \
  "sudo -u $runner_user env --chdir='$runner_root' rm -f '$bundle_path'"

printf 'Replica ready: %s\n' "$final_snapshot"
printf 'Current link: %s/current\n' "$replica_root"
