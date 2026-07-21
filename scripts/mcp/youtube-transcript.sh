#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
server_dir="$script_dir/youtube-transcript-mcp"
cache_dir="$project_root/.cache/youtube-transcripts"

for required_command in node yt-dlp deno; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    echo "youtube-transcript MCP requires '$required_command' on PATH." >&2
    exit 1
  fi
done

if [[ ! -f "$server_dir/dist/index.js" || ! -d "$server_dir/node_modules" ]]; then
  echo "youtube-transcript MCP is not built. Run: cd '$server_dir' && npm ci && npm run build" >&2
  exit 1
fi

mkdir -p "$cache_dir"
export YOUTUBE_TRANSCRIPT_CACHE_DIR="${YOUTUBE_TRANSCRIPT_CACHE_DIR:-$cache_dir}"
export YOUTUBE_MCP_MAX_CONTENT_CHARS="${YOUTUBE_MCP_MAX_CONTENT_CHARS:-200000}"
export YOUTUBE_MCP_TIMEOUT_MS="${YOUTUBE_MCP_TIMEOUT_MS:-180000}"

exec node "$server_dir/dist/index.js"
