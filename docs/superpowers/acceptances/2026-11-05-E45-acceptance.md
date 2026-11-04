# E45 Acceptance：SLA v2 thin — pause + breach→automation

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E45-S1`  
基线：`f6683d2`  
tip：_(收口填写)_

## 范围（交付中）
- **A** `sla_policies.pause_statuses` 默认 `[]`；CRUD/serialize `pauseStatuses`；校验 IssueStatus
- **B** `CLOCK_STATUSES+=paused`；`elapsed_before_pause_minutes` / `paused_at` / `segment_started_at`；sync pause/resume；resume 重算 deadline；pause 保留旧 deadline
- **C** stop>pause>start；run-due 仅 running；breach → Inbox + webhook + `fire_automations(issue.sla_breached)`；允许 set_status + 文档警告；无 pause timeline
- **D** FE：pause 多选 + paused 徽标 + automation 触发；vitest
- **E** CLI **1.29.0**：`--pause`；issue paused 字段；version 断言同步
- **F** Migration `l8a9b0c1d2e6` ← `k7f8a9b0c1d5`；running 回填 `segment_started_at`

## ADR（落地）
- D1 SLA v2 thin：pause + breach→automation  
- D2 仅 time_in_status；墙钟 UTC naive；无营业日历  
- D3 stop > pause > start  
- D4 活跃钟 = running|paused；每 (issue,policy) 一条  
- D5 run_due 只扫 running  
- D6 resume：`deadline = now + max(0, target - elapsed)`  
- D7 trigger = `issue.sla_breached`；复用 ACTION_TYPES  
- D8 breached → Inbox → webhook → automations；后两者失败不回滚  
- D9 CLI **1.29.0**  
- D10 不 push；不自开 E46

## 门禁
| 面 | 结果 |
|----|------|
| BE | _(收口)_ |
| BE 定向 | _(收口)_ |
| CLI | _(收口)_ |
| FE vitest | _(收口)_ |
| FE build | _(收口)_ |

## Gaps / 非目标（刻意不做）
- 营业日历 / first-response / 策略优先级 / pause timeline
- Redis / 进程内 cron；formula emit；HMAC 改版
- push / PR / E46

## superpowers
`design/plan/TDD/verify/acceptance = _(收口)_`
