# E56 Acceptance：SLA policy 日历覆盖 thin · CLI 1.40.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E56-S1`  
基线：`137f734`（全文 `137f7346730fefe110fa38014f5d5b85d42e7400`）  
**tip：** _pending_

## 范围落地

| 项 | 状态 | 说明 |
|----|------|------|
| A 覆盖模型 calendar JSON | ⏳ | Q1a 可选字段继承；Q2a WS 总闸；E53 exceptions / E50 windows |
| B 时钟路径 effective calendar | ⏳ | create/pause/resume/recompute/run-due；Q3a WS 全量；policy 仅本 policy；cap 500 |
| C alembic calendar 列 | ⏳ | Q4a nullable JSON；null≡全继承 |
| D FE 日历覆盖+清除+vitest | ⏳ | settings/sla 折叠；空=继承 |
| E CLI 1.40.0 | ⏳ | `--calendar-json` / `--clear-calendar`；show `effectiveCalendar`（Q5a/Q6a） |
| F 安全 / no-emit / 不改 E52/E54/E55 | ⏳ | owner 写；spy；无新 webhook 事件 |

## ADR 确认
- D1 Epic=SLA policy 日历覆盖 thin · D2 `SlaPolicy.calendar` JSON · D3 effective calendar 时钟 · D4 policy 变更重算本 policy / WS 见 Q3a · D5 FE=既有 SLA 表单 · D6 CLI **1.40.0** · D7 no-emit / 不 push / 不自开 E57

## 门禁
| 面 | 结果 |
|----|------|
| BE | _pending_ |
| CLI | _pending_ |
| FE | _pending_ |

## Gaps / 非目标（未做）
- 国家日历包 / 冲突矩阵 / Activity Push / 死信告警 / Insights 再厚
- Formula emit；push/PR/E57

## 流程
- `superpowers: design/plan/TDD/verify/acceptance = pending`
- **STOP**；**无 push / 无 PR / 不自开 E57**
