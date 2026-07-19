# 闪迪（NASDAQ: SNDK）三至五年财务预测与估值模型报告

> **信息截止：2026-07-17 12:23 ET。** 本文在该时点冻结信息，不使用其后发布的经营事实。SNDK 当时盘中价为 **$1,470.63**，不是 7 月 17 日收盘价；历史盘中快照未必能在动态报价页重现，可用 [Nasdaq SNDK 报价页](https://www.nasdaq.com/market-activity/stocks/sndk)复核后续行情。
>
> **最重要的口径提醒：FY26E 不是实际业绩。** FY26E 是截至 2026-04-03 的 **9M GAAP 实际**，加上公司 FY26 Q4 指引中点形成的模型估算。Q4 实际业绩在本报告截止时尚未披露；公司 Q4 GAAP 税费未给出完整指引，因此 FY26E 税率仍含模型假设。
>
> **状态：screen-grade（筛选级），不是投资建议，也不是卖方一致预期。** FY27—FY30 的 bit、ASP、成本、利润率、股本与估值倍数均为情景假设。数值已按共享模型口径冻结；最终文件一致性校验见 snapshot。

## 一、结论先行

1. 闪迪正处于极强的 NAND 上行周期。FY26 Q3 收入 $5.950bn，GAAP 毛利率 78.4%；收入同比增长 251%，核心原因是 ASP/GB 同比增长 248%，而出货 EB 同比持平。也就是说，当前利润跃升首先是**价格杠杆**，不能直接外推为永久利润率。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
2. AI 数据中心确实带来新的结构性需求：FY26 Q3 数据中心收入达到 $1.467bn、同比增长 645%，其中 ASP/GB 同比增长 186%、EB 同比增长 160%。但 Edge 仍占当季收入约 61.6%，PC、手机和渠道周期仍会显著影响全公司。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
3. 共享模型的 Base 情景并不是“收入永远增长”：FY27 因 bit 增长和高 ASP 跃升至 $33.205bn，随后 ASP 正常化使 FY28—FY30 收入逐步回落至 $27.540bn；净利润由 FY27 的 $18.974bn 降至 FY30 的 $7.394bn。
4. 以 $1,470.63 计，基础股本口径市值约 **$217.785bn**。用 2026-04-03 报表现金 $3.735bn、零债务计算的 reported-cash EV 为 **$214.050bn**；再扣除 4 月 8 日已支付的 $0.972bn 南亚科投资现金、但暂不给股权资产计值，cash-only pro-forma EV 为 **$215.022bn**。若同时把取得的南亚科股权按成本 $0.972bn 作为非经营资产扣除，调整后 EV 约回到 **$214.050bn**。对应 FY26E P/E 约 24.24x、cash-only pro-forma EV/收入约 11.15x。估值已经预支了相当多的结构性增长。
5. 情景估值为 Bear **$217.26**、Base **$1,054.68**、Bull **$3,322.31**。按 Bear/Base/Bull = 30%/50%/20% 加权，筛选级价值为 **$1,256.98**，较盘中价低 **14.53%**；Base 较盘中价低 28.28%。当前价格更接近要求 Bull 结构性突破成立，而不是仅仅要求 Base 成立。

## 二、预测合同与口径

| 项目 | 口径 |
|---|---|
| 实体与证券 | Sandisk Corporation，NASDAQ: SNDK |
| 币种 | 美元；财务表以 $bn 展示，底层模型以 $mm 计算 |
| 财年 | 公司财年约在 6 月末结束；FY26 Q3 截至 2026-04-03 |
| 信息截止 | 2026-07-17 12:23 ET |
| 历史与 FY26E | GAAP 实际为锚；FY26E = 9M 实际 + Q4 GAAP 指引中点，税率含模型假设 |
| FY27—FY30 | GAAP 样式的情景模型；不是公司指引、不是一致预期 |
| 经营原型 | Commodity NAND/storage：收入 = bit shipments × blended ASP/GB；利润另受 cost/GB、利用率、库存 NRV、产品组合与合同执行影响 |
| 估值 | 过渡期 EPS 与正常化 EPS 的加权 P/E，另加情景化 excess cash/share；不是完整 DCF |

## 三、已披露事实：经营与财务锚点

### 3.1 FY26 9M 实际与 Q4 指引

截至 2026-04-03 的 FY26 9M GAAP 实际如下：[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)

| $bn，EPS 除外 | FY26 9M 实际 |
|---|---:|
| 营业收入 | 11.283 |
| 毛利润 | 6.890 |
| 营业利润 | 5.352 |
| 税前利润 | 5.168 |
| 净利润 | 4.530 |
| 摊薄 EPS | $29.42 |
| 摊薄加权股数 | 154m |

公司给出的 FY26 Q4 指引是：收入 $7.750—$8.250bn，GAAP 毛利率 78.9%—80.9%，GAAP 运营费用 $523—$558mm，GAAP 利息及其他收入净额 $12—$32mm；摊薄股数约 158m。公司只给出 non-GAAP 税费 $775—$875mm 和 non-GAAP EPS $30.00—$33.00，未完整调和至 GAAP。[FY26 Q3 earnings deck](https://investor.sandisk.com/static-files/8ea78860-f8e5-4f1c-ada3-c554437d6281)

### 3.2 FY26E 拼接桥：明确不是实际值

模型取 Q4 收入、GAAP 毛利率、GAAP opex 和其他收入指引中点，并对全年采用 14.3% 的模型有效税率：

| $mm，EPS/税率除外 | FY26 9M 实际 | FY26 Q4E | FY26E |
|---|---:|---:|---:|
| 营业收入 | 11,283.0 | 8,000.0 | **19,283.0** |
| 毛利润 | 6,890.0 | 6,392.0 | **13,282.0** |
| 营业利润 | 5,352.0 | 5,851.5 | **11,203.5** |
| 税前利润 | 5,168.0 | 5,873.5 | **11,041.5** |
| 净利润 | 4,530.0 | 4,932.6 | **9,462.6** |
| 摊薄股数 | 154m | 158m 指引 | **156m 全年模型** |
| 摊薄 EPS | $29.42（9M） | 模型推算 | **$60.66** |
| 全年有效税率 | — | — | **14.3% 假设** |

Q4E 净利润不是公司直接给出的 GAAP 指引；它是为了完成 GAAP 样式全年桥而推算的数值。因此，**不得把 FY26E 的 $9.463bn 净利润写成“公司已实现”**。

### 3.3 收入结构与价格杠杆

FY26 Q3 的收入结构为：数据中心 $1.467bn、Edge $3.663bn、Consumer $0.820bn，分别占 24.7%、61.6% 和 13.8%。当季全公司 ASP/GB 同比 +248%，EB 同比持平；分市场来看：

| FY26 Q3 同比 | ASP/GB | EB | 收入 |
|---|---:|---:|---:|
| Datacenter | +186% | +160% | +645% |
| Edge | +343% | -10% | +295% |
| Consumer | +139% | -40% | +44% |

这些是公司 E0 披露事实，不等于未来假设。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)

### 3.4 合同、现金与 JV 固定成本

- 截至 2026-04-03，公司剩余履约义务（RPO）为 **$41.6bn**，但仅约 **15%** 预计在未来 12 个月确认；合同负债为 $511mm。RPO 不能平均摊进未来收入，也不能与产品需求模型重复相加。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
- 截至同日现金及现金等价物为 **$3.735bn**，定期贷款已于 2026-03-04 全额偿还；截至 2026-04-24，基础流通股为 **148,089,758 股**。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
- 闪迪通常取得 Flash Ventures 约 50% 的产出，并须承担一半固定成本，不论最终选择采购多少产出。该结构使下行周期的利润具有凸性风险：量和价格下降时，固定成本无法同步消失。公司还披露 Flash Ventures 历史上接近满产；FY26 9M 曾暂时降低利用率并产生 $11mm 相关成本，但 FY26 Q3 单季没有此类费用。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)

