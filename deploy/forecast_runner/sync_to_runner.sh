#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
runner_host="${RUNNER_HOST:-aws-sg}"
runner_root="${RUNNER_ROOT:-/srv/forecast-ops-runner}"
rsync_path="${RUNNER_RSYNC_PATH:-rsync}"
mode="--dry-run"

if [[ "${1:-}" == "--apply" ]]; then
  mode=""
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

ssh_command="ssh -o ProxyCommand=none -o BatchMode=yes -o ConnectTimeout=8"
rsync_args=(
  -az
  --links
  --no-perms
  --itemize-changes
  --include=.env.example
  "--exclude=.env*"
  --exclude=.venv
  "--exclude=*/.venv"
  --exclude=node_modules
  "--exclude=*/node_modules"
  --exclude=.cache
  "--exclude=*/.cache"
  --exclude=.pytest_cache
  "--exclude=*/.pytest_cache"
  --exclude=.next
  "--exclude=*/.next"
  --exclude=.wrangler
  "--exclude=*/.wrangler"
  --exclude=dist
  "--exclude=*/dist"
  --exclude=.playwright-mcp
  --exclude=/replica
  # Production state lives on the runner; code sync must never overwrite it.
  --exclude=/training-runs
  --exclude=/backend/jobs
  --exclude=/backend/state
  --exclude=.claude/settings.local.json
  "--exclude=.git/sg-hook*"
  "--exclude=*/__pycache__"
  "--exclude=*.pyc"
  --exclude=auth.json
  "--exclude=*/auth.json"
  "--exclude=*.db"
  "--exclude=*.db-wal"
  "--exclude=*.db-shm"
  --exclude=.DS_Store
  --exclude=pkcs11.txt
  --exclude=validator_stderr.txt
  --exclude=.agents/skills/ai-hardware-forecasting
  --rsync-path="$rsync_path"
  -e "$ssh_command"
)
if [[ -n "$mode" ]]; then
  rsync_args+=("$mode")
fi

rsync "${rsync_args[@]}" "$source_root/" "$runner_host:$runner_root/"
