# E58 Acceptance：国家/地区假日包 mid · CLI 1.42.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E58-S1`  
基线：`ed17b2d`（全文 `ed17b2d99cbee8676fc16add0908b0a027e18a2e`）  
**tip：** _pending_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 静态包+loader | ⏳ | Q1a CN+US 2026；kind ⊆ closed/forced_open |
| B preview/apply | ⏳ | Q2a 默认 WS / 可选 policy；Q3a pack wins；Q5a/Q6a |
| C 账本+alembic | ⏳ | Q4a applied_holiday_packs；重算 cap 500 |
| D FE | ⏳ | settings/sla 假日包折叠；vitest merge |
| E CLI 1.42.0 | ⏳ | holiday-packs list/show/preview/apply；pins |
| F 安全/no-emit | ⏳ | 无外网拉取；不改 E55/E57；formula no-emit |

## ADR 确认
- D1–D7 见 design；开放问题 **Q1a–Q6a** 全关（未重开）

## 门禁
| 面 | 结果 |
|----|------|
| BE | _pending_ |
| CLI | _pending_ |
| FE | _pending_ |

## Gaps / 非目标（未做）
- ICS / 在线政府 API / 州级包 / 冲突矩阵 / Activity Push / Insights 再厚 / Search FTS
- Formula emit；改 E57 告警 / E55 Insights 主表面
- **无 push / 无 PR / 不自开 E59**

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = ok`（收口后勾）
- **STOP**
