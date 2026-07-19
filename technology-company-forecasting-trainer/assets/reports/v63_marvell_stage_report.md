# AI硬件预测Skill v6.3：Marvell光互联/定制芯片回测

## 1. 本轮范围

本轮新增 `optical-interconnect-custom-silicon` 经营原型，使用四个Marvell历史截面：

- FY2020：企业边界断点，Inphi交易尚未公开；
- FY2021：校准集，Inphi交易已公告且目标公司FY2020财务可获得；
- FY2022：伪留出，Inphi和Innovium已并表；
- FY2023：伪留出＋AI制度切换尾部。

每个截面预测未来一至三年收入与GAAP营业利润，共24个预测点。

这仍是回顾性点时点模拟，不是当时真实封存的样本外预测。

## 2. 回测结果

### FY2022/FY2023伪留出

| 指标 | v6.2 | v6.3 |
|---|---:|---:|
| 收入MAPE | 10.9% | 2.6% |
| GAAP营业利润率误差 | 12.85pp | 2.33pp |
| 收入方向准确率 | 66.7% | 100.0% |
| 利润正负号准确率 | 16.7% | 100.0% |
| 收入区间覆盖 | 100.0% | 100.0% |
| 利润区间覆盖 | 66.7% | 100.0% |
| 收入区间分数 | 0.609 | 0.332 |
| 利润区间分数 | 0.420 | 0.211 |

收入区间分数改善 **45.5%**，利润区间分数改善 **49.7%**。

### FY2020企业边界断点

Inphi交易在FY2020预测截面后才公开，因此不以点MAPE考核。v6.3要求：

- 有机Marvell边界作为Base；
- 未知未来企业边界仅进入匿名分布尾部；
- 多年点值标记 `distribution-only`；
- 结论关键时标记 `human-required`。

v6.3的收入和利润分布均覆盖后三年实际，且没有将未来交易倒填进Base。

## 3. 发现的主要问题

### 3.1 “光模块公司”标签不准确

Marvell主要确认的是互联和计算半导体内容，包括：

- PAM/coherent DSP；
- driver/TIA/PHY；
- silicon photonics；
- DCI芯片或子系统；
- AEC/retimer；
- merchant switching；
- custom compute/ASIC；
- storage controllers和其他传统产品。

除非公司实际确认成品模块或系统收入，否则不能使用完整成品模块BOM。

### 3.2 数据中心收入不是同质收入桶

同一个Data Center收入中可能同时包含：

- AI光互联；
- 定制计算；
- 交换芯片；
- 存储控制器；
- 传统云和网络产品。

v6.3按项目阶段和产品经济单位建模，并将storage、enterprise、carrier、consumer和automotive库存状态独立处理。

### 3.3 Design win不等于收入

新阶段闸门：

```text
architecture discussion
→ funded NRE
→ tape-out
→ sampling / qualification
→ production award
→ material revenue
```

只有production award及以上证据，才能以明确ramp曲线进入Base。

### 3.4 企业边界必须遵守公告时点

若交易在 `as_of` 时已经公告：

```text
reported revenue
= organic legacy revenue
+ target standalone revenue × close probability × consolidated fraction
+ post-close program growth
```

若交易尚未公告，不得使用后续实际交易名称、规模和关闭日期倒填历史基准。

### 3.5 调整后经济与GAAP利润必须双桥

```text
GAAP operating income
= adjusted program economics
- acquired-intangible amortization
- inventory fair-value step-up
- acquisition / integration
- restructuring
- stock compensation
- legal / product claims
```

这一修正使伪留出利润正负号准确率由16.7%提高到100%。

## 4. 全回归

| 回归对象 | 结果 |
|---|---|
| Lam/KLA设备回测 | 无退化 |
| Sandisk锁定收入、EPS和估值 | 零差异 |
| Legacy 96个预测点 | 零差异 |
| Package self-test | 通过 |
| 单元测试 | 14项全部通过 |

因此，新规则没有把设备或存储模型改坏。

## 5. Skill v6.3变化

- 新增 `optical-interconnect-custom-silicon` 原型；
- 新增 `optical-custom-silicon.md`；
- 加强 networking、M&A/perimeter和accounting bridge；
- 新增Marvell benchmark和回测脚本；
- 新增perimeter-break分布评价；
- 新增“半导体内容 vs 成品模块/系统”边界；
- 新增程序级stage conversion；
- 新增Marvell、Lam/KLA、Sandisk和Legacy四组强制回归；
- 包版本升级为1.3.0。

## 6. 当前状态

该原型达到回顾性 `research-grade` 结构门槛，但仍缺：

- 更多公司独立留出；
- 项目级收入和设计阶段公开数据；
- 真实前瞻锁定验证；
- 客户和供应链交叉验证。

不应将本轮历史误差解释为未来预测精度承诺。

## 7. 下一轮

下一轮建立 `cloud-infrastructure-platform` 原型，优先回测AWS多个高速增长截面。AWS存在独立资产负债和现金流披露不足、共享基础设施和内部成本分配等问题，因此会显式建立 `human-required` 数据桥，并继续回归Marvell、Lam/KLA、Sandisk和Legacy。
