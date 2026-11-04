# E24 Acceptance

状态：齐套  
分支：sprint/E24-S1  
基线：89242cf  
tip：ede3db8d91778ec3972513b2e966361658837233

## Checklist
- [x] A `GET /api/insights/summary` 五块聚合 + 跨租户/缺头负例；SQL aggregate
- [x] B FE `/insights` + 侧栏；Cycle 下拉；空/loading；viewer 可见
- [x] C Home 薄条「本周完成 / 开放」→ Insights
- [x] D CLI `insights summary`；version **1.8.0**
- [x] BE/CLI 绿；FE 不恶化；未 push；不自开 E25

## 测试数
- BE：863 passed, 24 skipped（E23 857 + Insights 6）
- CLI：426 passed, 89 skipped（E23 423 + E24 insights 3；version 1.8.0）
- FE：233 passed（E23 231 + insights helpers 2）；lint 既有 10 errors 未新增；`pnpm run build` 成功

## ADR 摘要
D1–D10 见 design：独立 `/api/insights`（不复用 datainsight）；DONE=resolved+closed；Naive Progress+表格；Home 薄链；CLI 1.8.0。

## Gaps / 非目标（刻意不做）
自定义报表 / CSV / Slack / 自定义字段 / 自动化 / Redis WS / 远程 push / E25。
