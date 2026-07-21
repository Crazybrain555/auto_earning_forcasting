#!/bin/sh
# Start the forecasting dashboard backend (creates the local venv on first run).
cd "$(dirname "$0")" || exit 1
python_bin="${PYTHON_BIN:-python3}"
if [ ! -x .venv/bin/uvicorn ]; then
  "$python_bin" -m venv .venv || exit 1
  .venv/bin/pip install -q -r requirements.txt || exit 1
fi
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8787}"
