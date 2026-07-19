# Technology Company Forecasting v7.1：AWS多截面回测

## 结果

| 指标 | v7.0 | v7.1 |
|---|---:|---:|
| 收入MAPE | 10.2% | 2.3% |
| Segment营业利润率误差 | 3.64pp | 1.18pp |
| 收入覆盖 | 66.7% | 100.0% |
| 利润覆盖 | 100.0% | 100.0% |
| 收入区间分数 | 0.445 | 0.303 |
| 利润区间分数 | 0.130 | 0.087 |

收入和利润区间分数分别改善 **31.9%** 和 **32.9%**。

## 结构修正

1. 收入拆为usage、effective price、产品/客户/地域mix和cost optimization。
2. 服务器/网络设备使用寿命调整从经营改善中剥离，报告和正常化margin并列。
3. 使用AWS segment assets、P&E、net additions和D&A建立基础设施再投资proxy。
4. RPO按usage与确认时点进入，而不是直接等于未来年度收入。
5. FY2022后的AI增长作为离散regime tail，不事后倒填Base。
6. 独立AWS FCF和ROIC继续human-required。

## 状态

- AWS分部收入和营业利润：回顾性research-grade；
- 独立FCF/ROIC/完整分部估值：screen-grade；
- Netflix订阅与内容模块：仍provisional。

## 回归

Marvell、Lam/KLA、Sandisk和Legacy锁定样本均无退化。下一轮进入Netflix多截面回测。
