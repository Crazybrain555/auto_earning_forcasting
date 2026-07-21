# HANDOFF — 多 skill 预测系统改造（数据库先行 + 系统瘦身）

> 更新规则：每个 session 结束或完成一个里程碑时更新本文件；只写状态与指针，不复制大段内容；
> 绝不写入密钥/令牌/主机 IP。历史交接需要留档时改名为 `HANDOFF-<日期>.md` 再新建。
> 最后更新：2026-07-22 凌晨（方法 v11 财报拆解骨架三门全过并发布 `2cc0263`）。

## 一、使命与方向裁定（用户已拍板，后续 session 不得偏离）

1. **预测第一性**：一切改动以「更准确地预测营收/经营利润/GAAP 归母净利」为唯一目的；不追求指标好看，不做量化数据游戏。
2. **数据库先行**：所有获取过的数据按统一协议入库（初期尽可能简单有效），取过就存、复用优先、只补缺口。用户已授权安装 PostgreSQL（引擎选型见待办 #1 的决策点）。
3. **系统瘦身，检查只守底线**：检查占比过重=头重脚轻反模式。检查仅守：财务勾稽不能错、关键数据不能不查等底线；正确性主要靠 SOP 流程的合理构造（宪法第 2 条），不靠检测-修正循环。
4. **财报拆解方法论**（方法核心方向）：以历史财报勾稽为骨架，把关键科目拆细（收入→产品/客户/量价；量→供需；价→大宗/利率/供需/产品迭代），拆到能算清楚为止；不重要的按历史/经验估，重要的多方打磨；论文/观点只作查漏补缺的交叉验证，不当主线。不漫无目的套方法、找齐所有指标。
5. **流程要更清晰**：codex 写的部分可能过复杂，简化是合法目标（配合盲测防退化）。

## 二、当前状态（2026-07-21 晚）

- **skills 仓库**：`cf46400`（生产/训练边界拆分）已提交并推送；工作树干净。Trainer 测试 556 passed / 1 skipped。
  六维结构盲审通过，但**盈利预测准确率 not_established**，与旧版 24/30 的对照盲测未复验（待办 #7）。
- **root 仓库**：HEAD `7fc947c`（任务队列：满载排队、一公司一任务）。干净。
- **runner（aws-sg）**：skills=干净 cf46400（#6 已清理）；**方法已推进到 2cc0263，下个部署窗口在 runner 上 `git -C forecasting-skills pull` 即可**；backend 已同步重启（2026-07-21 深夜窗口）。
- **MRVL 事故（本次改造的直接动因）**：07-21 codex 首次实时预测（job 010e）跑 2h46m 后被部署重启杀死（`interrupted`）。
  事后复盘：研究 08:24Z 即完成，之后 1h44m 陷入「模型整合+严格校验+修复+全量重生成」循环；产出集中在一个 ~3300 行的
  `build_delivery.py`，每修一点全套重生成；估值红队发现 Q1 现金流重复计算的实质错误；日志膨胀到 132MB。
  10:30Z 有一次未经授权的重跑（606b，已停止）——教训已记：**重启/部署前必须确认无 running job 且经用户同意**。
- **日志证据**：132MB 原件在 runner `backend/jobs/20260721-074213-010e.log`；本地 gz 副本在本 session scratchpad
  `mrvl-logs/`（session 结束会消失）。重取命令：
  `ssh aws-sg "sudo -n -u forecastops gzip -c /srv/forecast-ops-runner/backend/jobs/20260721-074213-010e.log" > 010e.log.gz`。
  法证分析报告（进行中）将固化到 `docs/2026-07-21-mrvl-run-log-forensics.md`。
- **看板污染 bug 已定位**：`db.effective_valuation` 回退不查 sealed/delivery_passed，运行中草稿被当有效版本上板
  （MRVL 卡片 $85.83 事件）；v10 快照估值方言已改为 `fair_value_by_scenario_id`（可只估参考情景），backend 抽取器与
  webapp/Site 前端均未适配。
- **v10 的既有进展（别推倒重做）**：live 运行已实现每案例原件托管（`sources/raw/` 123MB SEC 原件）+ 全部真实
  sha256 content_hash——「入库」的身份键和 raw 托管已在案例内解决，缺的是**跨案例存储与回灌**。

## 三、待办清单（按用户优先级）

