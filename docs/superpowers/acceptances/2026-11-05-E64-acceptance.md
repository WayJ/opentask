# E64 Acceptance：假日包扩容 mid — EU/UK + 2027 · CLI 1.48.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E64-S1`  
基线：`63d7c4f`（全文 `63d7c4f66ca3e1f83e14b7bb4392b80a5607413a`；含 E64 design；E63 实现 tip `0a53ef7` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e64-holiday-pack-expansion-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e64-holiday-pack-expansion-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 6 静态包 + loader 发现 | ⏳ | EU/UK 2026 + CN/US/EU/UK 2027；CN2027 调休待补 |
| B list region/year + preview/apply 复用 | ⏳ | pack wins；applied_holiday_packs；cap |
| C FE 新区/年 + 可选筛 | ⏳ | vitest+build |
| D CLI 1.48.0 + list flags | ⏳ | pins |
| E 安全 / no-emit / 邻面不动 | ⏳ | 无 ICS/外网；不改 E57–E63 主表面 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

（收口补）

## Tip

（收口补）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`（收口确认）

**STOP** — 未 push / 未开 PR / 未开 E65
