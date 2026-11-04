# E39 Acceptance：Due reminders + digest tick

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E39-S1`  
基线 design：`019e552`  
状态：**施工中**（收口补 tip / 测数）

## 范围
- A：prefs `due_reminder`/`due_reminder_digest` + `due_reminder_deliveries` 账本
- B：`POST /api/inbox/run-due-reminders`（+ GET deliveries）
- C：FE 通知设置两开关 + Inbox type 标签
- D：CLI **1.23.0**（`notif run-due-reminders` + prefs keys）

## ADR（摘要）
- D1 账本表幂等；D2 无内置 cron / UTC；D3 LEAD=3 / 关闭态；D4 收件人 assignee∪watchers、digest issue_id NULL
- D5 每用户每 UTC 日至多 1 digest；D6 soon 含 due_date_bucket；overdue 按日
- D7/D8 prefs+E30 邮件；D9 CLI 1.23.0；D10 非目标 / 不 push / 不自开 E40

## 门禁（待填）
| 面 | 结果 |
|----|------|
| BE 定向 | TBD |
| BE 全量 | TBD |
| CLI | TBD |
| FE vitest+build | TBD |
| tip | TBD |

## 非目标（未做）
见 design §7。

## Superpowers
`design/plan/TDD/verify/acceptance` — 收口时勾 ok
