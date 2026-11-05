# E57 Design：Webhook 死信告警 mid-thick — 阈值 Inbox/邮件 + 可选自动停用 · CLI 1.41.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E57  
基线拟：`sprint/E56-S1` @ `cacfaee`（全文 `cacfaeea305f3aed49c8bbd7717d90fbc0447cea`；E56 design 基线 `137f734`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E57-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E58**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e57-webhook-dead-letter-alerts-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E57-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E56 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ **Webhook 投递可观测（E54：stats + 死信箱 + bulk retry）** → Insights 效能加厚（E55）→ **SLA policy 日历覆盖（E56）**。

E56 附录 runners-up（不绑定）：

1. **Activity 实时/Push 加厚**（WS 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢  
2. **Webhook 失败告警薄刀**（Inbox/email 当死信超过阈值）— E54 刚交可观测；单列过薄 → **本草案将其加厚为 mid-thick 并捆**  
3. **Insights 再厚 / 效能日报**（多 label OR、持久化「我的报表」、可选邮件 digest）— E55 刚交中厚；宜再沉淀

代码实证 @ `cacfaee`：

| 面 | 现状 |
|----|------|
| Webhook 可观测 | E54：`GET /webhooks/stats`、`GET /webhooks/dead-letter`、`POST /webhooks/dead-letter/retry`（cap 50）、单条 replay；FE 指标卡 + 死信箱；CLI `webhook stats` / `dead-letter`；**无**阈值告警、**无**自动停用、**无**告警去重账本 |
| 投递账本 | E44：`WebhookDeliveryLog` status=`success`/`pending_retry`/`dead`；`run-due-deliveries` 外部 tick |
| 钩子 | `WorkspaceWebhook.enabled` bool；**无** `paused_reason` / `alert_*` 列 |
| Inbox / 邮件 | E27 prefs + E30 `email_enabled` + E39 due-reminder 去重账本模式可复用；**无** `webhook_dead_letter_alert` 类型 |
| SLA 日历 | E50/E53/E56 弧已闭合（WS 周窗+例外 + policy 覆盖）；国家包 / 冲突矩阵仍砍 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification（仓内已有 `workspace_realtime`/`websocket` 基建，但产品 Push 仍易溢） |
| Insights | E55 切片+估点速度+CSV；再厚易变报表构建器 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | 厚 Linear 主面（Initiatives/Docs/Estimates/Relations/Customer/Insights/Git-PR）近期已交；E54 把「看得见死信」交齐后，缺口正是 **「超阈值主动找人」**——比立刻叠国家包或 Push 更贴运维闭环 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Webhook 死信告警 mid-thick**：WS（+可选 per-hook）阈值规则；外部 tick / 投递路径上评估 → **Inbox**（+ E30 邮件若 opt-in）；**去重账本**防刷；可选 **连续死信达硬顶自动 `enabled=false`** + 停用通知；FE 告警设置 + mute；CLI **1.41.0**；**无** PagerDuty / **无** Push / **无** 新事件包 | **中厚且闭合 E44→E51→E54→E57 出站弧**；把「过薄告警刀」捆成可交付 Epic；隔开 E55/E56 两轮后时机合适 |
| B | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | E52 铃铛后仍缺产品观察；Push/FCM 单 sprint 必溢；仓内 realtime 基建≠产品闭环；**默认再隔** |
| C | 国家/地区假日包 thin-mid（CN/US… 一键写入 WS/policy exceptions） | E56 刚闭合日历覆盖；连续第四刀 SLA 日历易审美疲劳；包版权/年份维护有债；作 runners-up |
| D | Insights 再厚 / 效能日报 | E55 刚交；立刻再叠易变报表构建器大战 |
| E | Search FTS / Customer 门户 / GitHub App / Initiative 依赖图 / Formula emit | FTS 偏基建；门户·App·依赖图偏厚或排除；emit **永不** |
| F | 仅阈值 Inbox **或**仅自动停用（不并捆） | **过薄**；与 prefer mid-thick 冲突 |

**建议拍板：A（Webhook 死信告警 mid-thick）。**  
Activity Push、国家假日包、Insights 再厚列入附录 runners-up。

自检：阈值语义、评估触发点、去重、自动停用、FE/CLI **1.41.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity 实时/Push | 单列易溢；非「明显最优」；不重开 |
| 国家假日包 | E56 刚交；连续 SLA 弧过密；版权/年份债 |
| Insights 再厚 / 日报 | E55 刚闭合；宜再沉淀 |
| Search FTS / Customer 门户 / GitHub App / Initiative 依赖图 | 基建或过厚/排除 |
| Formula emit / 重做 E52–E56 表面 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E54 已让 owner「看得见死信并能重试」，但超阈值仍靠人肉刷页——隔开 E55（Insights）+ E56（SLA policy 日历）两轮后，用中厚刀把 **阈值→Inbox/邮件 + 可选自动停用 + 去重** 补上，正好闭合出站集成「账本→可观测→告警」产品弧，且不重开 Push 或假日包大战。

