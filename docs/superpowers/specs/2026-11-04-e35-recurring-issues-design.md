# E35 设计：Recurring Issues（Linear 周期建单 lite）

日期：2026-11-04（Asia/Shanghai）  
Epic：E35  
基线：`sprint/E34-S1` @ `4014f92`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E35-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E36**。

## 0. Brainstorming（Yuri 代审）

目标：Linear 式周期建单 lite；约束：无常驻 cron、UTC、禁止 push。

方案对比：
- A · 进程内 APScheduler/celery beat — 运维重，非目标
- B · **`POST /api/recurrences/run-due` 外部 tick**（采纳）— 单测友好、与 E26 after-commit 风格一致
- C · 仅 CLI 本地循环 — 缺 API/FE 面

Yuri E35 brief 对齐本 design → **视为已代审**，本 Epic 不打断 Way。

自检：无 TBD；interval/权限/占位符/防刷屏（一次 tick 每条最多 1 张）已写清；范围单 Epic 可交付。

## 1. 目标

按周期从蓝本自动创建 Issue；**不内置常驻 cron**，提供 `POST /api/recurrences/run-due` 供外部调度。

### A · 模型 + CRUD
- 表 `issue_recurrences`：workspace_id、title_template、description、priority、labels_json、project_id、assignee_id、custom_fields_json、interval=`daily|weekly|monthly`、weekday（0=周一…6=周日，weekly 可选）、monthday（1–31，monthly 可选）、next_run_at、enabled、last_issue_id、created_by、timestamps
- `GET/POST /api/recurrences`；`GET/PATCH/DELETE /api/recurrences/{id}`
- 权限：member+ 写；viewer 读；强制 `X-Workspace-Id`；跨租户 403/404

### B · Tick
- `POST /api/recurrences/run-due`（member+）：对 `enabled && next_run_at <= now(UTC)` 每条最多建 1 张 Issue（KEY-N），推进 `next_run_at`，更新 `last_issue_id`
- title 占位：`{date}` / `{yyyy-mm-dd}` → 运行日 UTC `YYYY-MM-DD`
- 单条失败记 log，不阻断其它；返回 `{created, errors:[{recurrenceId,message}], issues:[{id,issueCode,recurrenceId}]}`

### C · FE
- `/settings/recurrences`：列表、创建/编辑、启停、显示 next_run / last issue；侧栏 Settings 入口

### D · CLI **1.19.0**
- `recurrence list|create|update|delete|run-due`；version → **1.19.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 时区：**一律 UTC**（`datetime.utcnow` / naive UTC）。不做 workspace 时区矩阵；文档与 API 注明。 |
| D2 | interval 仅 `daily`/`weekly`/`monthly`；不做 RRULE。 |
| D3 | 一次 `run-due` 对每条 due recurrence **最多创建 1 张**；`next_run_at` 从原计划点起按 interval 推进，直到 **> now**（宕机追赶不刷屏）。 |
| D4 | weekly：若设 `weekday`，推进时落到该 weekday；否则 +7 天。monthly：若设 `monthday`，落到该日（溢出则该月最后一天）；否则 +1 自然月。 |
| D5 | `labels_json` 为 tag **name** 字符串数组；运行时按 WS 解析，找不到的 label 跳过并记入该条 error 摘要（Issue 仍创建）。 |
| D6 | `custom_fields_json` 为 `{key: value}`；未知/校验失败 key 记 error，主 Issue 仍创建（与 E34 partial 精神一致）。 |
| D7 | `assignee_id` / `project_id` 必须属本 WS；创建时非法则该条失败（不建 Issue）。 |
| D8 | actor = recurrence.created_by；若空则用调用 run-due 的用户。 |
| D9 | 不内置 cron/celery beat；调度由外部调 `run-due`。 |
| D10 | CLI 1.19.0；全仓 version 断言同步 bump。 |
| D11 | 非目标：RRULE、日历 UI、时区矩阵、多步流水线、Inbox digest、远程 push、E36。 |

## 3. 非目标

RRULE 全量、日历 UI、时区矩阵、多步流水线、挂起 Inbox digest、远程 push、自开 E36。

## 4. 验收摘要

- CRUD + 租户/角色；run-due 建单+推进+占位符；FE 设置页；CLI 1.19.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**
