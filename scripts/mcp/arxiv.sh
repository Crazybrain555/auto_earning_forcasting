#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
paper_dir="$project_root/.cache/arxiv-papers"

mkdir -p "$paper_dir"
export XDG_CACHE_HOME="$project_root/.cache/xdg"
export HF_HOME="$project_root/.cache/huggingface"
export SENTENCE_TRANSFORMERS_HOME="$project_root/.cache/sentence-transformers"
export TORCH_HOME="$project_root/.cache/torch"

exec "$project_root/.venv/bin/arxiv-mcp-server" --storage-path "$paper_dir"
