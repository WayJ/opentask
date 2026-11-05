# E42 Design：SLA clocks v1（状态时钟策略 + 违约 tick）

日期：2026-11-05（Asia/Shanghai）  
Epic：E42  
基线：`sprint/E41-S1` @ `804ae42`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E42-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E43**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E42-S1`。建议路径  
`docs/superpowers/specs/2026-11-05-e42-sla-clocks-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E35/E38/E39 已固化 **外部 `POST …/run-due*`** 模式（UTC naive、无进程内 cron、单条失败隔离、CLI bump）。  
E41 补齐 Issue 审计面（timeline +4 / CSV export / CF webhook）。  
E40/E41 附录连续把 **SLA clocks** 标为下一厚候选，但 E41 当时判定「策略×状态机×tick 过厚」——本轮用 **v1 收窄** 压到单 sprint。

仓库现状：

| 面 | 现状 |
|----|------|
| 状态变更 | `IssueService.update_issue` 写 `status_changed` timeline + notif + automation + webhook |
| 到期提醒 | E39 `due_reminder*` + 投递账本 + `POST /api/inbox/run-due-reminders` |
| 自动化延迟 | E38 `delay_minutes` + `POST /api/automations/run-due`（冷却/升级近似，**非** SLA 策略） |
| SLA | **无**策略表、无时钟行、无违约语义 |

日常缺口（对齐 Linear 周边「运营/支持」期望，非 Linear 核心 board）：Issue 进入某状态后必须在 N 小时内离开（或进入目标状态），否则标记违约并通知。E38 delay 只能「等 N 分钟再动作」，不能表达「在状态上停留过久」。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | **SLA clocks v1**：WS 级「time-in-status」策略 CRUD + Issue 时钟行 + 状态写路径启停 + 外部 `run-due` 判违约 + Inbox/可选 webhook；CLI **1.26.0** | **中厚且连贯**；复用 E35/E38/E39 tick；砍掉营业时/多策略链/自动升级动作 |
| B | Formula 过滤 / SmartSearch / 可选物化 | 高 ROI 给公式用户，但触碰 E40 D2/D7（物化/emit）与列表求值成本；安全面另开更稳 |
| C | Webhook 事件包加厚（`assignee_changed` / `label_*` 等）+ 全局活动 feed | 偏薄或 UI 产品化重；`issue.updated.changed[]` 已覆盖大半 |
| D | 完整 SLA（营业日历×多策略优先级×暂停×升级动作链） | 单 sprint 必溢；与「加厚但可控」冲突 |

**拍板建议：A（SLA clocks v1）。**  
Formula 过滤物化、Webhook 事件包、全局活动 feed 列入附录供 E43+。

自检：策略模型、时钟状态机、tick 语义、权限、FE/CLI **1.26.0**、非目标已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Formula 过滤 / 物化 | E40 明示后置；列表侧读时求值或物化 emit 需独立安全 ADR |
| Webhook 事件包 | 薄；与 E41 刚交的 CF webhook 叠在一起 ROI 递减 |
| 全局活动 feed | E41 WS CSV export 已覆盖审计导出；产品化 feed 是另一 UI Epic |
| 完整 SLA（营业时/多策略） | 易溢出；v1 先立时钟语义 |

## 1. 目标

成功标准：WS 可配置 **time-in-status** SLA 策略；Issue 进入 `startStatuses` 时启动时钟，离开到 `stopStatuses`（或关闭态）时停止/满足；外部 tick 将超时时钟标为 **breached** 并投递 Inbox（可选 webhook）；详情可见 SLA 徽标；跨租户隔离；FE 设置 + 徽标；CLI **1.26.0**；**不**引入进程内 cron / 营业日历 / 自动升级动作。

### A · 数据模型

- 新表 **`sla_policies`**（WS 作用域）：
  - `id` (uuid str PK)
  - `workspace_id` (FK workspaces, CASCADE)
  - `name` (str, ≤80)
  - `enabled` (bool, default true)
  - `metric` (str)：本 Epic **仅** `time_in_status`（预留列，校验枚举）
  - `start_statuses` (JSON 数组，非空；Issue.status 字面量)
  - `stop_statuses` (JSON 数组，可空；空 = 任一 **非** start 且属关闭类 `{resolved,closed,rejected}` 亦停；显式列表优先)
  - `target_minutes` (int, 1…10080；默认 1440 = 24h) — **日历分钟**（UTC naive 墙钟差，**非**营业时）
  - `notify_assignee` (bool, default true)
  - `notify_watchers` (bool, default false)
  - `created_at` / `updated_at` (DateTime UTC naive)
  - 索引：`(workspace_id, enabled)`；**v1 允许多策略**，同一 Issue 可并发多时钟（每策略一行）
