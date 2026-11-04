# E24 Acceptance

状态：施工中  
分支：sprint/E24-S1  
基线：89242cf  
tip：（收口时填写）

## Checklist
- [ ] A `GET /api/insights/summary` 五块聚合 + 跨租户/缺头负例；SQL aggregate
- [ ] B FE `/insights` + 侧栏；Cycle 下拉；空/loading；viewer 可见
- [ ] C Home 薄条「本周完成 / 开放」→ Insights
- [ ] D CLI `insights summary`；version **1.8.0**
- [ ] BE/CLI 绿；FE 不恶化；未 push；不自开 E25

## 测试数
- BE：（收口）
- CLI：（收口）
- FE：（收口）

## ADR 摘要
D1–D10 见 design：独立 `/api/insights`；DONE=resolved+closed；CLI 1.8.0；Home 薄链。

## Gaps / 非目标（刻意不做）
自定义报表 / CSV / Slack / 自定义字段 / 自动化 / Redis WS / 远程 push / E25。
