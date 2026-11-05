# E42 Acceptance：SLA clocks v1

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E42-S1`  
基线：`a4a03a0`  
tip：`c478528`

## 范围（已交付）
- **A** 表 `sla_policies` / `issue_sla_clocks`；migration `i5d6e7f8a9b3`；pref `sla_breached` 默认 true；`WEBHOOK_EVENTS` += `issue.sla_breached`
- **B** `_sync_sla_clocks` 挂 create_issue / update_issue（真实 status 变更、同事务）；enter start → running；stop 非空严格 / 空→关闭类；已 breached 不改；CF/formula 不碰
- **C** `POST /api/sla/run-due` member+；deadline 到期 → breached + Inbox；respect pref；email 走 E30；disabled 跳过；幂等；失败隔离；可选 webhook `issue.sla_breached`
- **D** Policy GET/POST/PATCH/DELETE（owner 写）；`GET /api/issues/{id}/sla`；跨租户 404
- **E** FE `/settings/sla` CRUD；详情徽标 running/breached/met；偏好开关；webhook 多选
- **F** CLI **1.26.0**：`sla policy list|create|update|delete|show`、`sla issue`、`sla run-due`；历史版本断言已同步

## ADR（落地）
- 无营业日历；日历分钟 UTC naive；metric 仅 `time_in_status`；target 1…10080
- stop 空→`{resolved,closed,rejected}`；多策略并发；(issue,policy) 至多一条 running
- `enabled=false` tick 不 breach；外部 run-due only；create 也启钟；bulk YAGNI
- 不 push / 不开 PR / 不自开 E43

## 门禁
| 面 | 结果 |
|----|------|
| BE | **993 passed**, 1 failed（已知 flake `test_user_search`）, 24 skipped |
| CLI | **490 passed**, 89 skipped |
| FE vitest | **292 passed**（44 files） |
| FE build | **ok**（vite prod） |
| E42 专测 | BE `test_e42_sla_clocks` 16P；CLI `test_e42_sla` 6P |

## Gaps / 非目标（刻意不做）
- 营业日历 / 多 metric / 暂停 / breach 自动升级动作 / bulk 启停 / formula 物化 / 全局 feed
- push / PR / E43

## superpowers
`design/plan/TDD/verify/acceptance = ok`
