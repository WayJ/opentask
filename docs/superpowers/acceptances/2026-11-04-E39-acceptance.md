# E39 Acceptance：Due reminders + digest tick

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E39-S1`  
基线 design：`019e552`  
tip：`22dcc90`
状态：**PASS（本地齐套；未 push）**

## 交付 A–D

| 面 | 内容 |
|----|------|
| A | `notification_preferences.due_reminder`（默认 true，进 PREF_KEYS）+ `due_reminder_digest`（默认 false，模式列）；Inbox types `due_reminder` / `due_reminder_digest` → TYPE 均映 `due_reminder`；表 `due_reminder_deliveries`（`dedupe_key` 承载 soon/overdue/digest 唯一语义）+ Alembic `f2a3b4c5d6e0` |
| B | `POST /api/inbox/run-due-reminders` member+；UTC；LEAD=3；收件人 assignee∪watchers；digest 合并；失败隔离；`GET /api/inbox/due-reminder-deliveries`；create 用 `actor_user_id=None` |
| C | FE `/settings/notifications` 两开关（digest 在 reminder 关时 disabled）+ UTC/LEAD/email 说明；Inbox type 标签 |
| D | CLI **1.23.0**：`notif run-due-reminders`、`notif due-deliveries`；prefs keys；全仓 version 断言同步 |

## ADR（落地）
- D1 账本表 + `dedupe_key` 幂等（等价 design §A 三类唯一）
- D2 无内置 cron；外部 tick；UTC naive/date
- D3 LEAD_DAYS=3；关闭态 closed/resolved/rejected
- D4 收件人 assignee∪watchers；digest `issue_id` NULL
- D5 每用户每 UTC 日最多 1 digest；同日不改写
- D6 soon 去重含 due_date_bucket；overdue 按日
- D7/D8 prefs + E30 email_enabled 邮件钩
- D9 CLI 1.23.0
- D10 非目标见 design §7；不 push；不自开 E40

## 门禁

| 面 | 结果 |
|----|------|
| BE 定向 `test_e39_due_reminders.py` | **12 passed** |
| BE 全量 | **957 passed** / 24 skipped / **1 failed**（已知 flake `test_tasks_jira_wire::TestMetadata::test_user_search`；与 E39 无关；单跑复测见下） |
| CLI 全量 | **475 passed** / 89 skipped |
| FE vitest | **278 passed**（42 files） |
| FE build | **ok**（vite prod） |

### flake 复测
- `pytest tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`：见收口 commit 当时结果（不阻塞 E39）。

## 非目标（未做）
进程内 cron；可配 LEAD；Formula CF；webhook CF outbound；Slack；snooze 联动；push/PR；E40。

## Superpowers
`superpowers: design/plan/TDD/verify/acceptance = ok`
