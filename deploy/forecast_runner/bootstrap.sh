#!/usr/bin/env bash
set -euo pipefail
umask 0027

runner_root="${1:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}"
runtime_dir="$runner_root/.runtime"
bootstrap_venv="$runtime_dir/bootstrap"

if [[ ! -f "$runner_root/pyproject.toml" || ! -f "$runner_root/uv.lock" ]]; then
  echo "runner root does not contain the project lockfiles" >&2
  exit 2
fi

mkdir -p "$runtime_dir" "$runner_root/home" "$runner_root/codex-home" "$runner_root/github"
chmod 700 "$runner_root/home" "$runner_root/codex-home" "$runner_root/github"

python3 -m venv "$bootstrap_venv"
"$bootstrap_venv/bin/pip" install --disable-pip-version-check --quiet "uv==0.10.2" "yt-dlp==2026.7.4"
export PATH="$runtime_dir/codex/node_modules/.bin:$runtime_dir/tools/node_modules/.bin:$bootstrap_venv/bin:$PATH"

cd "$runner_root"
uv python install 3.13
uv sync --frozen --python 3.13

if [[ ! -x "$runner_root/backend/.venv/bin/python" ]]; then
  uv venv --python 3.13 "$runner_root/backend/.venv"
fi
uv pip install --python "$runner_root/backend/.venv/bin/python" -r "$runner_root/backend/requirements.txt"
uv pip install --python "$runner_root/backend/.venv/bin/python" "pytest==9.0.3"

npm install --prefix "$runtime_dir/codex" --no-save "@openai/codex@0.144.6"
npm install --prefix "$runtime_dir/tools" --no-save \
  "deno@2.9.3" \
  "@anthropic-ai/claude-code@2.1.110"

cd "$runner_root/sites/forecast-ops-console"
npm ci

cd "$runner_root/scripts/mcp/youtube-transcript-mcp"
npm ci
npm run build

mkdir -p "$runner_root/.agents/skills"
ln -sfn ../../forecasting-skills/technology-company-profit-forecasting \
  "$runner_root/.agents/skills/technology-company-profit-forecasting"
ln -sfn ../../forecasting-skills/technology-company-forecasting-trainer \
  "$runner_root/.agents/skills/technology-company-forecasting-trainer"

chmod -R o-rwx "$runner_root"

codex --version
claude --version
"$runner_root/.venv/bin/python" --version
node --version
