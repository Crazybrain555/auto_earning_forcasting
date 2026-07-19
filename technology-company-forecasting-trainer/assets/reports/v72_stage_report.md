# Technology Company Forecasting v7.2：Netflix与NVIDIA多截面回测

## 本轮范围

仍使用一个统一的 `technology-company-forecasting` Skill，不创建Netflix或NVIDIA独立Skill。

- Netflix：FY2014校准、FY2016/FY2018伪留出、FY2019外生冲击分布；
- NVIDIA：FY2018校准、FY2019企业边界断点、FY2020/FY2021伪留出；
- 每个截面预测未来1—3年收入和营业利润；
- 外生冲击、未公告并购和AI制度切换使用distribution-only合同。

这些预测是回顾性点时点模拟，并非当年真实封存的样本外业绩。

## 伪留出结果

| 公司 | 指标 | v7.1 | v7.2 |
|---|---|---:|---:|
| Netflix | 收入MAPE | 15.7% | 3.3% |
| Netflix | 营业利润率误差 | 2.20pp | 0.53pp |
| Netflix | 收入覆盖 | 25.0% | 100.0% |
| NVIDIA | 收入MAPE | 20.0% | 3.3% |
| NVIDIA | 营业利润率误差 | 9.30pp | 1.76pp |
| NVIDIA | 收入覆盖 | 20.0% | 100.0% |

## Netflix修正

1. 收入改为平均付费会员×ARPU＋广告/其他，并按地域、套餐、价格和汇率拆分。
2. 会员桥强制区分gross additions、churn和净增。
3. 国内与国际/新市场使用不同成熟度和贡献利润曲线。
4. 内容资产、内容摊销、现金内容投入、内容义务和债务分开。
5. 报告营业利润和现金内容经济同时输出。
6. 疫情等截面时不可知的外生冲击不倒填Base，只进入分布尾部。

## NVIDIA修正

1. Gaming sell-in、sell-through和渠道库存分开。
2. Gaming、Data Center、ProViz、Auto和OEM等平台分别建模。
3. 客户部署需求与公司实际订单、供应和可交付能力分开。
4. foundry、先进封装、HBM、网络和系统交付共同形成供给上限。
5. 采购义务、库存和取消风险进入下行情景。
6. 已公告并购进入企业边界桥；未公告交易不得倒填。
7. 调整后项目经济与GAAP摊销、step-up、SBC、整合、终止费用分开。
8. 生成式AI作为离散制度切换尾部，第三年点值降级。

## 全回归

- AWS：无退化；
- Marvell：无退化；
- Lam/KLA：无退化；
- Sandisk：锁定收入、EPS和估值零差异；
- Legacy 96点：零差异；
- Package self-test与24项单元测试：通过。

## Readiness

Netflix历史收入/营业利润和NVIDIA常规平台/渠道周期达到回顾性research-grade。精确Netflix churn、单部内容ROI、NVIDIA客户份额、渠道库存和供应容量仍为human-required。外生冲击、企业边界断点和AI制度切换只输出分布。

当前样本仍小，且全部为回顾性模拟。真正decision-grade需要未来4—8个季度不回改的滚动验证。
