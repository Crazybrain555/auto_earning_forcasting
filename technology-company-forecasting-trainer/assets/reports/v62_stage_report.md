# AI硬件预测Skill v6.2：Lam Research / KLA回测与Sandisk回归

## 本轮范围

本轮只处理两类已验证原型：

- `wafer-fab-equipment`：Lam Research；
- `process-control`：KLA。

使用2个校准截面和4个伪留出截面，每个截面预测未来1、2、3年收入与利润，共36个预测点。预测是回顾性点时点模拟，不是真正预注册样本外。

## 伪留出结果

| 指标 | v6.1 | v6.2 |
|---|---:|---:|
| 收入MAPE | 11.3% | 3.7% |
| 利润率误差 | 2.47pp | 0.60pp |
| 收入方向准确率 | 66.7% | 91.7% |
| 收入区间覆盖率 | 75.0% | 100.0% |
| 利润区间覆盖率 | 66.7% | 91.7% |
| 收入区间分数 | 0.457 | 0.285 |
| 利润区间分数 | 0.234 | 0.115 |

收入区间分数改善37.7%，利润区间分数改善50.9%。

## Lam Research修正

1. CSBG不能整体视作服务年金；需拆合同服务、备件、升级和Reliant成熟节点设备。
2. 客户WFE至少拆DRAM、NAND、foundry、logic/IDM，并叠加地域和出口限制。
3. 递延收入需拆客户预付款、已出货待验收工具和未来服务。
4. 毛利率桥需包含客户/产品mix、材料与物流、工厂利用率、field utilization和重组。

## KLA修正

1. technology-development spend与capacity spend分开。
2. 产品拆为wafer inspection、patterning、specialty、PCB/display与service。
3. 服务收入使用installed base × utilization × attach/renewal × ASP。
4. RPO/合同负债按确认期限拆分，超过12个月部分不直接进入一年收入。
5. Orbotech企业边界、减值/摊销和税进入利润桥。

## Sandisk回归

所有锁定收入、EPS和估值指标差异均为0。数值影响中性；治理影响正向，因为v6.2新增原型作用域和非目标原型回归，降低设备规则污染存储模型的风险。

## 方法状态

本轮结构门槛通过，但仍是回顾性研究级证据。下一轮按计划处理Marvell光模块/数据中心互联，并同时回归Lam、KLA、Sandisk和既有legacy benchmark。
