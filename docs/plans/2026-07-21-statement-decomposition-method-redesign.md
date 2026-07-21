# Statement-decomposition method redesign (HANDOFF #3)

> Date: 2026-07-21 深夜（研究完成，实施未开始）
> Inputs: 三份调研（经典文献蒸馏 / 现有方法融会贯通审计 / 外部长文搜寻）+ `docs/2026-07-21-mrvl-run-log-forensics.md`
> Gate: 任何方法改动必须过对照盲测（HANDOFF #7，对照旧版 24/30 基线）后才 commit/push

## 一、用户裁定（方向，不再讨论）

只用价值投资视角，不做产业叙事与趋势追逐；以「历史财报勾稽为骨架、逐科目拆解到能算清」为主线重写 SOP；
先融会贯通现有逻辑，不东拼西凑；预测准确本身就能捕捉成长（未来利润看清 → 远期估值自然低）；
训练框架强调"学习阶段"。检查只守底线（宪法 #2 增补），系统整体瘦身。

## 二、现状诊断（审计结论，行号证据见审计原文）

- **现行主线与目标主线顺序相反**：现在是「因果 DAG 优先 → 三表作为派生视图 → 勾稽当下游校验」
  （research-sop.md 十阶段，causal_graph/operating_model 在 integrated_statements 之前）；
  目标是「报表勾稽当骨架 → 逐科目向上拆驱动」。证据纪律可共用，骨架要倒过来。
- **碎片化实锤**：独立性/corroboration 规则被定义 ≥6 处；利润链重述 ≥6 处；价值创造恒等式 5 处；
  三表 schedule 3 处近重复；正常化"三视图"有三套命名（reported/normalized/owner-cash vs
  reported/analytical/cash）；两个 canonical 文件的最终 stage ID 打架（publish_monitor_version vs
  freeze_monitor_learn）；三个纯转发 stub；EV→technology-trend-evidence.md 生产装机断链。
- **产业叙事存量**：industry-economics-and-cycle、technology-commercialization-and-ip、
  forward-evidence、research-lanes、9 个 lens（仅 trainer，632 行）≈1400+ 行，纪律上已自称"必须落到
  财务 driver"，但作为一级方法文档与骨架并列——按裁定应整体降级为"驱动打磨阶段的可选交叉验证输入"。
- **可继承资产**（别推倒重做）：model-mechanical-integrity.md 的三表勾稽/roll-forward/zero-check
  就是新骨架的现成实现；earnings-power-and-mean-reversion.md 的 profit-layers 与正常化；
  ce917c6 的 profit-forecast-accuracy.md（实测误差驱动：margin bridge、below-the-line 清单、
  guidance 锚定纠偏）与拆解主线完全同向；equation-primitives 与 module-* 叶子方程。

## 三、新骨架：八步 SOP（每步带出处）

0. **会计体检闸门**：Healy&Palepu 会计分析六动作 + 巴菲特会计花招清单（重组费/养老金假设/SBC/
   pro forma）+ 芒格激励地图（薪酬 KPI 挂钩科目 → 指引打折）。红旗未清不得进拆解。
1. **历史报表重构**：Penman 经营/金融分离（NOA/NFO、经营利润/净财务费用），大额权益法投资补
   look-through 调整（巴菲特 1990-91 信）。产出可勾稽的历史骨架——这是全案的组织结构，不是某阶段附件。
2. **勾稽锚定**：三表 roll、分部加总、单位期间一致作为硬闭合；"估计项"（维持性 capex 等）明确
   不进精确闭合、只进敏感性（巴菲特 1986 附录："宁可大致正确"）。
3. **科目拆解**：套 RNOA = PM × ATO（Nissim-Penman）：收入→产品/客户/量价挂 PM；量→供需；
   价→大宗/利率/供需/产品迭代；产能/营运资本→ATO。拆到能算清为止；算不清的标注弃权（格雷厄姆
   "投资 vs 投机"）。
4. **驱动打磨**：重要驱动 ≥2 独立来源交叉（费雪 scuttlebutt 纪律）；每驱动打标
   「可算清 / 肥尾 / 能力圈内外」（塔勒布：肥尾变量禁止点估计只进情景树；芒格能力圈）；
   不重要的按历史/经验中枢估。论文/专家观点只在此步作交叉验证来源，不作驱动本身。
