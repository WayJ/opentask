# E19 设计：Linear Home / My Issues · Due→Inbox · Watchers 列表

日期：2026-11-04（Asia/Shanghai）  
Epic：E19  
基线：`sprint/E18-S1` @ `46d562b`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E19-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E20**。

## 1. 目标

### A · Home / My Issues
- Home 分区：Assigned to me / Created by me / Watching / Due soon
- 各区跳 Issue 列表（带 filter/query）；侧栏「我的问题」可进列表
- API 扩展 list 滤参：`assignee_id=me` / `reporter_id=me` / `watching=true` / `due_before` / `due_soon`；强制 workspace membership；跨租户负例

### B · Due → Inbox
- `due_date` 变更 → 通知 assignee + watchers（跳过 actor）；类型 `due_date_changed`（与 timeline 对齐）
- 同时写 timeline `due_date_changed`

### C · Watchers 列表 UI
- Issue 详情展示 watchers（名/可选头像占位）；可取消自己；不管理他人
- list API 附带 `username`/`name` 展示字段

### D · CLI
- `issue list --mine / --watching / --due-soon`；version **1.4.0**

## 2. ADR：Due soon 策略

**选定：Home / list 查询，不造 cron Inbox。**

| 方案 | 说明 | 结论 |
|------|------|------|
| A. Home-only 查询 | `due_soon=true` = 今日起 3 日内到期且未关闭；Home 分区 + list 深链 | **采用** |
| B. 轻量 Inbox 定时投递 | 每日扫到期写 Inbox | 不做：重、需调度；E19 排除 cron |
| C. 仅前端本地滤 | 无服务端滤 | 不做：CLI/跨页不可复用 |

事件型 Inbox 仅覆盖 **due_date 被改**，不覆盖「自然到了今天」。

## 3. 决策

| ID | 决策 |
|----|------|
| D1 | Query：`assignee_id`/`reporter_id` 支持字面量 `me`（路由层解析为当前用户） |
| D2 | `watching=true`：join `issue_watchers` 且 `user_id=current` |
| D3 | `due_before=YYYY-MM-DD`：`due_date::date <= due_before`；`due_soon=true`：`today <= due_date::date <= today+3` 且 status ∉ {closed,resolved,rejected} |
| D4 | `notify_due_date_changed`：assignee + watchers，跳过 actor；type=`due_date_changed` |
| D5 | update_issue：due_date 变更写 timeline + 调 notify |
| D6 | serialize_watcher 增 `username`/`name`（批量查 User） |
| D7 | Home 四区卡片 + 深链 `/issue/list?scope=assigned|created|watching|due_soon` |
| D8 | Issue list 读 `scope`/`assignee_id`/`reporter_id`/`watching`/`due_soon` 传 API |
| D9 | CLI bump 1.4.0；中文 docs；不 push；不自开 E20 |

## 4. 非目标
- Slack/邮件外发、Customer Requests、Insights、WebSocket
- 管理他人 watchers、Due soon cron Inbox
- 换主题令牌

## 5. 验收摘要
- 四区 Home 可点进列表且结果符合滤参
- due_date 变更 → assignee/watchers Inbox；actor 不收；timeline 有 due_date_changed
- 详情可见 watchers；可取消自己
- CLI `--mine/--watching/--due-soon` 绿；BE/CLI pytest 绿；相关 vitest 绿
- 本地 tip；**不 push**
