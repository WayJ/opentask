# E39 Design：Due reminders + digest tick（到期提醒 / 日摘要 + 外部 tick）

日期：2026-11-04（Asia/Shanghai）  
Epic：E39  
基线：`sprint/E38-S1` @ `c443a39`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E39-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E40**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E39-S1`。建议路径  
`docs/superpowers/specs/2026-11-04-e39-due-reminders-digest-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E19 交付 Home / My Issues 与 **`due_soon` 查询面**，以及 **`due_date_changed` 事件型 Inbox**（仅当有人改 due）。  
**缺口明确写在 E19 ADR：**「自然到了今天」不会进 Inbox；不做 due cron。  
E27 加偏好键（含 `due_date_changed`），**非目标：digest**。  
E30 加邮件通道 `email_enabled`（opt-in），**非目标：digest/cron**。  
E35/E38 已固化可复用模式：**外部 `POST …/run-due*`、UTC naive、无进程内 cron、单条失败隔离、CLI bump**。

日常 Linear 缺口：assignee / watcher 在到期窗口内与逾期后应收到提醒（Inbox，可选邮件），而不是只靠打开 Home「Due soon」卡片。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | 进程内 APScheduler / asyncio 定时扫 `due_date` | 与 E35/E38「无内置 cron」冲突；难测、难水平扩展 |
| B | **`POST /api/inbox/run-due-reminders` 外部 tick**：扫本 WS 未关闭且 due 落在 soon/overdue 窗的 Issue → 按偏好写 Inbox（走 E30 邮件钩）+ **投递账本去重**；可选 **日 digest 合并**（采纳） | 对齐 E35/E38；单测友好；运维同一类 cron 调 recurrences + automations + due-reminders |
| C | 仅 FE 轮询 `due_soon` / 本地 toast | 无服务端语义；离线/邮件不可达；与 E27/E30 偏好面脱节 |

**拍板建议：B。**  
不做 Formula CF；不做 webhook `custom_field_changed` outbound（薄，可另插空）；不做 workspace 时区矩阵 / RRULE / 多通道 Slack。

自检：无 TBD；soon/overdue 窗、收件人、去重桶、digest 开关、租户、CLI **1.23.0** 已写清；单 sprint 可交付。

### 为何不是其它 E38 附录候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Formula custom fields | 求值沙箱/安全面大，厚且易拖长；不堵今日提醒缺口 |
| Webhook `custom_field_changed` outbound | 薄扩展（E29 `events[]` + E36 emit）；ROI 低于补齐 E19/E27/E30 明示非目标 |

## 1. 目标

成功标准：外部 tick 能对「即将到期 / 已逾期」Issue 向 assignee+watchers 投递 Inbox（尊重新偏好）；可选日 digest 合并；邮件走既有 E30 钩；跨租户隔离；FE 可开关键；CLI **1.23.0**；**不**内置 cron。

### A · 偏好 + 投递账本

- **`notification_preferences` 增列**（迁移）：
  - `due_reminder` (bool，默认 **true**) — 类型开关；进 `PREF_KEYS`
  - `due_reminder_digest` (bool，默认 **false**) — **模式开关**（非 TYPE 映射）；true → 当日同用户合并为 **1 条 digest** Inbox，而非逐 Issue
- Inbox `type` 新增：
  - `due_reminder` — 单 Issue soon/overdue 提醒
  - `due_reminder_digest` — 日摘要（body 列多条）
- `TYPE_TO_PREF_KEY`：`due_reminder` → `due_reminder`；`due_reminder_digest` → `due_reminder`（digest 仍受同一类型开关；若 `due_reminder=false` 两者都不落）
- 新表 **`due_reminder_deliveries`**（防刷屏账本，ADR D1）：
  - `id` (uuid str)
  - `workspace_id` (FK workspaces, CASCADE)
  - `issue_id` (FK issues, CASCADE，**digest 行可 NULL** — 见 D4)
  - `user_id` (str，收件人)
  - `kind`：`soon` | `overdue` | `digest`
  - `bucket_date` (Date，**UTC 日历日**)
  - `due_date_bucket` (Date nullable) — soon 用：快照 `due_date::date`，改期后可再提醒
  - `notification_id` (nullable str) — 关联已创建 Inbox
  - `created_at` (DateTime UTC naive)
  - **唯一约束**：
    - soon：`uq_due_rem_soon (workspace_id, issue_id, user_id, kind, due_date_bucket)` where kind=`soon`
    - overdue：`uq_due_rem_overdue (workspace_id, issue_id, user_id, kind, bucket_date)` where kind=`overdue`
    - digest：`uq_due_rem_digest (workspace_id, user_id, kind, bucket_date)` where kind=`digest`（`issue_id` NULL）
  - 实现可用部分唯一索引 / 应用层先查后插 + DB unique；测覆盖双跑不双投
  - 索引：`(workspace_id, bucket_date)`；`(user_id, bucket_date)`

### B · Tick：`POST /api/inbox/run-due-reminders`