| # | 事项 | 状态 | 车道/入口 |
|---|------|------|-----------|
| 1 | **证据数据库**：统一协议入库/查询/回灌；实现 `forecasting-system-contracts/protocol_manifest.json` 已定义的 ports；训练读取强制 `available_at ≤ cutoff` + 快照定格 | **v1a ✅ 本机已落地**（PG=已决策）：`backend/app/evidence.py`（register/query/bind/ingest/stats + CLI）+ `evidence` schema 四表 + 4 项测试（临时 PG 集群 fixture，含 cutoff 红线与未封存拒收台账两道机制测试）；真实入库：被杀 MRVL 运行的 77 个原件已入库绑定。**剩余**：v1b scaffold 回灌（改 skills）、db.scan 自动 ingest 挂钩、backup/replica 接 pg_dump、runner 装 PG（并入 #6 窗口） | backend/ 为宿主；skill 侧只经 scaffold 回灌与交付 ingest（宪法 #4） |
| 2 | **MRVL 132MB 日志法证** → 系统缺陷清单 | ✅ 完成：报告在 `docs/2026-07-21-mrvl-run-log-forensics.md`（13 条缺陷分四类；关键数字：107 次单体重写=38.9% 日志、可见推理 0.01%、Q1 双计只被终局红队抓到）——#3 以此立项 | 只读分析 |
| 3 | **系统瘦身 + SOP 重构**：以「财报拆解」为核心重写方法主线 | **骨架已落地（未提交）**：method_system v11 十二阶段（新增 accounting_diagnosis、historical_statements；causal_graph 改根为科目拆解；value_creation 统一正常化命名）；research-sop/analysis-kernel 主线倒置；新 references/accounting-diagnosis.md；2 个转发 stub 删除；canonical_definitions 注册表+5 锚点；protocol stock_flow_attribution 不变量；schema/模板/stage_owners 同步。✅ **已发布 `2cc0263`（2026-07-22 凌晨）**：三重盲测门全过后按授权流程 commit/push：骨架 ✅ + 去重收敛 ✅（独立性/价值恒等式/三表清单→单一权威+指针，命名统一 owner-cash）+ 产业降级 ✅（横幅定位+driver-tree 历史基座迁移，净减 44 行）+ 训练研习阶段 ✅（同一 method_reflection 契约双触发器、五出处入册、不豁免盲测）。三门结果：B 六维结构盲审（主证据，`prepare_promotion_evidence.py` prepare→assemble-blind→finalize，见 PROMOTION_EVIDENCE_WORKFLOW.md）→ A 30 分执行盲测（3 题 Codex CLI 冻结快照执行 vs 冻存基线 24/30 与 v10 28/30，注意 4 个破盲坑：prompt 身份标签/快照路径泄版/协议词指纹/grader 只看 response.md）→ C skill-system 三案例回归。B=VALID_PROMOTION_EVIDENCE（approve·method_research·accuracy not_established）；A=29/30（>24/30 旧发布、>28/30 v10；唯一失分是答案自弃 ROIC/fade 链）；C=1胜1平1窄负、无 iteration-1 式回归复发（operating 窄负记为下轮训练发现，档案 training-runs/skill-system-eval/iteration-4/） | canonical 源=trainer 顶层 references/ + assets/（协调器包全是生成物勿手改）；基线命令 `cd technology-company-forecasting-trainer && python3 -m pytest tests/ -m "not diagnostic_benchmark"` |
| 4 | **backend 修复**：a) `effective_valuation` 只认 sealed/delivery_passed（治半成品上板）b) `extract_valuation`/`has_valuation` 适配 v10 `fair_value_by_scenario_id` 方言 | a) ✅ b) ✅ 均已落地并 Fable 逐行验收（后端 116 + 前端 9 全绿；v10 视图绝不伪造 fair_value.base；行为变化：v10 行以参考情景值计入"平均上涨空间"）。已随 `8fcc39c` 提交、本地+runner 均已部署生效 | backend/app/db.py；测试跑法见下「验收命令」 |
| 5 | **前端适配**：webapp + Site console 渲染 scenario-set 新形态 | ✅ 全部完成：webapp 与 #4b 同批；Site console 已 sync:ui + 测试 142/142 + lint 干净，提交推送 `73860dd`，经 sites-hosting 流程公开部署为**平台 Version 17**（用户批准），线上实测 `app.js?v=20260721-v13` 加载、MRVL 卡片恢复已交付估值（基准 $213 三值条），污染数据消失 | sites/forecast-ops-console |
| 6 | **runner 对齐** | ✅ 完成（2026-07-21 深夜窗口，无任务在跑）：skills 重置为干净 cf46400（40 个 rsync 残留已核实可恢复并打保险包进 backups/ 后清理；sync 脚本已排除 forecasting-skills 防再脏）；代码同步；PG16 安装+forecast_evidence 建库；证据库 init+ingest（77 原件）；backend 服务重启验证 active；备份 bundle 冒烟含 pg_dump 无警告 | 本地与 runner 双端一致 |
| 7 | **盲测复验** | ✅ 完成（2026-07-22）：v11 = **29/30**（基线 24/30、28/30 全超），档案 training-runs/method-system-v11-evals/iteration-1/；促升证据 training-runs/method-system-v11-research/promotion-runs/20260721T162238…/promotion_evidence.json | 后续方法改动仍以此为门 |
| 8 | **流程清晰化**：把 docs/plans/ 里已落地/已过期的方案标注状态，方法文档去重 | 未开始 | docs/plans/ |
| 9 | **运行护栏**（法证缺陷 ⑫⑬）：job 日志体量护栏（截断/大 diff 折叠）；长跑 job 的检查点/续跑评估；codex 引擎侧全量回显与 compaction 问题主要靠 #3 工件瘦身缓解 | 未开始 | backend/app/jobs.py（注意与任务队列改动接力） |

