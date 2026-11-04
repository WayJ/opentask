# E42 Acceptance：SLA clocks v1

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E42-S1`  
基线：`a4a03a0`  
tip：（收口填写）

## 范围
- A 数据模型 `sla_policies` / `issue_sla_clocks` + pref/webhook 常量
- B `_sync_sla_clocks` 挂 create/update
- C `POST /api/sla/run-due` + Inbox + `issue.sla_breached`
- D Policy CRUD + `GET /api/issues/{id}/sla`
- E FE `/settings/sla` + 详情徽标 + 偏好/webhook
- F CLI **1.26.0**

## ADR
- D1–D10 见 design；日历分钟 UTC；stop 空→关闭类；多策略并发；disabled 跳过 tick breach；外部 tick；create 启钟；bulk YAGNI

## 门禁（收口填）
| 面 | 结果 |
|----|------|
| BE | |
| CLI | |
| FE vitest | |
| FE build | |

## Gaps / 非目标
- 营业日历 / 多 metric / 暂停 / breach 自动升级 / bulk / formula 物化 / 全局 feed / push/PR / E43
- 已知 flake：`test_user_search`（若出现不单独阻断）

## superpowers
`design/plan/TDD/verify/acceptance = ok`（收口确认）
