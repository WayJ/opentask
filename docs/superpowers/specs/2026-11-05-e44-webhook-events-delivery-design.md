# E44 Design：Outbound webhook event pack + delivery reliability v1

日期：2026-11-05（Asia/Shanghai）  
Epic：E44  
基线：`sprint/E43-S1` @ `851319a`（design `bf57338`；acceptance tip 文件内仍写 `f98806d`，属 tip-bump 残余）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E44-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E45**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E44-S1`。开放问题 Q1–Q6 均按建议默认关闭。建议路径  
`docs/superpowers/specs/2026-11-05-e44-webhook-events-delivery-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E29 交付出站 Webhook：CRUD、HMAC、同步投递（`MAX_ATTEMPTS=2` / `RETRY_DELAY_S=0.3`）、`WebhookDeliveryLog`（无 payload）、`POST …/test`、FE 设置页、CLI。  
E41/E42 各加一薄事件：`issue.custom_field_changed`、`issue.sla_breached`。  
Automations 侧早已有专用触发：`issue.assignee_changed`、`label_added` / `label_removed`；**出站 webhook 没有对等事件**——指派变更只落在 `issue.updated.changed[]`，标签增删 **完全不** `fire_webhooks`。

现状缺口（代码实证）：

| 面 | 现状 |
|----|------|
| `WEBHOOK_EVENTS` | `issue.created\|updated\|status_changed` · `comment.created` · `issue.custom_field_changed` · `issue.sla_breached` |
| `IssueService.update_issue` | assignee 变 → automation `issue.assignee_changed`；webhook 仅 `issue.updated`（+可选 status） |
| `TagService` 加/删 label | timeline + automation；**无** `fire_webhooks` |
| `WebhookDeliveryLog` | success / status_code / attempt / error / latency；**不存** request body / envelope |
| 同步重试 | 请求内最多 2 次；失败后无队列、无延期、无人工 replay |
| FE | 详情可见 deliveries 列表；**无**按失败过滤、无「重试」按钮、无死信态 |
| CLI | CRUD + test；无 deliveries / retry / run-due |

E41–E43 附录连续把「Webhook 事件包 + 投递重试/死信 UI」标为下一候选，但单做事件名过薄。本轮 **事件包与投递可靠性捆成一个中厚切片**，对齐 Linear 周边「集成可订阅、失败可恢复」期望，并复用 E35/E38/E39/E42 的外部 `run-due` 模式（无进程内 cron）。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Webhook event pack + delivery reliability v1**：专用 `issue.assignee_changed` / `issue.label_added` / `issue.label_removed` + 失败投递持久化 payload + 外部 `run-due-deliveries` 延期重试 + 人工 replay API + FE 失败列表/重试 + CLI **1.28.0** | **中厚且连贯**；闭合多轮「薄事件」抱怨；集成面 ROI 高 |
| B | SLA v2 薄片（暂停 + breach→automation；无营业日历） | E42 刚交 clocks；宜再沉淀；附录已标 v2 |
| C | Formula range / sort-by-formula / Display 条件格式 | E43 刚齐 surfaces；range 可后置；非集成主路径 |
| D | WS 全局活动 feed 产品化 | UI 重；E41 CSV export 已够审计 |
| E | 仅加 3 个 webhook 事件名（无可靠性） | **过薄**；与「prefer mid-thick」冲突 |

**拍板建议：A（Webhook event pack + delivery reliability v1）。**  
SLA v2、Formula range/sort、全局 feed 列入附录供 E45+。

自检：事件契约、payload 持久化、重试/死信语义、权限、FE/CLI **1.28.0**、非目标已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| SLA v2（营业时/暂停/升级） | E42 次日再加厚易溢；先观察 v1 使用 |
| Formula range / sort / 条件格式 | E43 刚交付等值过滤；range 属增强非阻塞 |
| 全局活动 feed | 产品化 UI Epic；审计导出已有 |
| 仅事件名不加可靠性 | 薄；订阅方仍无法从失败中恢复 |
| Redis/Celery 真队列 | 运维面过大；与现网「外部 tick」哲学冲突 |

## 1. 目标

成功标准：订阅方可收到 **指派变更** 与 **标签增删** 的专用出站事件（HMAC 契约同 E29）；失败投递可被 **延期自动重试**（外部 tick）或 **人工 replay**；FE 可浏览失败投递并一键重试；跨租户隔离；CLI **1.28.0**；**不**引入进程内 cron / Redis 队列 / 改 HMAC 主算法。

### A · 专用事件包（BE 写路径）

在 `WEBHOOK_EVENTS` 追加（均带 `issue.` 前缀，与现网 webhook 命名对齐；**开放问题 Q1**）：

| 事件 | 触发点 | payload 要点（`data`） |
|------|--------|------------------------|
| `issue.assignee_changed` | `IssueService.update_issue` 当 `assignee_id` 实际变化（含置空） | `{ id, issueCode, title, from, to, actorUserId }`；`from`/`to` 为 user id 或 `null` |
| `issue.label_added` | `TagService`（及等价）成功把 label 挂到 Issue | `{ id, issueCode, title, labelId, labelName, actorUserId }` |
| `issue.label_removed` | 成功从 Issue 卸 label | 同上 |

