# E64 Acceptance：假日包扩容 mid — EU/UK + 2027 · CLI 1.48.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E64-S1`  
基线：`63d7c4f`（全文 `63d7c4f66ca3e1f83e14b7bb4392b80a5607413a`；含 E64 design；E63 实现 tip `0a53ef7` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e64-holiday-pack-expansion-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e64-holiday-pack-expansion-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 6 静态包 + loader 发现 | ✅ | `EU/UK/2026` + `CN/US/EU/UK/2027`；CN2027 closed-only + sourceNote「调休待补」(Q4a)；UK=England & Wales (Q5a)；EU 单一超集 (Q1a) |
| B list region/year + preview/apply 复用 | ✅ | `list_packs(region=, year=)` + `GET ?region&year`；pack wins；applied_holiday_packs；CN/US 2026 回归 |
| C FE 新区/年 + 可选筛 | ✅ | settings/sla 假日包折叠；region/year NSelect；vitest `holidayPacks.test.ts`；build ok（elegant-router 误删 f/r 已还原，守 E63） |
| D CLI 1.48.0 + list flags | ✅ | `sla holiday-packs list --region/--year`；pins 全钉 **1.48.0** |
| E 安全 / no-emit / 邻面不动 | ✅ | apply 无新 webhook 事件名；automation spy=0；无 ICS/州包/外网；不改 E57–E63 主表面 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1206 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E64 无关）
- BE 定向 E64+E58：**16 passed**
- CLI：**561 passed / 89 skipped**（全钉 **1.48.0**）
- FE vitest：**361 passed**（48 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E64-S1`
- tip：`f195dcc`（全文 `f195dccdd2122cf167a26998deddc487a95c2d44`）
- **未 push / 未开 PR / 未开 E65**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E65
