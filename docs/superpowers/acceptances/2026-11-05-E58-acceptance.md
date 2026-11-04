# E58 Acceptance：国家/地区假日包 mid · CLI 1.42.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E58-S1`  
基线：`ed17b2d`（全文 `ed17b2d99cbee8676fc16add0908b0a027e18a2e`）  
**tip：** `d042c09`（全文 `d042c09ee7ac12b7f77f8d12d4cce369f2696728`）

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 静态包+loader | ✅ | Q1a `opentask/data/holiday_packs/{CN,US}/2026.json`；kind ⊆ closed/forced_open；list/show；非法 404 |
| B preview/apply | ✅ | Q2a 默认 WS / 可选 policy；Q3a pack wins；Q5a 缺 windows 走 E53 默认；Q6a 单年 |
| C 账本+alembic | ✅ | Q4a `applied_holiday_packs` WS+policy；`q3f4a5b6c7d1`；重算 cap 500 复用 E50/E56 |
| D FE | ✅ | settings/sla 「假日包」折叠；预览 diff；目标 WS/policy；policy 表「假日包」快捷；vitest merge |
| E CLI 1.42.0 | ✅ | `sla holiday-packs list\|show\|preview\|apply`；pins 全 1.42.0；保留 business-hours/calendar |
| F 安全/no-emit | ✅ | 无外网拉取；跨租户 policy 404；不改 E55/E57；apply 不新增 webhook 事件名；formula no-emit |

## ADR 确认
- D1–D7 见 design；开放问题 **Q1a–Q6a** 全关（未重开）

## 门禁
| 面 | 结果 |
|----|------|
| BE | **1155 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`）；E58+E56+E53/E50 定向 **54P** |
| CLI | **546 passed / 89 skipped**；version pins **1.42.0** |
| FE | **vitest 348 passed**（46 files）；**build OK** |

## Gaps / 非目标（未做）
- ICS / 在线政府 API / 州级包 / 冲突矩阵 / Activity Push / Insights 再厚 / Search FTS
- Formula emit；改 E57 告警 / E55 Insights 主表面
- **无 push / 无 PR / 不自开 E59**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**