- 新表 **`issue_sla_clocks`**：
  - `id` (uuid str PK)
  - `workspace_id` (FK, CASCADE)
  - `issue_id` (FK issues, CASCADE)
  - `policy_id` (FK sla_policies, CASCADE)
  - `status`：`running` | `met` | `breached` | `cancelled`
  - `started_at` (DateTime UTC naive)
  - `deadline_at` (DateTime = started_at + target_minutes)
  - `stopped_at` (nullable)
  - `breached_at` (nullable)
  - `start_status` (str，启动时 Issue.status 快照)
  - `unique`：`(issue_id, policy_id)` **where status='running'**（部分唯一；SQLite 测用应用层 + 普通 unique 兜底：同对最多一条 running——实现用查询保证，PG 用 partial unique）
  - 索引：`(workspace_id, status, deadline_at)` 供 tick
- Inbox `type` += `sla_breached`
- `PREF_KEYS` += `sla_breached`（默认 **true**）；`TYPE_TO_PREF_KEY` 映射
- 迁移：`i5d6e7f8a9b3_sla_clocks_v1`（命名按仓内 Alembic 惯例；down_revision = E41 tip 头 revision `h4c5d6e7f8a2`）

### B · 写路径（启停时钟）

- 挂在 `IssueService.update_issue` **status 实际变更之后**（与 timeline/automation 同请求；时钟写入 **同事务**）：
  1. 加载本 WS `enabled` 策略（`metric=time_in_status`）
  2. 对每个策略：
     - 若 `new_status ∈ start_statuses` 且该 (issue,policy) **无** `running` 时钟 → 创建 `running`（`started_at=utcnow`, `deadline_at=started_at+target_minutes`, `start_status=new_status`）
     - 若存在 `running` 且 `new_status` 满足停止条件 → 置 `met`，`stopped_at=utcnow`（**不**改已 `breached`）
     - 停止条件：`new_status ∈ stop_statuses`（若 stop 非空）；或 `stop` 空且 `new_status ∈ {resolved,closed,rejected}`；或 `new_status ∉ start_statuses` 且 stop 非空时 **仅** stop 列表生效（**ADR D3**：stop 非空则严格按 stop；stop 空则「关闭类」停）
  3. Issue **软删/硬删**（若有）：级联 FK；无额外钩
- **不**在 create_issue 自动启钟，除非创建时 status 已落在 start_statuses（**拍板：create 也启**——与 update 共用 `_sync_sla_clocks(issue, old_status|None, new_status)`）
- bulk_update：**YAGNI** 本轮不扩展（与 E41 cycle timeline 一致）；标 Gaps
- formula / CF 变更 **不**触碰 SLA

### C · Tick：`POST /api/sla/run-due`

- 权限：**member+**；强制 `X-Workspace-Id`；仅当前 WS
- 语义：
  - 候选：`issue_sla_clocks` where `workspace_id=WS` AND `status='running'` AND `deadline_at <= utcnow()`
  - 对每条：置 `breached` + `breached_at=utcnow`；然后投递 Inbox
  - 收件人：按策略 `notify_assignee` / `notify_watchers` 收集；去重；无人则仅标违约
  - Inbox：`type=sla_breached`；title 含 issueCode + policy name；body 含 started/deadline；尊偏好 `sla_breached`；邮件走 E30 钩若 `email_enabled`
  - **幂等**：已 `breached` 不再投；同 clock 双跑 tick 第二趟 skip
  - 单条失败记 `errors[]`，不阻断其余
- 响应：
  ```json
  {
    "scanned": 10,
    "breached": 3,
    "notificationsCreated": 4,
    "skipped": 7,
    "errors": [{"clockId":"…","message":"…"}]
  }
  ```
- **可选薄加（同 Epic）**：`WEBHOOK_EVENTS` += `issue.sla_breached`；breach 时 `fire_webhooks`（HMAC 复用 E29）；payload `{ id, issueCode, title, policyId, policyName, deadlineAt, breachedAt, actorUserId: null }`  
  - **拍板：做**（与 E41 出站信号连贯；事件面小）
- **不内置 cron**；文档注明与 recurrences / automations / due-reminders 同调度

### D · API

| 方法 | 路径 | 权限 | 行为 |
|------|------|------|------|
| GET | `/api/sla/policies` | member+ | 列表本 WS 策略 |
| POST | `/api/sla/policies` | **owner** | 创建；校验 statuses ⊆ 已知 IssueStatus；target_minutes 范围 |
| PATCH | `/api/sla/policies/{id}` | owner | 更新；禁用 `enabled=false` **不**自动取消 running（tick 仍扫；**ADR D5**：禁用后 tick **跳过**该 policy 的 running——实现：join policy.enabled） |
| DELETE | `/api/sla/policies/{id}` | owner | 删策略；级联时钟 |
| GET | `/api/issues/{id}/sla` | member+ 读 Issue | 返回该 Issue 时钟列表（含 policy 摘要） |
| POST | `/api/sla/run-due` | member+ | tick |

跨租户 404；强制 `X-Workspace-Id`。

### E · FE