## 四、行业与技术驱动：事实边界

### 4.1 支持增长的证据

- Kioxia 在 2026 Investor Day 引用 TechInsights 的 NAND 市场预测：CY25—CY28 全行业 bit CAGR 约 22%，数据中心约 46%，AI inference 相关需求约 86%；同时预计供需偏紧延续至 CY27。[Kioxia Investor Day 2026](https://www.kioxia-holdings.com/content/dam/kioxia-hd/en-jp/ir/library/event/asset/Kioxia_Investor_Day_2026_en_script.pdf) 这属于供应商官方材料中的第三方预测，应作为 E3 情景输入，不应当作闪迪订单事实。
- Micron 在 2026-06-24 表示，预计 CY26 NAND 行业 bit shipments 增长约 20%，并认为 NAND 供需偏紧可能延续至 CY27 之后。[Micron FY26 Q3 prepared remarks](https://investors.micron.com/static-files/631b1a32-5537-46ae-8f40-82e42fc79dfe)
- TrendForce 估计 1Q26 企业级 SSD 行业收入环比增长 86.1%，合约价约上涨 80%；其对闪迪的估计是企业 SSD bit shipments 约增 20%、收入接近 $1.47bn。[TrendForce, 2026-06-11](https://www.trendforce.com/presscenter/news/20260611-13092.html) 其中行业和公司拆分均为 E3，不取代公司 E0 财报。
- Kioxia 计划未来三年平均每年约 ¥470bn capex，以支持约 22% GB CAGR；其前端 cost/GB 目标为每年下降“10% range”。[Kioxia Investor Day 2026](https://www.kioxia-holdings.com/content/dam/kioxia-hd/en-jp/ir/library/event/asset/Kioxia_Investor_Day_2026_en_script.pdf) 这为模型的 bit 和 cost/GB 边界提供支持，但并非闪迪独立成本指引。

### 4.2 不能越界的地方

1. 客户 AI 基建需求不等于闪迪订单；客户 qualification、shipment、revenue recognition 必须分别建模。
2. QLC 能提高单盘容量和出货 bits，也可能降低 ASP/GB；不能既把 QLC 的 bit 增长全部计入，又把产品组合溢价完整计入，造成双重计算。
3. BiCS10 的 +59% bit density 不等于 cost/GB 立即下降 59%。真实成本还取决于良率、wafer cycle time、设备折旧、节点切换和利用率。
4. RPO 是合同交易价，不等于无条件、等利润率的收入。公司明确提示，如果自身交付失败，可能遭遇降价、减量、赔偿或提前终止；客户违约时的 financial guarantees 也未必覆盖全部收入损失。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)

## 五、共享经营模型

### 5.1 收入方程

共享模型采用：

```text
Revenue_t = Revenue_(t-1)
          × (1 + bit shipment growth_t)
          × (blended ASP/mix index_t ÷ blended ASP/mix index_(t-1))
```

FY26E 收入锚为 $19.283bn，FY26 blended ASP/mix index 设为 75。ASP/mix index 是全公司混合指标，包含市场价格、产品组合、合同价格和终端组合的净效果，不是公司披露的单一产品 ASP。

### 5.2 情景输入：bit 与 ASP/mix

| 情景 | FY27 bit | FY28 bit | FY29 bit | FY30 bit | FY26 ASP index | FY27 | FY28 | FY29 | FY30 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Bear | +12% | +16% | +15% | +14% | 75 | 75 | 45 | 35 | 32 |
| Base | +23% | +23% | +20% | +18% | 75 | 105 | 80 | 60 | 50 |
| Bull | +33% | +30% | +26% | +23% | 75 | 125 | 118 | 105 | 90 |

复算示例：

```text
Base FY27 revenue
= $19.283bn × 1.23 × (105 ÷ 75)
= $33.205bn

Base FY28 revenue
= $33.205bn × 1.23 × (80 ÷ 105)
= $31.118bn
```

情景含义：

- **Bear：** FY27 尚未跌价，但 FY28 出现明显供给/价格均值回归，之后成本下降只能部分修复利润。
- **Base：** FY27 紧缺和数据中心 mix 把 ASP 推至高位；FY28 起价格逐步正常化，bit 增长无法完全抵消 ASP 下行。
- **Bull：** AI inference、QLC/TLC 企业 SSD、长期合同和有限净新增供给共同维持高 ASP；bit 增长也显著高于行业中枢。

### 5.3 cost/GB 与数据中心组合边界

以下为模型假设区间，不是公司指引：

| 情景 | FY27 cost/GB index | FY28 | FY29 | FY30 |
|---|---:|---:|---:|---:|
| Bear | 95—100 | 85—92 | 78—86 | 72—80 |
| Base | 88—92 | 76—82 | 67—74 | 59—66 |
| Bull | 84—88 | 70—76 | 60—67 | 52—59 |

| 情景 | FY27 DC 收入占比 | FY28 | FY29 | FY30 |
|---|---:|---:|---:|---:|
| Bear | 27%—32% | 30%—36% | 33%—39% | 35%—42% |
| Base | 32%—38% | 40%—47% | 45%—52% | 48%—56% |
| Bull | 38%—45% | 50%—58% | 57%—64% | 60%—68% |

FY26 Q3 实际 DC 收入占比只有 24.7%，所以 Base 已要求明显的组合迁移。Kioxia 自身提出 FY28 数据中心收入占比超过 60%的目标，但该目标**不等于闪迪一定达到同一水平**。[Kioxia Investor Day 2026](https://www.kioxia-holdings.com/content/dam/kioxia-hd/en-jp/ir/library/event/asset/Kioxia_Investor_Day_2026_en_script.pdf)

## 六、FY26E—FY30 三情景财务预测

### 6.1 核心结果

单位：$bn；EPS 为美元。FY26E 对所有情景相同，FY27 起分叉。

| 情景 | 指标 | FY26E | FY27E | FY28E | FY29E | FY30E |
|---|---|---:|---:|---:|---:|---:|
| Bear | 营业收入 | 19.283 | 21.597 | 15.031 | 13.445 | 14.013 |
|  | 净利润 | 9.463 | 8.227 | 2.048 | 0.586 | 1.532 |
|  | 摊薄 EPS | 60.66 | 52.07 | 12.96 | 3.73 | 9.82 |
| Base | 营业收入 | 19.283 | 33.205 | 31.118 | 28.006 | 27.540 |
|  | 净利润 | 9.463 | 18.974 | 13.187 | 8.659 | 7.394 |
|  | 摊薄 EPS | 60.66 | 123.21 | 86.75 | 57.35 | 49.29 |
| Bull | 营业收入 | 19.283 | 42.744 | 52.455 | 58.812 | 62.005 |
|  | 净利润 | 9.463 | 27.026 | 31.262 | 30.787 | 27.964 |
|  | 摊薄 EPS | 60.66 | 176.64 | 211.23 | 213.80 | 199.75 |

底层精确值以 $mm 计算：

- Bear 收入：21,596.96 / 15,031.48 / 13,444.83 / 14,013.35；净利润：8,226.58 / 2,048.03 / 585.62 / 1,531.94。
- Base 收入：33,205.33 / 31,118.13 / 28,006.32 / 27,539.55；净利润：18,973.65 / 13,186.75 / 8,659.31 / 7,393.62。
- Bull 收入：42,743.98 / 52,455.42 / 58,812.30 / 62,004.97；净利润：27,025.91 / 31,261.54 / 30,786.66 / 27,964.44。

### 6.2 利润与股本逻辑

净利润桥采用：

```text
Gross profit_t = Revenue_t × gross margin_t
Pre-tax income_t = Gross profit_t - operating expenses_t + other income_t
Net income_t = Pre-tax income_t × (1 - tax rate_t)
EPS_t = Net income_t ÷ diluted shares_t
```

| 情景 | 项目 | FY27 | FY28 | FY29 | FY30 |
|---|---|---:|---:|---:|---:|
| Bear | 毛利率 | 55% | 30% | 20% | 28% |
|  | Opex ($mm) | 2,300 | 2,200 | 2,100 | 2,200 |
|  | Other income ($mm) | 100 | 100 | 100 | 100 |
|  | 税率 | 15% | 15% | 15% | 16% |
|  | 净利率 | 38.1% | 13.6% | 4.4% | 10.9% |
|  | 摊薄股数 | 158m | 158m | 157m | 156m |
| Base | 毛利率 | 74% | 58% | 46% | 42% |
|  | Opex ($mm) | 2,450 | 2,650 | 2,850 | 3,050 |
|  | Other income ($mm) | 200 | 300 | 400 | 500 |
|  | 税率 | 15% | 16% | 17% | 18% |
|  | 净利率 | 57.1% | 42.4% | 30.9% | 26.8% |
|  | 摊薄股数 | 154m | 152m | 151m | 150m |
| Bull | 毛利率 | 80% | 76% | 68% | 60% |
|  | Opex ($mm) | 2,600 | 3,000 | 3,400 | 3,800 |
|  | Other income ($mm) | 200 | 350 | 500 | 700 |
|  | 税率 | 15% | 16% | 17% | 18% |
|  | 净利率 | 63.2% | 59.6% | 52.3% | 45.1% |
|  | 摊薄股数 | 153m | 148m | 144m | 140m |

利润逻辑不是简单的收入利润率外推：

1. ASP/mix 上涨几乎直接落入增量毛利，而 cost/GB 下降相对缓慢，因此 FY27 的利润弹性大于收入弹性。
2. FY28—FY30 ASP 正常化时，即使 bit 增长和 cost/GB 下降，毛利与净利仍可能快速收缩；Bear FY29 接近周期压力测试。
3. Flash Ventures 固定成本、利用率和节点切换会放大利润尾部；必要时还应显式加入 under-utilization、库存 NRV、保修和减值费用。
4. 摊薄股数假设体现 $6bn 回购授权及未来现金生成，但公司明确表示授权不构成必须回购的义务。因此 Base/Bull 的股数下降是模型假设，不是事实。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
5. 毛利率、Opex、other income、税率和股数均为已冻结的共享模型假设，而非公司指引或一致预期。SBC、特殊项目、未来实际税率与回购节奏仍是预测误差来源；目前不应把 45%—63% 的 Bull 净利率视为已验证的长期稳态。

## 七、产品阶段门

| 产品/项目 | 截止时证据 | 阶段门 | Base 模型许可 | 升级或失效条件 |
|---|---|---|---|---|
| BiCS8 | 已在量产；公司 FY26 capex 主要支持 BiCS8，Q3 TLC 企业 SSD 已贡献强劲数据中心收入 | **Stage 4：material revenue** | 可完整进入 bit、成本与产品 mix 模型 | 跟踪良率、占比、cost/GB；若节点切换导致利用率/良率恶化则下调 |
| PCIe Gen5 TLC 企业 SSD | 已完成第二家 hyperscaler qualification；Q3 公司称强劲 TLC 需求推动数据中心收入 | **Stage 4** | 可进入 Base，仍不得把“新增 hyperscaler qualification”直接等同满额收入 | 新客户量产、重复订单和收入拆分上调；qualification 延期或份额流失下调。[FY26 Q2 deck](https://investor.sandisk.com/static-files/1b7ca99b-f84a-4294-9f56-690b32fce69a) |
| Stargate QLC | FY26 Q3 时公司预期 Q4 开始为收入发货；TrendForce 后续称高容量 QLC 已进入 volume shipment，二者对“量产/收入确认”的措辞存在边界差异 | **Stage 3：production + high-confidence demand；尚无截止时 Q4 实际收入** | Base 可计入有限 FY27 收入和 DC mix，不得在 FY26 当作已确认重大收入 | Q4 实际确认收入、更多 qualification、repeat orders 升级；延迟、认证失败或价格折让降级。[FY26 Q3 deck](https://investor.sandisk.com/static-files/8ea78860-f8e5-4f1c-ada3-c554437d6281) / [TrendForce](https://www.trendforce.com/presscenter/news/20260611-13092.html) |
| BiCS10 1Tb TLC | 2026-07-02 宣布 sampling；+59% bit density、+33% interface speed。2026-07-03 K2 宣布“start of production”，但 2026-06-02 Kioxia Q&A 曾表示 samples 后约一年进入 mass production | **Stage 1：sample/initial production；量产时点存在冲突** | Base 到 FY28 才允许重大收入/成本贡献；Bull 可提前至 FY27 下半年；Bear 延后至 FY29 | 客户 qualification、稳定良率、volume mix 和实际 cost/GB 才能升级。[Sandisk BiCS10](https://investor.sandisk.com/news-releases/news-release-details/sandisk-announces-sampling-bics10-1tb-tlc-3d-nand-flash-memory) / [Kioxia K2](https://www.kioxia.com/en-jp/about/news/2026/20260703-2.html) / [Kioxia Q&A](https://www.kioxia-holdings.com/content/dam/kioxia-hd/en-jp/ir/library/event/asset/Investor-Day-2026-Eng-QA.pdf) |
| NBM/LTA 与 $41.6bn RPO | 合同与 RPO 为事实，但执行、产品 mix、价格保护和利润率不是已实现事实 | **Recognition gate** | 只按可交付数量、合同价格和确认期建模；未来 12 个月参考公司披露的约 15% RPO | contract liabilities、履约转收入、违约/重谈、financial guarantee 回收决定上调或下调 |

## 八、当前估值与市场反推

### 8.1 市值、EV 与现行倍数

盘中价格快照为 $1,470.63。以 10-Q 披露的 148.089758m 基础流通股计算：

| 项目 | 计算 | 数值 |
|---|---|---:|
| 市值 | $1,470.63 × 148.089758m | **$217.785bn** |
| 现金 | 2026-04-03 实际 | **$3.735bn** |
| 债务 | 定期贷款已还清；模型按 0 | **$0** |
| Reported-cash EV | 市值 - 4/3 报表现金 + 债务 | **$214.050bn** |
| 南亚科投资现金流出 | 2026-04-08 已支付；暂不给股权资产计值 | **$0.972bn** |
| Cash-only pro-forma EV | 市值 - ($3.735bn - $0.972bn) + 债务 | **$215.022bn** |
| 含南亚科非经营资产的调整 EV | $215.022bn - $0.972bn 成本计值 | **约 $214.050bn** |
| FY26E P/E | $1,470.63 / $60.66 | **24.24x** |
| FY26E pro-forma EV/Revenue | $215.022bn / $19.283bn | **11.15x** |
| FY26E pro-forma EV/Net income | $215.022bn / $9.463bn | **22.72x** |

基础股本用于即时市值，摊薄股本用于 EPS，两者不可混用。现金和债务是截至 2026-04-03 的最后已披露资产负债表数据，并非 7 月 17 日实时余额。Cash-only pro-forma EV 只调整已知的南亚科付款，没有猜测其后经营现金流或回购；若把取得的南亚科股权按 $0.972bn 成本视作非经营资产，则该资产与现金流出相互抵消，EV 近似保持在 $214.050bn。这里未对该股权作市值重估或流动性折价。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)

### 8.2 反推市场隐含的正常化收入

采用简化反推：市场给予正常化 14x P/E、摊薄股本 158m，则当前股价隐含：

```text
Normalized EPS = $1,470.63 ÷ 14 = $105.05
Normalized net income = $105.05 × 158m = $16.597bn
```

再按可持续净利率反推收入：

| 正常化净利率假设 | 隐含正常化收入 |
|---:|---:|
| 35% | **$47.42bn** |
| 40% | **$41.49bn** |

这是 equity reverse model，不是 EV/revenue 模型。结果表明，当前股价要求公司长期维持约 $41.5—$47.4bn 收入并实现 35%—40% 净利率。Base FY30 收入仅 $27.540bn、净利润 $7.394bn；Bull 才明显超过这一隐含收入门槛。因此，市场当前定价更接近“高 ASP 维持 + DC mix 大幅提升 + bit 高增长 + cost/GB 持续下降”的组合。

### 8.3 三情景筛选级估值

估值公式：

```text
Fair value
= 40% × FY27 EPS × transition P/E
+ 60% × AVG(FY29 EPS, FY30 EPS) × normalized P/E
+ excess cash per share
```

| 情景 | 概率 | Transition P/E | Normalized P/E | Excess cash/share | 公允价值 | 相对 $1,470.63 |
|---|---:|---:|---:|---:|---:|---:|
| Bear | 30% | 8x | 10x | $10 | **$217.26** | -85.23% |
| Base | 50% | 10x | 16x | $50 | **$1,054.68** | -28.28% |
| Bull | 20% | 14x | 18x | $100 | **$3,322.31** | +125.91% |
| 概率加权 | 100% | — | — | — | **$1,256.98** | **-14.53%** |

倍数、概率和未来 excess cash/share 全部是模型假设，不是市场共识。此方法用 FY29/FY30 平均 EPS 避免把 FY26/FY27 峰值利润完全资本化，但它仍不是完整 DCF，也尚未对未来价值折现和资本支出尾部做独立审计。

## 九、事实、假设与待验证假说

### 9.1 事实（可作为模型锚）

- FY26 9M 收入 $11.283bn、净利润 $4.530bn；Q3 收入 $5.950bn、GAAP 毛利率 78.4%。
- Q3 全公司 ASP/GB 同比 +248%、EB 同比持平；DC ASP/GB +186%、EB +160%。
- Q4 收入指引 $7.750—$8.250bn、GAAP 毛利率 78.9%—80.9%；Q4 实际尚未知。
- RPO $41.6bn，约 15% 预计未来 12 个月确认；合同负债 $511mm。
- 现金 $3.735bn、定期贷款已还清；基础股数 148.089758m。
- Flash Ventures 产出通常约一半归闪迪，闪迪无论采购量都承担一半固定成本。
- 第二家 hyperscaler 的 PCIe Gen5 TLC 已完成 qualification；Stargate QLC 截止时尚无公司披露的 Q4 实际收入。
- BiCS10 已 sampling，K2 已宣布 start of production，但 mass production 时点存在官方措辞冲突。

主要事实来源：[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)、[FY26 Q3 deck](https://investor.sandisk.com/static-files/8ea78860-f8e5-4f1c-ada3-c554437d6281)、[FY26 Q2 deck](https://investor.sandisk.com/static-files/1b7ca99b-f84a-4294-9f56-690b32fce69a)。

### 9.2 模型假设（不得表述成事实或共识）

- Bear/Base/Bull 概率为 30%/50%/20%。
- FY27—FY30 的 bit growth、ASP/mix index、cost/GB index、DC revenue mix。
- FY26E 14.3% 全年税率；FY27—FY30 的净利润、净利率和摊薄股本。
- 回购足以让 Base/Bull 的摊薄股数下降；回购授权本身不保证执行。
- 过渡期/正常化 P/E、40%/60% 权重和 excess cash/share。
- 14x P/E、158m 股数和 35%—40% 净利率的市场反推框架。

### 9.3 待验证假说（决定 Base/Bull 是否成立）

1. **AI inference 使 SSD 成为新内存层级。** RAG、KV cache、context storage 和 HDD 替代将令企业 SSD bit 需求长期高于传统 PC/手机 NAND。
2. **长期合同压低周期振幅。** NBM/LTA 能改善收入可见性与资本投入纪律，但不能消除交付、重谈、客户违约和市场价格风险。
3. **产品 mix 足以对冲 ASP/GB 均值回归。** 高性能 TLC 和高容量 QLC 令 DC 收入占比明显提升；但 QLC 的低 $/GB 可能抵消部分“高价值产品”叙事。
4. **BiCS10 在量产良率成熟后扩大成本优势。** +59% density 最终带来 cost/GB 改善，但不会在 sampling 或初始生产时立即全部兑现。
5. **供应扩张保持克制。** K2 和同行 capex 主要满足需求增长，而非在 FY28—FY30 再次制造严重过剩。

## 十、关键风险与模型失效点

1. **ASP 均值回归速度快于 cost/GB 下降。** 这是最大的单变量风险，也是 Bear 与 Base 差距的核心。
2. **供给反应滞后但幅度过大。** Kioxia 计划约 ¥470bn 年均 capex，同行也在提高产能；若行业 supply bit growth 持续超过需求，FY28 后价格可快速下行。
3. **固定成本和利用率凸性。** Flash Ventures 固定成本分担、节点切换、良率和库存 NRV 会使净利润下行幅度远大于收入下行。
4. **阶段门失败。** Stargate qualification、客户量产或 BiCS10 mass production 延后，都会同时影响 bit、DC mix、ASP 和 cost/GB，不能只调一个变量。
5. **RPO 被误读。** 只有约 15% 预计在未来 12 个月确认；均匀摊销 $41.6bn 或把它再加到产品模型上会严重高估收入。
6. **合同执行风险。** 交付不足可能触发降价、减量、赔偿或终止；客户违约 guarantees 也可能不足以弥补全部收入。[FY26 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
7. **客户和终端集中。** FY26 Q3 top-10 客户占收入 46%；Edge 仍占 61.6%，PC/手机单位需求疲弱会影响组合与 bit。
8. **JV、自然灾害、供应链和日元风险。** 闪迪实质依赖 Kioxia/Flash Ventures 的 wafer 供应和 K2/Yokkaichi 执行。
9. **税率与会计桥。** FY27 起税法、SBC、特殊项目、外汇及投资项目可能令 GAAP 净利润偏离当前模型。
10. **估值风险。** 11.15x FY26E pro-forma EV/revenue 和 24.24x 峰值附近 FY26E P/E 留给执行失误的缓冲很小。

## 十一、监控触发器

| 频率 | 触发器 | Base 升级信号 | Base 降级/失效信号 |
|---|---|---|---|
| FY26 Q4 实际披露 | 收入、GAAP GM、ASP/GB、EB、Stargate revenue | 收入/GM 达到或超过指引上沿，Stargate 有可验证收入 | 低于指引中点、Stargate 延迟、价格或量显著弱于预期 |
| 每季 | 全公司及终端 ASP/GB 与 EB | bit >20%、ASP 高位保持且 DC 量增长 | ASP 快速跌破模型路径，量增不能抵消价格 |
| 每季 | DC revenue mix、TLC/QLC qualification | Base FY27 向 32%—38% 迁移，多客户 repeat orders | DC mix 停滞、qualification 延迟或客户集中上升 |
| 每季 | RPO、contract liabilities、NBM 数量 | 合同负债转收入、未来 12m 转化率可见 | RPO 下修、重谈、违约、financial guarantees 触发 |
| 每季/节点 | BiCS8/BiCS10 mix、K2 工具安装、良率、cost/GB | BiCS10 在 FY27 后期完成 qualification 并显示成本改善 | “start of production”长期未转成 mass production，良率拖累成本 |
| 每季 | 库存、DIO、NRV、under-utilization | 库存与需求同步、无利用率费用 | 库存持续上升、重复 under-utilization/NRV charges |
| 每季 | 行业供应、capex、企业 SSD 合约价 | 需求 bit 增长持续高于 supply | 行业供给增速 >22% 且价格连续下跌 |
| 每季 | 基础/摊薄股数与回购 | 现金生成实际转化为低价回购并抵消 SBC | 高价回购、回购暂停或摊薄股本上升 |
| 每季 | PC/手机 units 与 Edge 内容量 | 单机容量上升抵消 unit 下降 | units 与内容量同时走弱，Edge ASP/mix 回落 |

建议的情景迁移规则：若连续两个季度同时出现 DC mix >40%、bit 增长 >25%、ASP 至少维持 FY26 Q3 指数 100 附近、且无利用率费用，可提高 Bull 权重；若 ASP 在 FY28 前跌至 FY26 blended index 75 以下、行业供给增速持续超过需求、或出现重复利用率/NRV 费用，应提高 Bear 权重。

## 十二、最终判断

闪迪不是一个可以只用“AI 存储 TAM”外推的线性成长股；它仍是一个价格、bit、成本、利用率和产品阶段门共同驱动的 NAND 周期公司。AI 数据中心、TLC/QLC 企业 SSD、LTAs 和 BiCS10 可能抬高长期中枢，但 FY26 Q3 的 78.4% 毛利率主要发生在 ASP/GB 同比约 3.5 倍的环境中，不能永久资本化。

在本模型的 30%/50%/20% 情景权重下，概率加权价值 $1,256.98 低于 $1,470.63 盘中价 14.53%，Base 价值低 28.28%。市场反推又要求约 $41.5—$47.4bn 的正常化收入和 35%—40% 净利率，显著高于 Base 长期路径。由此，当前价格的风险回报依赖 Bull 的多项条件同时成立，安全边际不足。

因此本报告结论为 **screen-grade：暂不升级到 research-grade 或 decision-support**。升级至少需要：Q4 实际验证、Stargate 收入确认、两至三个季度的 ASP/bit/DC mix 路径、RPO 实际转化，以及 BiCS10 qualification、良率与成本数据。新事实应生成新版本和新 snapshot，不应回写本次冻结预测。

## 主要直接来源

- [Sandisk FY26 Q3 Form 10-Q，2026-05-01](https://www.sec.gov/Archives/edgar/data/2023554/000162828026029401/sndk-20260403.htm)
- [Sandisk FY26 Q3 earnings deck，2026-04-30](https://investor.sandisk.com/static-files/8ea78860-f8e5-4f1c-ada3-c554437d6281)
- [Sandisk FY26 Q2 earnings deck，2026-01-29](https://investor.sandisk.com/static-files/1b7ca99b-f84a-4294-9f56-690b32fce69a)
- [Sandisk FY26 Q1 earnings deck，2025-11-06](https://investor.sandisk.com/static-files/a1cf180d-5720-4475-a3cc-345cfc8aab38)
- [Sandisk BiCS10 sampling announcement，2026-07-02](https://investor.sandisk.com/news-releases/news-release-details/sandisk-announces-sampling-bics10-1tb-tlc-3d-nand-flash-memory)
- [Kioxia Investor Day 2026 script，2026-06-02](https://www.kioxia-holdings.com/content/dam/kioxia-hd/en-jp/ir/library/event/asset/Kioxia_Investor_Day_2026_en_script.pdf)
- [Kioxia Investor Day 2026 Q&A，2026-06-02](https://www.kioxia-holdings.com/content/dam/kioxia-hd/en-jp/ir/library/event/asset/Investor-Day-2026-Eng-QA.pdf)
- [Kioxia/Sandisk K2 BiCS10 production announcement，2026-07-03](https://www.kioxia.com/en-jp/about/news/2026/20260703-2.html)
- [Micron FY26 Q3 prepared remarks，2026-06-24](https://investors.micron.com/static-files/631b1a32-5537-46ae-8f40-82e42fc79dfe)
- [TrendForce enterprise SSD market，2026-06-11](https://www.trendforce.com/presscenter/news/20260611-13092.html)
