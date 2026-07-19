#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
data_dir="$project_root/.cache/edgar"

mkdir -p "$data_dir"
# SEC requires a real identity for EDGAR API requests; ":-" also covers the
# empty string passed through from .mcp.json when the shell env is unset.
export EDGAR_IDENTITY="${EDGAR_IDENTITY:-Yuye Zhang zhangyuye555@gmail.com}"
export XDG_CACHE_HOME="$project_root/.cache/xdg"
export EDGAR_LOCAL_DATA_DIR="$data_dir"
export EDGARTOOLS_DATA_DIR="$data_dir"

exec "$project_root/.venv/bin/edgartools-mcp"