---

## 1. 目标

成功标准：owner 可为 Workspace（及可选 per-hook）配置死信告警阈值；当窗口内 `dead` 计数（或连续失败）达到阈值时，向 **WS owners**（建议）投递 Inbox（类型 `webhook_dead_letter_alert`），并在收件人 `email_enabled` 时走 E30 邮件钩；同一规则在去重桶内不刷屏；可选开启「硬顶自动停用」将该钩 `enabled=false` 并额外通知；FE 在既有 webhooks 设置薄加「告警」折叠 + mute；CLI **1.41.0**；跨租户隔离；**不**引入 PagerDuty/Slack Incoming 新通道、**不** Activity Push、**不**改 E51 事件包 / HMAC、**不**改 E55/E56 主表面、**不** formula emit。

### A · 告警规则模型（BE）

- 存储建议见 **Q1**（默认 **Q1a**：`workspaces.webhook_alert_settings` JSON nullable + 可选 `workspace_webhooks.alert_settings` JSON nullable 覆盖）  
  - 形状建议：`{ enabled: bool, windowHours: int, deadThreshold: int, consecutiveDeadThreshold?: int|null, autoDisable: bool, muteUntil?: iso|null }`  
  - WS 缺省（建议）：`enabled=false`（**opt-in**，见 **Q2**）；`windowHours=24`；`deadThreshold=10`；`consecutiveDeadThreshold=null`（关闭连续计数）；`autoDisable=false`  
  - per-hook：`null` = 继承 WS；对象 = 字段级覆盖（对齐 E56 calendar 风格）  
- 计数定义（建议 **Q3a**）：窗口内该 scope（WS 汇总或单钩）`WebhookDeliveryLog.status='dead'` 的行数；连续 = 同钩按 `created_at` 倒序连续 `dead` 条数（遇 success 打断）  
- 非法 JSON / 阈值 <1 / windowHours 超界 → 400；跨租户 404

### B · 评估与投递路径

- 触发点建议 **Q4a**：**在 `run-due-deliveries` 将某条标记为 `dead` 之后**同步评估该钩（+ WS 汇总）；另提供 `POST /api/webhooks/run-alert-eval` 外部 tick 兜底扫（对齐 E38/E39/E44 外部 tick 模式）  
- 收件人建议 **Q5a**：WS **owners**（角色 owner）；不广播全员  
- 投递：`NotificationService.create(type='webhook_dead_letter_alert', …)` → 尊 E27 pref + E30 email 钩  
- **去重账本**（新建小表或复用通用 delivery ledger）：`(workspace_id, webhook_id|NULL, rule_kind, bucket)` 唯一；建议 bucket = `floor(now / windowHours)` 或日桶（见 **Q6**）；已存在 → skip  
- `autoDisable=true` 且触及硬顶（建议用 `consecutiveDeadThreshold` 或 `deadThreshold` 之二，默认连续阈值优先若设置，否则窗口阈值）：`webhook.enabled=false`；写 `paused_reason='auto_dead_letter_alert'`（新可空列）或 JSON 旁路字段；再发一条 `webhook_auto_disabled` 通知（可与告警同 pref 键，见 Q2）  
- 手动重新 `enabled=true` 清除 `paused_reason`；**不**自动 re-enable

### C · 存储 / migration

- Alembic 一版：WS JSON 设置列 + 钩 JSON 覆盖列 + 可选 `paused_reason` String nullable + 去重账本表  
- SQLite 测友好  
- **禁止**新 webhook 事件名进 E51 pack；**禁止**改 HMAC 签名

### D · FE

- 既有 `settings/webhooks`：顶栏/设置折叠「死信告警」——总开关、窗口、阈值、自动停用、muteUntil；钩详情可覆盖  
- 死信箱行：若钩因告警停用，展示「已自动停用」标签 + 一键启用  
- vitest：normalize merge / 缺省 inherit / mute 期内不展示「待告警」状态（纯函数）  
- **不做**告警路由到第三方（PagerDuty/Slack app）、值班排班、风暴图

### E · CLI **1.41.0**

- `webhook alerts show|set`（WS 级；`--webhook-id` 可选覆盖）  
- `webhook alerts mute --until ISO` / `webhook alerts unmute`  
- `webhook run-alert-eval`（外部 tick）  
- 既有 `dead-letter` / `stats` 保留  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.41.0**

### F · 安全 / 租户 / no-emit