规则：

- **额外**于既有 `issue.updated`：指派变更仍发 `issue.updated`（`changed` 含 `assignee_id`），**并**发专用事件（订阅方可只订专用事件，避免解析 `changed[]`）。  
- 标签增删：今日无 webhook → 本轮新增专用事件；**不**为此硬造一条假的 `issue.updated`（除非写路径本就会碰 updated——**建议不加**，避免噪音；Q2）。  
- Automation 触发名保持不变（`issue.assignee_changed` / `label_added` / `label_removed`）；webhook 用表内新名，文档注明对照。  
- Formula / cache / SLA 路径 **不**因本 Epic 新增 emit（延续 E40 D7 / E43）。

### B · 投递账本加厚（持久化可 replay）

扩展 `webhook_delivery_logs`（或并列新表 `webhook_delivery_attempts`——**建议扩列 + 状态机，少表**；Q3）：

新增/明确字段：

| 列 | 含义 |
|----|------|
| `delivery_id` | 稳定投递 UUID（= envelope `id` / `X-OpenTask-Delivery`）；同一次逻辑投递多 attempt 共享 |
| `payload_json` | 完整 envelope（或 body 文本）；**仅失败/待重试行保留**；成功可清空或截断以控体积（ADR D4） |
| `status` | `success` \| `pending_retry` \| `dead` \| `success_after_retry`（或 bool 组合；实现选一） |
| `next_attempt_at` | UTC naive；`pending_retry` 时有值 |
| `attempt` | 已尝试次数（含首次同步） |
| `max_attempts` | 默认常量 `WEBHOOK_DELIVERY_MAX_ATTEMPTS = 5`（含首次）；可后置 WS 设置 |

行为：

1. `dispatch_event` / `_deliver`：首次仍同步尝试（保持 E29 低延迟手感）；若最终失败 → 写/更新 log：`status=pending_retry`，`payload_json=envelope`，`next_attempt_at = now + backoff(attempt)`。  
2. **Backoff（ADR D5）**：固定序列分钟级，例如 `[1, 5, 25, 120]`（在 max 内）；UTC naive；与 due-reminder 账本同风格。  
3. 超过 max → `status=dead`（死信）；不再自动 tick；可人工 replay（replay 重置 attempt 或另开 delivery_id——**建议同 delivery_id 续 attempt 并清 dead→pending**；Q4）。  
4. 成功：`status=success`（或 `success_after_retry`）；**可**置 `payload_json=null` 省空间。  
5. 修剪：`DELIVERY_LOG_LIMIT` 仍按 webhook 保留最近 N 条；死信优先保留至上限内（实现时：删最旧 **非 dead** 优先；Q5 可简化为仍按时间 prune）。

### C · 外部 tick + 人工 replay API

| 端点 | 行为 |
|------|------|
| `POST /api/webhooks/run-due-deliveries` | member+（对齐其它 run-due）；扫描本 WS `pending_retry` 且 `next_attempt_at <= now`；逐条 `_deliver` 用存盘 payload；单条失败隔离；返回 `{ processed, succeeded, failed, dead, errors[] }` |
| `POST /api/webhooks/{id}/deliveries/{deliveryLogId}/retry` | owner（或 member+；**建议 owner** 对齐 webhook 写）；忽略 next_attempt_at，立即用存盘 payload 再投；无 payload → 400 `delivery_not_replayable` |
| `GET /api/webhooks/{id}` | deliveries 序列化增 `status` / `nextAttemptAt` / `deliveryId` / `replayable` |

无进程内 cron；CLI / 外部调度打 tick。

### D · FE

- `/settings/webhooks`：事件多选 +3（中文 label：经办人变更 / 添加标签 / 移除标签）  
- Webhook 详情/抽屉：投递表增列「状态」；筛「失败/死信」；行内 **重试** 按钮（调 replay API）；dead 行高亮  
- 最小 vitest：事件常量含新三项；`replayable` 展示逻辑

### E · CLI **1.28.0**

- `webhook create|update --events` 接受新事件名；help 列表更新  
- `webhook deliveries <webhook_id> [--status pending_retry|dead|…] [--json]`  
- `webhook retry <webhook_id> <delivery_log_id> [--json]`  
- `webhook run-due [--json]` → `POST /api/webhooks/run-due-deliveries`  
- version → **1.28.0**；全仓历史 version 断言同步

### F · 数据模型摘要

**修改：** `WEBHOOK_EVENTS` +3；`webhook_delivery_logs` 加列（Alembic `k7f8a9b0c1d5`，`down_revision = j6e7f8a9b0c4`）  
**写路径：** `IssueService` assignee 旁路 `fire_webhooks(issue.assignee_changed)`；`TagService` 加/删后 `fire_webhooks`  
**复用：** E29 HMAC / `build_event_envelope` / `_deliver`；E35+ run-due 模式  
**不改：** automation 触发名；formula emit 禁令；SLA 表