## 三点五、协作纪律（开发/改造 session 适用；不写进 CLAUDE.md 的原因见末条）

1. 方案性工作先调研 2–4 个成熟同形态项目再出方案；不做只回应用户上一条意见的"响应式设计"。
2. 方向未定型先停下与用户磨清楚；汇报先平实语言、后数字、少参数名词。
3. 同一判别机制修到第 2、3 个边缘 case 时停手问用户（继续追修 vs 换通用形态）。
4. 代码注释不写出处附注；决策溯源放设计文档与 commit message。
5. 并行 session：开始/恢复先 `git status --short` 摸并发改动，接力不重做不回退，不越权写别人车道。
6. 失败响亮上报；「完成」只能由当次真实跑过的检查背书；执行代理的「完成」必须实物核查后才认账。
7. Git 纪律：未经用户明确要求不 commit/push/发布/破坏性清理；唯一豁免是 forecasting-skills 方法文件的
   既定 git 流程（编辑规范源→测试→重生成→commit→push）。
8. 运维纪律：重启/部署后端（本地或 runner）会杀 running job——先查任务看板、再经用户同意；重跑失败任务同样先问。
9. 路由：Fable 做方案/语义敏感修复/复审/裁决，Opus 子代理做规格明确的执行（用户 2026-07-21 常设授权
   Fable 自主路由）；模型路由由 `CLAUDE_CODE_SUBAGENT_MODEL=opus` 环境变量机械实现。
10. **这些纪律只放本文件与 memory，不写进 CLAUDE.md/AGENTS.md**——用户已裁定过一次撤销：headless
    预测/训练 job 会加载那两个文件，散文规则会污染其上下文（教训记录于 memory
    `feedback-ultracode-subagent-model`）。

## 四、关键决策与教训（What worked / What didn't）

- ✅ v10 原件托管+真实 hash；SEC 批量抓取快（8 分钟 123MB）；结构化交付校验能抓住真错误（Q1 现金流重复计数被红队发现）。
- ❌ 3300 行单体生成器 + 每修一点全量重生成 = 检查-试错循环的放大器（1h44m）；发布硬门槛要求「独立评审身份」但引擎单进程难产出 → 反复冻结（FRESH_FREEZE_3）；部署重启杀掉 2h46m 的任务；未封存草稿污染投资看板。
- 📌 机制裁定：像「Q1 现金流重复计算」这类错误，追求的是**机制上不可能发生**（构造正确），检查只是兜底。
- 📌 并行 session 纪律照旧（先 `git status` 摸并发改动，接力不重做）；重启/重跑任务必须先问用户。

## 五、验收命令（改动前后都要真实跑过）

- 后端：`FORECAST_JOBS_DIR=<tmp> FORECAST_DB_PATH=<tmp>/forecast.db backend/.venv/bin/python -m pytest -q backend/tests`
- 前端：`node --test webapp/tests/model-view.test.cjs`（必须指定文件）
- Site：`cd sites/forecast-ops-console && npm test` 与 `npm run lint`
- skills：`cd forecasting-skills/technology-company-forecasting-trainer && python3 -m pytest tests/ -m "not diagnostic_benchmark"`（当前基线 563 passed / 1 skipped）
