# MCP 候选筛选

筛选日期：2026-07-17。硬约束是同时兼容 Claude Code 与 Codex、支持项目级配置、来源可审计、许可证明确，并避免把凭据写入仓库。

## 已安装

| MCP | 固定版本 | 用途 | 许可证 | 上游 |
|---|---:|---|---|---|
| EdgarTools MCP | 5.40.1 | SEC 10-K/10-Q/8-K、XBRL、申报章节、13F/Form 4 | MIT | https://github.com/dgunning/edgartools |
| arXiv MCP Server | 0.5.0 | 技术论文检索、下载与阅读 | Apache-2.0 | https://github.com/blazickjp/arxiv-mcp-server |

二者都通过标准 MCP stdio 接入；未安装任何仅 Claude 或仅 Codex 的插件包装。

## 符合双端要求但暂未安装

| MCP | 原因 | 上游 |
|---|---|---|
| Alpha Vantage MCP | 官方同时提供 Claude Code 与 Codex 配置，但需要 API Key，并受配额、修订数据与供应商条款约束 | https://github.com/alphavantage/alpha_vantage_mcp |
| Exa MCP | 双端标准 MCP，适合产业链和网页资料发现；需要 API Key/OAuth，且搜索结果仍需回到原始来源核验 | https://github.com/exa-labs/exa-mcp-server |

## 未采用

- Financial Datasets MCP：维护活跃度不足，且需要供应商 API Key。
- OpenBB：依赖和权限面过大，默认状态目录不符合严格项目隔离目标。
- FRED MCP：需要 API Key，当前工具面不满足 ALFRED vintage/点时点回测要求。
- 其他 SEC MCP：与 EdgarTools 重叠，部分使用 AGPL；优先采用上游 MIT 实现。