- `/settings/sla`（或 settings 子页）：策略列表 + 创建/编辑抽屉（name、start/stop 多选状态、target 小时或分钟、notify 开关、enabled）
- Issue 详情：SLA 徽标区——`running` 显示剩余/已用；`breached` 红色；`met` 灰；多策略并列
- 通知偏好：`sla_breached` 开关文案「SLA 违约」
- settings/webhooks：事件多选 + `issue.sla_breached`（label：SLA 违约）
- 最小 vitest：剩余时间格式化；事件常量含新事件

### F · CLI **1.26.0**

- `sla policy list|create|update|delete|show`
- `sla issue <id|code>`（列时钟）
- `sla run-due [--json]`
- webhook `--events` 可含 `issue.sla_breached`
- version → **1.26.0**（全仓断言同步）

## 2. 数据模型（摘要）

**新增：** `sla_policies`、`issue_sla_clocks`；Inbox type / pref `sla_breached`；`WEBHOOK_EVENTS` + `issue.sla_breached`

**不改：** Issue 主表结构（时钟外置）；automations 表；due_reminder 账本

**复用：** E29 `fire_webhooks`；E30 邮件钩；E35/E38/E39 run-due 模式；`IssueStatus` 枚举

## 3. 安全 / 租户

- 全部查询带 `workspace_id`；issue/policy 必须同 WS
- owner 写策略；member 读时钟 / 跑 tick（对齐其它 run-due）
- webhook 仍 HMAC；无 SSRF 新面
- 无任意代码；target_minutes 上限防荒谬 deadline
- 禁用策略：tick 不 breach（见 D5）；已 breached 保持历史

## 4. 非目标

- 营业时间 / 时区矩阵 / 节假日日历
- 多 metric（first response、resolution）——仅 `time_in_status`
- 策略优先级 / 互斥 / IssueType 绑定 / 每项目覆盖
- 暂停（snooze / 等待客户）与恢复计时
- breach 自动升级动作（改 priority / 派单）——交给既有 Automations；本轮只通知 + webhook
- bulk_update 启停；全局活动 feed；Formula 过滤/物化
- 进程内 cron；远程 push / 开 PR / 自开 E43

## 5. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | 策略 CRUD；非法 status/分钟 400；跨 WS 404；owner 写 |
| B | 进入 start → running 时钟；stop/关闭 → met；同策略不双开 running |
| C | run-due：过期 → breached + Inbox；双跑幂等；禁用策略跳过；errors 隔离 |
| D | `GET /issues/{id}/sla` 可见；webhook `issue.sla_breached` 可选投递 |
| E | FE 设置页 + 详情徽标 + 偏好 + webhook 多选 |
| F | CLI 1.26.0 + policy/issue/run-due + version 断言 |
| 门禁 | BE 定向+全量绿（记 passed/skip）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E43 |

## 6. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = SLA clocks **v1**（方案 A）；收窄营业时/多 metric/升级动作 |
| D2 | metric 仅 `time_in_status`；日历分钟 UTC naive |
| D3 | stop_statuses 非空 → 严格按 stop；空 → `{resolved,closed,rejected}` 停 |
| D4 | 多策略并发；每 (issue,policy) 至多一条 running |
| D5 | `enabled=false` 的策略：tick **不**标 breach；running 行保留直至手动/删除 |
| D6 | 外部 `POST /api/sla/run-due`；无进程内 cron |
| D7 | breach → Inbox `sla_breached` + 可选 webhook `issue.sla_breached` |
| D8 | create_issue 若 status∈start 也启钟；bulk YAGNI |
| D9 | CLI **1.26.0**；全仓 version 断言同步 |
| D10 | 非目标见 §4；不 push；不自开 E43 |

## 7. 测试要点

- BE：create policy；PATCH status 入 start → 1 running；再入 stop → met
- BE：deadline 过去 + run-due → breached + notif；再 run-due 不双投
- BE：enabled=false 不 breach；跨 WS policy/issue 404
- BE：create issue 直接 start status → 有时钟
- BE：webhook 订阅时 breach 投递；未订阅无调用
- FE：徽标文案；事件常量
- CLI：version 1.26.0；run-due help；policy create
- 回归：E39 due reminders；E38 automations delay；E41 timeline/CF webhook

## 8. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration + models + policy CRUD（TDD）  
3. `_sync_sla_clocks` 挂 update/create（TDD）  
4. run-due + Inbox + webhook 事件（TDD）  
5. FE 设置 + 详情徽标 + 偏好/webhook  
6. CLI 1.26.0  
7. 门禁 + acceptance tip  

---

## 附录 · 本轮未选但仍高 ROI（供 E43+）

1. **Formula 过滤 / SmartSearch / 泳道 / 可选物化 emit**：在列表求值成本与 E40 D2/D7 安全策略明确后再开。  
2. **Webhook 事件包加厚**：`issue.assignee_changed` / `label_added` 等专用事件（今日多由 `issue.updated` 覆盖）+ 投递重试 UI。  
3. **SLA v2**：营业日历、first-response metric、暂停、breach→automation 动作链。  
4. **WS 全局活动 feed**：产品化时间线（E41 CSV 已够审计导出）。