- 告警设置写：owner；读：member+（与 webhook 设置对齐，见现网）  
- 跨租户 404  
- **不**新增 outbound webhook 事件、**不**改 Activity / Insights / SLA  
- formula **no-emit**；告警路径 spy 不触发 `fire_webhooks`（避免告警→webhook→告警环）；不触 automations

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification / 实时 WS 扇出产品化  
- 国家日历包 / ICS 订阅 / SLA 冲突矩阵  
- Insights 报表构建器 / 效能邮件日报  
- PagerDuty / Opsgenie / Slack Incoming 新通道（仅复用 Inbox + 既有 E30 邮件）  
- 重做 E51 事件包 / 重做 E54 stats 形状 / 改 HMAC  
- Formula 物化 emit（E40 D2/D7）  
- Customer 公开门户、GitHub App 安装 UX、Initiative 依赖图、原生移动端、Search FTS  
- 远程 push / 开 PR / 自开 E58

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 默认 opt-in 关闭时永不告警；开启后窗口内 dead≥阈值 → owners 各至多 1 条/桶；跨租户 404 |
| B | `run-due-deliveries` 置 dead 后可触发；`run-alert-eval` 兜底；muteUntil 内 skip；email 尊 E30 |
| C | `autoDisable`：达硬顶 → `enabled=false` + 通知；手动启用恢复；alembic 可升级 |
| D | FE 告警折叠 + 钩覆盖 + 停用标签；vitest；build ok |
| E | CLI **1.41.0** + alerts show/set/mute + run-alert-eval + version pins |
| F | 无新 E51 事件名；告警路径无 fire_webhooks；formula no-emit；不改 E55/E56 主表面 |
| 门禁 | BE 定向（E57+E54+E51/E44 相关）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E58 |

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Webhook 死信告警 mid-thick**（方案 A）；阈值 Inbox/邮件 + 去重 + 可选自动停用并捆；**无** Push / 国家包 / Insights 再厚 / PagerDuty |
| D2 | 设置挂 WS JSON + 可选 per-hook JSON 覆盖；缺省全继承；**默认总闸 opt-in false** |
| D3 | 评估挂 `run-due-deliveries` 置 dead 后 + `run-alert-eval` 外部 tick 兜底 |
| D4 | 去重账本按 bucket 防刷；收件人 = WS owners |
| D5 | FE 落点 = 既有 webhooks 设置薄加；不新开导航 |
| D6 | CLI = **1.41.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；告警路径不 fire_webhooks；不改 E55 Insights / E56 SLA 主表面；非目标见 §2；不 push；不自开 E58 |

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 设置存储形态？ | **Q1a** WS `webhook_alert_settings` JSON + 钩 `alert_settings` JSON 可选覆盖；备选 Q1b 独立 `webhook_alert_rules` 表（多规则，偏厚） |
| Q2 | 默认是否开启告警？通知 pref 键？ | **Q2a opt-in**：WS `enabled=false` 默认；新 pref 键 `webhook_delivery_alert`（默认 true，但受 WS 总闸约束）；`webhook_auto_disabled` 共用同一 pref；备选 Q2b 默认开启 |
| Q3 | 计数口径？ | **Q3a** 窗口内 `status=dead` 行数 + 可选连续 dead；备选 Q3b 用失败率（需 attempts 分母，易抖） |
| Q4 | 何时评估？ | **Q4a** 置 dead 后即时评估 + `run-alert-eval` 兜底；备选 Q4b 仅外部 tick |
| Q5 | 谁收告警？ | **Q5a** WS owners；备选 Q5b owners+钩创建者；Q5c 可配置收件人列表（偏厚，砍） |
| Q6 | 去重桶粒度？ | **Q6a** 按 `windowHours` 对齐的时间桶（同窗同规则一条）；备选 Q6b 自然日桶（简单但与窗口不完全对齐） |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Alembic + settings normalize/merge + 去重账本（TDD）  
3. BE 评估器挂 run-due-deliveries + run-alert-eval + autoDisable（TDD；回归 E54）  
4. FE 告警折叠 + 停用标签  
5. CLI 1.41.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- 总闸关闭 → 无论 dead 多少不告警  
- 阈值边界：threshold-1 不发；=threshold 发 1 次；同桶再 dead 不发  
- muteUntil 内 skip；过期恢复  
- per-hook 覆盖字段级继承  
- autoDisable：达硬顶停用 + 通知；手动启用后可再次告警（新桶）  
- 跨租户；非法 settings  
- spy：告警路径无 `fire_webhooks`；不触 Insights export / SLA calendar / activity cursors  
- CLI 1.41.0 pins + alerts show/set/mute + run-alert-eval  

---

## 附录 · runners-up（供 E58+；若 Yuri 改选可替换本草案）

1. **国家/地区假日包 mid**（CN/US/… 精选包一键合并进 WS 或 policy.calendar.exceptions；按年；仍砍 ICS 订阅 / 冲突矩阵）— E56 覆盖已齐后下一刀日历增强；本轮为轮换出站弧让路。  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非本轮最优。  
3. **Insights 再厚 / 效能日报**（多 label OR、持久化「我的报表」、可选邮件 digest）— E55 刚交中厚；宜再沉淀。  

（备选扫描但本轮不推：Search FTS 基建、Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动 — Roadmap 排除或过厚。Formula emit — 永不本轮。重做 E52–E56 表面 — 无增量，不推。）

## CLI 版本

**1.41.0**
