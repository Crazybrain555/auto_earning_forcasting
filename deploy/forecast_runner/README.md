# Forecast Ops 云端 Runner

这个目录描述可替换的计算节点，不把 AWS、区域、IP 或个人目录写进业务代码。Sites 负责生产入口、API、D1/R2 和命令队列；Runner 只领取受权命令、按所选引擎执行 `claude -p` 或 `codex exec`、校验结果并回传。Git 是代码事实源，Runner 磁盘是可恢复的执行工作区，本地电脑仅用于开发、测试和只读备份。

## 部署参数

- `RUNNER_HOST`：SSH 别名或主机名。
- `RUNNER_ROOT`：Runner 独占的绝对目录。
- `RUNNER_RSYNC_PATH`：远端以专用用户执行的 rsync 命令；默认 `rsync`。
- `RUNNER_USER`：无 sudo 的专用服务用户。
- `BACKEND_ENV_FILE`：只含后端/MCP所需非桥接配置的环境文件。
- `BRIDGE_ENV_FILE`：只含 Sites URL 和桥接令牌的 0600 环境文件。

服务模板不包含云厂商信息。更换服务器时只修改这组部署参数、重新完成 Claude/Codex/Git 登录并恢复 Sites 数据，不改应用路由、队列协议或预测方法。

## 当前部署 profile

下面是**唯一随生产服务器迁移而更新的说明区块**。其他 README 和业务代码只引用它，不重复保存主机身份。

<!-- ACTIVE-RUNNER-PROFILE:START -->
```text
RUNNER_PROVIDER=AWS
RUNNER_REGION=Singapore (ap-southeast-1)
RUNNER_HOST=aws-sg
RUNNER_ROOT=/srv/forecast-ops-runner
RUNNER_USER=forecastops
BACKEND_ENV_FILE=/etc/forecast-ops-runner/backend.env
BRIDGE_ENV_FILE=/etc/forecast-ops-runner/bridge.env
```

`RUNNER_HOST` 使用 SSH 配置中的可替换别名。README 不记录公网 IP、令牌或登录文件。
<!-- ACTIVE-RUNNER-PROFILE:END -->

### 更换服务器

迁移到别的云厂商、区域或主机时：

1. 排空命令队列，并保证旧桥与新桥不会同时运行。
2. 在新机器创建独立无 sudo 服务用户和独占目录。
3. 只更新上面的 active profile，以及两个未纳入 Git 的环境文件。
4. 重新执行安全同步、`bootstrap.sh` 和 systemd 渲染；不要复制虚拟环境、系统二进制或 Mac 的 Claude/Codex 登录文件。
5. 在新 Runner 上分别完成 Claude 订阅登录、Codex ChatGPT 设备登录和 Git 授权。
6. 从 Sites D1/R2 恢复并校验生产数据；完整迁移完成前，使用最新一致性备份恢复。
7. 验证后停止旧桥，等待旧租约失效，再启动新桥并更新本区块。

服务器迁移不会改变三条权威边界：Git 管代码，Sites D1/R2 管生产数据，Runner 只负责计算和可恢复缓存。

## 安全边界

- Runner 使用专用无 sudo 用户，不能读取并列服务目录。
- FastAPI 只监听 `127.0.0.1:8787`，安全组和 Nginx 均不开放该端口。
- `codex exec --dangerously-bypass-approvals-and-sandbox` 只能在 Runner 独占目录中运行。
- Claude 与 Codex 的订阅登录都在 Runner 上独立完成，不得从 Mac 复制，也不得进入 Git、D1、R2、日志或备份；Codex 登录使用 Runner 自己的 `CODEX_HOME`。
- 后端和桥使用两个环境文件，防止 Claude/Codex 子进程继承 Sites 桥接令牌。
- Sites 写操作必须通过 ChatGPT 身份和服务端邮箱允许列表；公开读取不等于公开执行。
- Mac 桥与云端桥绝不同时运行。切换前先停旧桥并等待租约窗口结束。

## 构建环境

在已经同步的 Runner 目录中，以服务用户执行：

```bash
deploy/forecast_runner/bootstrap.sh "$RUNNER_ROOT"
```

脚本在项目的 `.runtime/` 内安装 uv、yt-dlp、Deno，以及固定版本的 Claude Code 和 Codex，在项目目录内从 `uv.lock` 与两个 `package-lock.json` 重建依赖；不会修改系统级 Node 或其他服务环境。

## 环境、Git 与 MCP 对齐

“与本地同步”指功能、版本约束、代码和配置接口一致，而不是复制 Mac 二进制、虚拟环境或个人凭据：

- Python 使用项目声明的 3.13，并从 `uv.lock` 重建根环境；后端使用独立虚拟环境。
- Node 使用兼容的 Linux LTS 版本，并从 Site 与 YouTube MCP 的 `package-lock.json` 执行 `npm ci`。
- Claude Code 与 Codex CLI 均锁定为已验证的项目版本。Claude 使用 `-p` 无交互执行并在 Runner 上单独完成订阅登录；Codex 使用 ChatGPT 订阅单独完成设备登录，不要求 `OPENAI_API_KEY`。
- 应用代码、Site 代码和预测方法都记录确切 Git commit。正常更新只拉取经过测试的 commit；首次迁移脏工作树是一次性例外，必须额外记录 HEAD 与差异哈希。
- 项目 MCP 保持 `edgartools`、`arxiv`、`youtube-transcript` 三项，继续使用仓库内相对启动脚本与锁文件。预测 Skill 继续从 `forecasting-skills/` 建立项目内链接。
- 不复制 Computer Use、桌面浏览器、Mac 应用路径、浏览器 cookies、用户级插件缓存、`~/.ssh` 或 `auth.json`。这些内容既不可移植，也不属于生产计算依赖。

