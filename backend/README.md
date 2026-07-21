# Forecasting dashboard backend

生产部署中，这个 FastAPI 服务运行在可替换的云端 Runner 内，只监听 Runner 的 `127.0.0.1:8787`。Sites 是用户入口和云端控制/数据平面；Runner 桥只通过 localhost 调用 FastAPI，FastAPI 不向浏览器或公网暴露。当前服务器 profile 与通用替换步骤见 `../deploy/forecast_runner/README.md`。

FastAPI service the leadership dashboard calls. It has exactly three powers:

1. **Read** the Runner 工作区中的 `training-runs/` case tree and the skills git repo (per-company results, method-evolution timeline, live status).
2. **Write one file**: `training-runs/control.json` — the pause/resume switch training sessions obey.
3. **Launch/stop agent jobs**: spawn a headless agent to run a live forecast, one training case, or a full autonomous training round. Local and hosted consoles both expose Claude and Codex when the corresponding Runner executable is installed and authenticated. Both resolve to the same canonical forecasting method through the project skill links; engine-specific CLI settings stay in `config.json`.

这些文件系统能力是当前过渡期的执行接口，不表示 `training-runs/` 是长期生产事实源；完整迁移后，结构化状态以 Sites D1 为准，报告与模型工件以 Sites R2 为准。

## Run

```bash
backend/run.sh          # first run creates backend/.venv and installs fastapi+uvicorn
# -> http://127.0.0.1:8787   (PORT=xxxx backend/run.sh to change)
```

用最近一次从生产 Runner 拉取并校验过的数据副本进行本地调试：

```bash
deploy/forecast_runner/pull_replica.sh --apply
PORT=8792 backend/run-replica.sh
```

`run-replica.sh` 只把 runs、job JSON 和 SQLite 路径改到 `replica/current`；原有本地工作树不受影响，副本中的测试写入也不会上传 AWS 或 Sites。拉取命令、快照回看和单向同步边界见 `../deploy/forecast_runner/README.md`。

API reference for the frontend: `API.md`.

The same port also serves the **local development dashboard** (`webapp/` at the project
root, mounted at `/`): four Chinese-language views — 投资组合 (per-company
results with causal/value model, report and model download), 方法体系
(the canonical ten-stage method and git evolution), 训练控制, and 运行任务
(pause switch, dual-engine job launcher and live logs). Pure static
HTML/JS, no build step, works offline for development, testing, and presentations. It is not the production user entry point.

## Layout

- `config.json` — deployment config: paths, engines, prompt templates. This is the deployment layer; nothing here belongs in the skills repo.
- `app/` — service code (`data` runs-tree reader, `method` git timeline, `control` pause switch, `jobs` engine/job manager, `main` routes).
- `jobs/` — job records (`<id>.json`) and full logs (`<id>.log`). Gitignore-grade artifacts；只能在确认保留策略、归档和一致性备份后清理旧记录。

## Security notes

- Binds to 127.0.0.1 only; no auth. Do not expose the port beyond localhost. Production authorization belongs to the Sites API before a command enters the queue.
- Run production with the dedicated account named by the active Runner profile and separate backend/bridge environment files. The backend environment must never contain Sites bridge or ingest secrets because spawned Codex processes inherit the backend environment.
- The configured headless engines run with unattended permissions (`claude -p --permission-mode bypassPermissions` or `codex exec --dangerously-bypass-approvals-and-sandbox`) so research/training rounds are not blocked by prompts. A launched job can therefore edit files and run commands in this project like an unattended operator. Tighten the engine arguments in `config.json` if a less autonomous deployment is required.
- Codex is deliberately launched without the stale localhost proxy variables recorded in older notes; the current direct configuration is the tested path.
- Jobs run with cwd = project root. Codex reads `AGENTS.md`; Claude reads `CLAUDE.md`. Both files describe runs root, control.json, and the “skills repo only via git” boundary.

## Smoke test

```bash
PYTHONPATH=backend/.venv/lib/python3.13/site-packages python -m pytest -q backend/tests
FORECAST_BACKEND_CONFIG=/tmp/test-config.json backend/.venv/bin/uvicorn app.main:app --port 8791
curl -s http://127.0.0.1:8791/api/health
```