- 权限：**member+**（对齐 E35/E38 run-due）；强制 `X-Workspace-Id`；仅当前 WS
- 语义（UTC）：
  - `today = utcnow().date()`
  - **LEAD_DAYS = 3**（与 E19 `due_soon` 对齐，本 Epic **不**做可配）
  - 候选 Issue：本 WS、`due_date IS NOT NULL`、`status ∉ {closed, resolved, rejected}`
    - **soon**：`today <= due_date::date <= today+LEAD_DAYS`
    - **overdue**：`due_date::date < today`
  - 收件人：每个 Issue 的 **assignee**（若有）∪ **watchers**；去重；无收件人则跳过该 Issue
  - 对每个 (issue, user)：
    1. 读偏好：无行 = 懒默认（`due_reminder=true`, `due_reminder_digest=false`, `email_enabled=false`）
    2. `due_reminder=false` → skip
    3. 若 `due_reminder_digest=true`：不立刻 create；将该 issue 摘要加入 **user 当日 digest 缓冲**
    4. 若 digest=false：按 kind 查账本；已存在 → skip；否则 `NotificationService.create(type=due_reminder, …)`（自动走 E30 邮件钩若 email_enabled），成功后写 delivery 行
  - digest 收尾：对每个有缓冲的 user，若当日尚无 `kind=digest` 账本 → create 一条 `due_reminder_digest`（title 如「今日到期提醒 (N)」；body 列 soon/overdue 分组 + issueCode/title/due），写账本；已有则 **本 tick 不追加改写**（ADR D5：同日 digest 以首次为准，避免每分钟 cron 改文）
- **一次 tick**：每个 (issue,user,kind) / 每个 user digest **最多尝试 1 次**；单用户/单 Issue 失败记 `errors[]`，**不阻断**其余
- 响应形状：
  ```json
  {
    "processedIssues": 12,
    "remindersCreated": 5,
    "digestsCreated": 2,
    "skipped": 8,
    "errors": [{"issueId":"…","userId":"…","kind":"soon","message":"…"}]
  }
  ```
- **不内置 cron**；文档注明可与 `POST /api/recurrences/run-due`、`POST /api/automations/run-due` 一同外部调度（建议日频 ≥1，soon/overdue 日桶语义下小时级亦可）
- 可选薄：`GET /api/inbox/due-reminder-deliveries?bucket_date=&limit=100` member+ 只读（验收/CLI）；非必须若时间紧可砍，CLI 仍可只调 run

### C · FE

- `/settings/notifications`：
  - 新增开关 **「到期提醒」** ↔ `due_reminder`
  - 新增开关 **「合并为每日摘要」** ↔ `due_reminder_digest`（`due_reminder` 关时 disabled）
  - 短说明：UTC；soon=今日起 3 日内；逾期每日至多一条；邮件仍受 `email_enabled` + SMTP
- **不做**独立「提醒队列」管理页；Home Due soon 卡片保持 E19 查询面不变
- Inbox 列表对未知 type fail-open 展示 title/body（若现有已支持则零改；否则补 type 标签文案）

### D · CLI **1.23.0**

- `opentask notif run-due-reminders` → `POST /api/inbox/run-due-reminders`
- `notif prefs get|set`：支持 `due_reminder` / `due_reminder_digest`（`--key due_reminder --on|--off`；json 亦可）
- 可选：`notif due-deliveries` → list 账本（若 API 有）
- version → **1.23.0**（全仓历史 version 断言同步 bump）

## 2. 数据模型（摘要）

**改：**`notification_preferences` +2 bool 列。  
**增：**`due_reminder_deliveries`。  
**复用：**`NotificationService.create`（偏好门闩 + E30 `_maybe_send_email`）；E19 关闭态集合；issue watchers 查询。

伪代码（tick 核心）：

```
today = utc_today()
issues = load_open_with_due(ws)
buffers: user_id -> list[(kind, issue)]
for issue in issues:
    kind = "overdue" if issue.due.date() < today else "soon" if issue.due.date() <= today+LEAD else continue
    for user in recipients(issue):
        prefs = get_prefs(ws, user)  # lazy defaults
        if not prefs.due_reminder: continue
        if prefs.due_reminder_digest:
            buffers[user].append((kind, issue)); continue
        if already_delivered_soon_or_overdue(...): continue
        n = await notif.create(type="due_reminder", user_id=user, …)
        insert delivery(...)
for user, items in buffers.items():
    if digest_exists(ws, user, today): continue
    n = await notif.create(type="due_reminder_digest", body=format(items), …)
    insert delivery(kind=digest, issue_id=null, bucket_date=today)
```

## 3. API

| 面 | 行为 |
|----|------|
| `GET/PUT /api/inbox/preferences` | 读写含 `due_reminder`、`due_reminder_digest`；序列化进响应 |
| `POST /api/inbox/run-due-reminders` | 见 §B；member+；强制 WS |
| `GET /api/inbox/due-reminder-deliveries`（建议） | query `bucket_date` 可选、`limit≤100`；member+ |
| Inbox list/read | 新 type 可展示；无破坏性契约变更 |