## 2. 安全 / 租户 / 威胁模型

- 一切 query/tick 带 `workspace_id`；跨租户 404  
- webhook CRUD / replay：**owner**；run-due：member+（与 inbox/sla run-due 对齐）  
- payload_json 含租户数据：仅 owner 可读 deliveries；不进其它 API  
- URL 校验沿用 E29（防 SSRF）；重试不放宽  
- 无任意代码；tick 单 WS 扫描硬顶（如 100 条/请求）防打爆  
- 签名算法不变；replay 使用**原 secret 现签**（secret 轮换后旧 payload 仍用当前 secret——文档注明；与 test 一致）

## 3. 非目标

- Redis / Celery / 进程内 cron / 多 worker 租约  
- 改 HMAC 版本或 payload schema 大版本（envelope 字段可加 `deliveryAttempt`）  
- 入站 webhook / OAuth app 市场  
- `issue.cycle_changed` / `estimate_changed` 等其它专用事件（仍由 `issue.updated.changed[]` + timeline 覆盖）  
- SLA v2；Formula range/sort；WS 全局活动 feed  
- 远程 push / 开 PR / 自开 E45

## 4. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | 改 assignee → 订阅方收到 `issue.assignee_changed`（含 from/to）；未订阅不调用 |
| B | 加/删 label → `issue.label_added` / `issue.label_removed`；无标签变更不发 |
| C | 同步失败 → log `pending_retry` + 存 payload；run-due 到期再投成功 → success；超限 → dead |
| D | `POST …/retry` 对 dead/pending 可 replay；无 payload → 400；跨 WS 404 |
| E | FE 多选新事件；失败列表 + 重试按钮可用 |
| F | CLI **1.28.0** + deliveries / retry / run-due + version 断言 |
| G | 回归：E29 test 投递；E41 CF webhook；E42 sla_breached；E43 formula **不**因本 Epic emit |
| 门禁 | BE 定向+全量绿（记 passed/skip；`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E45 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **Webhook event pack + delivery reliability v1**（方案 A） |
| D2 | 新事件：`issue.assignee_changed` / `issue.label_added` / `issue.label_removed`（webhook 命名空间统一 `issue.*`） |
| D3 | 指派变更：**双发** `issue.updated` + 专用事件；标签：**只发**专用事件 |
| D4 | 失败才持久化 `payload_json`；成功可清空 |
| D5 | 首次同步 2 次短重试保留；其后靠 `pending_retry` + 外部 run-due + backoff |
| D6 | `WEBHOOK_DELIVERY_MAX_ATTEMPTS = 5`（含首次同步）；超限 dead |
| D7 | 人工 replay = owner；run-due = member+ |
| D8 | CLI **1.28.0**；全仓 version 断言同步 |
| D9 | 非目标见 §3；不 push；不自开 E45 |

## 6. 测试要点

- BE：PATCH assignee → webhook spy 含 `issue.assignee_changed`；payload from/to  
- BE：add/remove label → 对应事件；无 fire 当未订阅  
- BE：mock httpx 失败 → pending_retry + payload；拨 `next_attempt_at` 过去 + run-due → 再 POST  
- BE：连续失败至 max → dead；retry API 拉起再投  
- BE：跨 WS retry 404；无 payload 400  
- FE：事件常量；retry 按钮调 API  
- CLI：version 1.28.0；run-due / retry help  
- 回归：既有 events；HMAC test；E41/E42 事件；E43 no-emit

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration 扩 `webhook_delivery_logs` + status 机（TDD）  
3. `_deliver` 失败入队语义 + run-due + replay API（TDD）  
4. 写路径挂 assignee / label 专用 `fire_webhooks`（TDD）  
5. FE 事件多选 + 投递表状态/重试  
6. CLI 1.28.0  
7. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | webhook 标签事件用 `issue.label_*` 还是与 automation 同名 `label_*`？ | **`issue.label_*`**（与 `issue.*` 包一致；文档对照 automation） |
| Q2 | 标签变更是否同时发 `issue.updated`？ | **否**（减噪；专用事件足够） |
| Q3 | 扩 `webhook_delivery_logs` 还是新 `webhook_outbox` 表？ | **扩列**（少迁移面） |
| Q4 | dead 人工 replay：续同一 `delivery_id` 还是新 id？ | **续同一 id**，attempt++，status→pending/success |
| Q5 | prune 是否特殊保留 dead？ | **否**；仍按时间/上限简单 prune（死信可先手动 retry） |
| Q6 | run-due 权限 member+ 还是仅 owner？ | **member+**（对齐 sla/inbox run-due） |

---

## 附录 · 本轮未选但仍高 ROI（供 E45+）

1. **SLA v2**：营业日历、first-response metric、暂停（waiting-on-customer）、breach → automation 动作链。  
2. **Formula range / sort-by-formula / Display 条件格式**（接 E43 等值过滤）。  
3. **WS 全局活动 feed**：产品化时间线（E41 CSV 已够审计导出）。  
4. 其它专用 webhook（`issue.cycle_changed` / `estimate_changed`）——仅当订阅方强烈需要再拆。