训练流程需要按项目规则提交和推送预测方法，因此 Runner 的 Git 写权限只授予对应方法仓库；其他仓库使用最小必要权限。

## 同步代码

同步默认仅预览：

```bash
RUNNER_HOST="$RUNNER_HOST" \
RUNNER_ROOT="$RUNNER_ROOT" \
deploy/forecast_runner/sync_to_runner.sh --dry-run
```

确认清单后才显式使用 `--apply`。同步不使用删除模式，并排除密钥、环境文件、Codex 登录、虚拟环境、依赖目录、缓存、构建结果、浏览器数据和 SQLite 活跃 WAL/SHM。数据库须另用 SQLite `.backup` 生成一致副本后传输。

长期更新应由 Git 拉取经过测试的确定提交；首次迁移为了保留当前三个脏工作树，会记录各自 HEAD 和差异哈希后做一次受控镜像。训练任务运行期间禁止自动 `git pull`。

## 本地只读生产副本

Mac 不再领取生产命令，也不向 Sites 上传快照；需要用真实生产数据调试时，从 Runner 拉取一个经过校验的版本化副本。命令默认只预览，不连接服务器：

```bash
deploy/forecast_runner/pull_replica.sh
```

确认当前 profile 后显式拉取：

```bash
deploy/forecast_runner/pull_replica.sh --apply
```

Runner 会使用 SQLite `.backup` 在线生成一致性数据库，并把 `training-runs/`、安全的 `backend/state/` 文件和任务 JSON 一并打包；环境文件、Codex 登录、桥令牌、任务日志、缓存与依赖均不进入副本。Mac 会依次验证压缩包 SHA-256、逐文件校验和及 SQLite 完整性，然后把新版本安装到 `replica/snapshots/<snapshot-id>/`，最后原子切换 `replica/current`。旧快照保留，拉取失败不会替换当前版本。

用副本启动本地仪表盘：

```bash
PORT=8792 backend/run-replica.sh
```

这会把所有读取和本地测试写入限定在 `replica/current` 指向的可丢弃副本中，不会回传生产。需要临时查看旧版本时，不必改动 `current`：

```bash
FORECAST_REPLICA_CURRENT="$PWD/replica/snapshots/<snapshot-id>" \
PORT=8792 backend/run-replica.sh
```

代码仍通过 Git 同步，数据只走 `AWS/Sites → Mac`。`sync_to_runner.sh` 明确排除整个 `replica/`，防止本地调试数据被误传回 Runner。完整 D1/R2 主数据迁移后，保留上述本地命令和目录协议，只替换服务端导出来源。

## systemd

生成单位文件：

```bash
python3 deploy/forecast_runner/render_units.py \
  --runner-root "$RUNNER_ROOT" \
  --backend-env-file "$BACKEND_ENV_FILE" \
  --bridge-env-file "$BRIDGE_ENV_FILE" \
  --output-dir /tmp/forecast-ops-units \
  --runner-user "$RUNNER_USER"
```

安装后先只启动后端并验证 `/api/health`。只有当 ChatGPT 身份头与 `FORECAST_CONTROL_EMAILS` 服务端允许列表已经部署、本地桥已停止且旧租约已过期，才启动 `forecast-sites-bridge.service`。

## 定时备份与最小监控

代码由 Git 保管；生产数据依靠两层定时任务加一个看门狗：

1. **Runner 每日自动打包**：`forecast-replica-backup.timer`（UTC 19:00，即北京时间 03:00）以服务用户运行
   `deploy/forecast_runner/scheduled_backup.sh`，在 `$RUNNER_ROOT/backups/` 生成经一致性校验的
   `replica-export-*.tar.gz`，并只保留最近 `FORECAST_BACKUP_KEEP`（默认 7）份。安装：先按下节渲染单位文件，然后

   ```bash
   sudo cp /tmp/forecast-ops-units/forecast-replica-backup.service \
     /tmp/forecast-ops-units/forecast-replica-backup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now forecast-replica-backup.timer
   ```

2. **本地每日异地副本**：操作机用 launchd/cron 定时运行 `deploy/forecast_runner/pull_and_prune.sh`
   （内部调用 `pull_replica.sh --apply`），本地保留最近 `FORECAST_REPLICA_KEEP`（默认 14）个快照，
   永不删除 `replica/current` 指向的快照。

3. **看门狗**：`deploy/forecast_runner/watchdog.py --site-url <站点URL> --replica-current <项目>/replica/current --notify`
   检查桥心跳、快照新鲜度与本地副本年龄，失败时非零退出并在 macOS 弹出通知；建议每 30 分钟一次。

`sync_to_runner.sh` 只同步代码，明确排除 `training-runs/`、`backend/jobs/`、`backend/state/` 与整个 `replica/`：
生产状态的权威在 Runner/Sites，数据只经 `pull_replica.sh` 单向回流本地。

## 数据与恢复

目标权威边界：

- 应用和方法代码：Git。
- 生产控制状态、任务记录和结构化索引：Sites D1。
- 报告、模型和不可变运行包：Sites R2。
- Runner：执行缓存和上传失败 outbox。
- 本地：`Sites → 本地` 单向校验副本；不会自动回写生产。

当前桥只同步安全快照和 Excel 模型，完整 D1/R2 主数据迁移完成前，Runner 工作区仍需保留一致性备份。不能把“执行器已搬到云端”误写成“Sites 已经保存全部生产数据”。