权限：prefs 仍仅本人；run-due-reminders **member+**（与其它 tick 一致，非「仅本人」）；viewer **403**；跨租户不泄漏。

## 4. FE

- 通知设置页两开关 + 文案
- Inbox type 标签（若需要）
- 不改 Board/Automations/CF（E37/E38 已交付面）

## 5. CLI

- **1.23.0**
- `notif run-due-reminders` + prefs keys + help/测；version 断言全仓同步

## 6. 安全 / 租户

- 全部查询强制 `workspace_id == X-Workspace-Id` 当前 WS
- 收件人必须为该 Issue 的 assignee 或 watcher；**不**向无关成员广播
- create 路径继续走偏好门闩；未知历史 type fail-open 不变
- 邮件：仅当 `email_enabled` + SMTP configured + 可解析地址（E30 D3）
- 账本唯一约束防并发双投；冲突视为 skip（幂等）
- run-due 调用者 **不是**提醒收件人（系统 tick）；Inbox actor 元数据可用 `meta.source=due_reminder_tick`，不冒充用户评论

## 7. 非目标

- 进程内 cron / Celery beat / workspace 时区矩阵（**一律 UTC**）
- 可配 LEAD_DAYS / 每 Issue 自定义提醒偏移 / RRULE
- Formula custom fields；Webhook `custom_field_changed` outbound
- Slack / 推送 / HTML 精美邮件模板
- 改 E19 Home 分区语义；snooze 与 due 提醒联动（E9 snooze 不重做）
- 人工「立即重发」按钮、改期自动清账本 UI（改 due 后 soon 靠 `due_date_bucket` 自然可再投即可）
- 远程 push / 开 PR / 自开 E40

## 8. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | prefs 列+映射；账本唯一；改 due 后 soon 可再投；同日 overdue/digest 不双投 |
| B | run-due-reminders：soon/overdue 收件正确；digest 合并；失败隔离；viewer 403；跨租户不泄漏 |
| C | FE 两开关可用；digest 依赖 due_reminder |
| D | CLI 1.23.0 + `notif run-due-reminders` + prefs keys + help/测 |
| 门禁 | BE 定向+全量绿（记录 passed/skip）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E40 |

## 9. ADR

| ID | 决定 |
|----|------|
| D1 | 新表 `due_reminder_deliveries` 做幂等账本；不在 notification 行上挤唯一语义 |
| D2 | **不内置 cron**；外部 `POST /api/inbox/run-due-reminders`；时区 **UTC naive / UTC date** |
| D3 | `LEAD_DAYS=3` 固定对齐 E19 `due_soon`；关闭态 = closed/resolved/rejected |
| D4 | 收件人 = assignee ∪ watchers；digest 账本行 `issue_id` 允许 NULL |
| D5 | `due_reminder_digest=true` → 每用户每 UTC 日最多 1 条 digest；同日再次 tick 不改写 |
| D6 | soon 去重键含 `due_date_bucket`；overdue 去重键含当日 `bucket_date`（逾期可每日一条） |
| D7 | 新 Inbox types + pref `due_reminder`；`due_reminder_digest` 为模式列，不进 TYPE 映射值域之外的第二类型门 |
| D8 | 邮件仍走 E30：`email_enabled` 通道开关，默认 false |
| D9 | CLI **1.23.0**；全仓 version 断言同步 |
| D10 | 非目标见 §7；不 push；不自开 E40 |

## 10. 测试要点

- BE：soon 窗内 assignee+watcher 各 1 条；关闭态不投；无收件人跳过
- BE：同 tick / 二次 tick 不双投；改 due 后再进窗可再 soon
- BE：overdue 次日可再投；同日不双投
- BE：digest 开 → 多 Issue 仅 1 条 digest；`due_reminder=false` 全跳过
- BE：viewer run 403；跨 WS 不泄漏；单条 create 失败隔离
- BE：email_enabled 时 create 后触发 transport（mock）
- FE：开关读写；digest disabled when reminder off
- CLI：version 1.23.0；`notif run-due-reminders --help`；prefs key 烟测
- 回归：E19 due_soon 查询、E27 其它 prefs、E30 email_enabled、E35/E38 run-due 行为不变

## 11. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration：prefs 列 + deliveries 表 + PREF/TYPE 映射（TDD）  
3. `POST /api/inbox/run-due-reminders`（+ 可选 deliveries list）  
4. FE 通知设置两开关  
5. CLI 1.23.0  
6. 门禁 + acceptance tip  

---

## 附录 · 本轮未选但仍高 ROI（供 E40+）

1. **Formula custom fields**：只读计算列；独立厚 Epic（安全求值 / 依赖图）。  
2. **Webhook `custom_field_changed` outbound**：E29 `events[]` 扩展，接 E36 emit 出站（薄，可插空）。  