5. **正常化盈利能力**：跨周期多年平均（格雷厄姆 7-10 年，窗口须含一次下行）；owner earnings 并列
   输出（净利+非现金−维持性capex）；先算零增长 EPV（Greenwald：正常化税后经营利润/WACC），
   增长价值单列且必须由"持续高无杠杆有形回报率"背书（巴菲特护城河的财务表达 = 财务事实非故事）；
   fade 默认先验：盈利能力 ~40%/年向长期均值回归、离均值越远越快（Fama-French 2000），
   偏离先验须给证据。
6. **安全边际**：缓冲宽窄由各驱动证据强度反推（格雷厄姆 20 章），另加"未建模不确定性"预算
   （塔勒布沉默证据），不拍固定折扣。
7. **证伪清单**：芒格反演（必须写"崩掉的 3 条路径"并回填情景）+ 固定清单（激励扭曲/会计红旗/
   基率忽视/过度自信/近期偏好）+ 火鸡问题反审（"长期稳定"科目查尾部积累）。未过清单不算完成。

产业内容的裁剪判据（一条规则）：**"这条建议最终改变哪个财务科目的哪个数、证据能否独立复核？"**
能 → 进 SOP；不能 → 降级为产业边界注记。lens/趋势文档整体降级为第 4 步可选交叉验证输入。

## 四、瘦身与构造化（法证 13 条缺陷的对应处置）

- 拆掉单体生成器模式：交付工件按"可独立重建单元"模块化生成，增量门禁（改一处只重生成受影响
  工件）——直接消灭 38.9% 日志与全量重生成循环。
- 检查收敛为两类：①底线确定性校验（三表恒等式/roll-forward/zero-check/provenance/唯一 producer
  ——现有 validate_investment_case、workbook_contract、equation_contract 等保留）；
  ②独立 agent 判断（moat 真伪/论文可信/主线洞见）。其余"防计数/防双填"类校验由
  「authored state → generated views」构造从源头消除。
- 补三类底线检查（法证缺陷 ⑥）：scenario shock 必须真实驱动 sheet 数据流；FCF 必须 driver-built
  非 back-solved；**存量-流量跨期唯一归属**（Q1 现金流双计的机制性拦截——写库/建模时唯一约束）。
- 收敛重复定义：独立性规则、利润链、价值创造恒等式、三表 schedule 各留一处权威定义 + 引用；
  正常化视图统一一套命名；stage ID 统一；删除三个转发 stub 与断链路由（删除清单主循环逐项核实）。

## 五、训练框架：从"错误驱动反思"扩为"课程驱动研习"

现状：trainer 已有完整外部方法反思机制（误差归因 taxonomy → 查外部方法源 → method_reflection.md
+ validate_method_reflection.py + 防过拟合 guard），但它是 miss 触发的事后反应。
改法（复用现有契约，不建新机器）：
1. 在 training loop 选组之前增设 **prior-art 研习阶段**：按课程主动精读方法文献，产出与
   method_reflection 同构的 bounded-claim + misuse_boundary 记录，直接喂给 SOP 重写；
2. methodological-foundations.md 扩为「财报拆解范式」的权威出处册。
首批精读清单（外部搜寻代理排序）：① Fama & French (2000)《Forecasting Profitability and
Earnings》（fade 先验的实证锚）；② Nissim & Penman 报表重构（拆解骨架模板）；③ Greenwald EPV
（零增长盈利能力的机械步骤）；基石背景：巴菲特 1986/1990-91 信、格雷厄姆、Damodaran
narrative-to-numbers（编排哲学）。YouTube 讲座（Damodaran NYU 课、Greenwald 哥大讲座）待
YouTube 匿名访问问题解决后补。

## 六、实施路径（下一步，未开始）

1. RED：为新骨架写失败测试（骨架顺序、重复定义收敛、存量-流量唯一归属、增量重生成）；
2. 重写 research-sop.md + analysis-kernel.md 主线（骨架倒置），Historical base 上提为独立阶段；
3. 收敛重复定义与命名；产业文档降级；删除清单逐项核实后执行（软删原则不变）；
4. trainer 增加 prior-art 研习阶段并首跑一轮（精读清单①-③入册）；
5. 统一重生成五 skill → trainer 全套测试 → **对照盲测（同 v9 iteration-2 三题，对照 24/30）**；
6. 通过后按既定流程 commit/push；不通过则回到 2，绝不带病发布。
