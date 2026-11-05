# E67 Design：Workspace 时区进 due/recurrence mid — 本地日历日 · CLI 1.51.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E67  
基线拟：`sprint/E66-S1` @ `ea96ebd`（全文 `ea96ebdfe27927172f254d1ecb4dfd191274097e`；E66 design 基线 `0e93813`；E65 tip `8202d69` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E67-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E68**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e67-workspace-timezone-due-recurrence-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E67-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E66 连续闭合 … → Customer 公开状态（E63）→ 假日包扩容（E64）→ Initiative 依赖图（E65）→ **Issue 附件鉴权 mid（E66：会话 ACL + HMAC 签名 URL · CLI 1.50.0）**。

E66 附录 runners-up（不绑定）：

1. **Activity 实时/推送加厚**（WS / Notification / FCM）— 单列易溢；非「明显最优」；**默认不重开**  
2. **Customer 门户再厚** — 任务 **prefer skip**  
3. **Initiative 甘特精修** — E65 刚交依赖；**prefer skip**  
4. **Workspace 时区进 due/recurrence mid** — 复用已有 `workspaces.timezone`；对齐 E35/E39 明示非目标 → **本草案收之（代码实证后）**

任务硬约束：轮换离开 **附件 ACL / Initiative deps / 假日包 / Customer 门户 / Search / Insights** 刚闭弧；Activity Push **勿默认**。

代码实证 @ `ea96ebd`：

| 面 | 现状 |
|----|------|
| WS `timezone` | `workspaces.timezone` IANA 列已有；SLA business hours（E50+）读写齐；CLI `workspace update --timezone` 已有 |
| Due reminders（E39） | `run_due_reminders`：`today = datetime.utcnow().date()`；soon/overdue/`bucket_date` **一律 UTC 日历日**；FE 通知设置文案写死「按 UTC」 |
| Recurrence（E35） | `next_run_at` UTC naive；`run_due` 用 `datetime.utcnow()`；title `{date}` 扩成 **UTC** `YYYY-MM-DD`；FE 明示「时区 UTC」 |
| 附件 ACL | E66 **刚闭**；本轮宜轮换离开 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | runners-up #1–#3 不宜默认；#4 有列可复用、无新表、单 sprint 可改 tick 语义 + FE 文案 + CLI pins；不重开 Push/甘特/门户/附件 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **WS 时区进 due/recurrence mid**：due tick 的「今日」= WS IANA 本地日历日（空 → UTC）；recurrence title `{date}` 同用本地日；`next_run_at` **仍存 UTC naive**（无 migration）；FE 文案去「一律 UTC」；CLI **1.51.0**；**无** Push / 甘特 / 门户 / 附件再开 | **中厚**；接 E66 #4；复用既有列与 SLA 校验；单 sprint 可交付 |
| B | Activity Push | 单列易溢；**默认不重开** |
| C | Customer 门户再厚 | prefer skip |
| D | Initiative 甘特 | prefer skip |
| E | 再开附件 ACL / Search / Insights / 假日 | 刚闭；轮换离开 |
| F | 仅改 FE 文案仍按 UTC 算 | **过薄**；国际站「今天」仍错位 |
| G | 引入 per-user 时区矩阵 / RRULE | **过厚**；E35/E39 已拒 |

**建议拍板：A（Workspace 时区进 due/recurrence mid）。**  
Activity Push、Customer 门户再厚、Initiative 甘特列入附录 runners-up。

自检：本地日语义、空 TZ 回退、无 schema 炸、FE/CLI **1.51.0**、非目标与 no-emit 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 非「明显最优」；任务勿默认 |
| Customer 门户再厚 | prefer skip；刚闭弧轮换 |
| Initiative 甘特 | E65 后 prefer skip |
| 附件 ACL 再开 | 刚闭 E66 |
| 假日 / Search / Insights | 刚闭；轮换离开 |
| per-user TZ / RRULE / 日历 UI | 过厚 |

### Why this Epic now（一句话）

SLA 早已吃 `workspaces.timezone`，但 **到期提醒与周期建单仍锁死 UTC 日历日**——亚太站「今天即将到期 / 每日模板日期」会偏一天；E66 附件鉴权弧刚闭后轮换离开安全/依赖/假日/门户/Search，用中厚刀把 **E35/E39 明示非目标补成「WS 本地日」**，正好让已有时区列真正服务人日节奏，且不重开 Push、甘特或门户。

---

## 1. 目标

成功标准：WS 配置合法 IANA `timezone` 后，`POST …/run-due-reminders` 的 soon/overdue/`bucket_date` 按 **该 TZ 本地日历日**；`POST …/recurrences/run-due` 的 title `{date}`/`{yyyy-mm-dd}` 扩成 **同一本地日**；`timezone` 空或非法 → **UTC**（与 SLA `validate_timezone` 一致风格）；`next_run_at` 存取仍 UTC naive（**无** alembic）；FE 文案与设置提示对齐；CLI **1.51.0**；**不** Activity Push、**不**改 E57–E66 邻面主表面、**不** formula emit。

### A · 共享时区助手（BE）

- 复用 / 薄封 `opentask.services.sla.business_hours.validate_timezone`（或同级 `workspace_time.py`）：  
  `resolve_workspace_tz(ws) -> ZoneInfo`（None/非法 → `UTC`）  
  `local_today(ws, *, now_utc: datetime | None = None) -> date`  
- **不**引入 per-user TZ；**不**改 Issue.due_date 存贮（仍 date / UTC naive datetime 既有形状）

### B · Due reminders（E39 路径）

- `NotificationService.run_due_reminders`：  
  - `today = local_today(workspace)`（允许测试注入 `today=` 仍优先生效）  
  - soon = `[today, today+LEAD_DAYS]`；overdue = `due_d < today`；digest/`bucket_date` 用同一 `today`  
- 文案 title/body 可标注本地日（可选薄）；dedupe key 形状不变（仍含 `bucket_date`）  
- **Q1a**：分类与账本日历日一律 WS 本地；备选 Q1b 仅 Inbox 文案本地、账本仍 UTC（易双轨）

### C · Recurrence（E35 路径）

- `expand_title(..., now)`：`{date}` / `{yyyy-mm-dd}` → **WS 本地** `YYYY-MM-DD`（传入 `local_today` 或 aware now）  
- `run_due` 的 `now` 比较 **仍 UTC naive**（`next_run_at` 不改列、不批量 rewrite）  
- **Q2a**：本轮不改 advance 算法的墙钟语义（daily/weekly/monthly 仍按 UTC `next_run_at` 推进）；只改 title 日期与文档；备选 Q2b 把 advance 锚到本地午夜（易震存量 schedule，拒作默认）  
- FE `settings/recurrences`：去掉「一律 UTC」绝对表述 → 「next_run_at 存 UTC；标题日期按工作区时区」

### D · FE

- `settings/notifications`：到期提醒说明改为「按工作区时区日历日；未设时区则 UTC」  
- `settings/recurrences`：同上  
- SLA 时区选择器仍是写入 `workspaces.timezone` 的主 UI（**Q4a** 不新开「通用时区」页，避免双入口）；可选在通知/周期页加「前往 SLA / 工作区时区」链  
- vitest：本地日边界（如 `Asia/Shanghai` 相对 UTC 跨日）纯函数测；build ok

### E · CLI **1.51.0**

- pins → **1.51.0**  
- `workspace show` 已显 Timezone — 保持  
- help/文案：`inbox` due-reminders / `recurrence run-due` 注明 WS TZ 本地日（**Q6a**）  
- **不**强制新子命令（已有 `--timezone`）

### F · 安全 / 邻面 / no-emit

- 跨租户不变；非法 IANA 写路径仍拒（既有 SLA 校验）  
- **Q5a**：不新增 webhook 事件；tick 不 fire 新出站  
- formula **no-emit**  
- **不**改 E57–E66 主表面（附件 ACL / Initiative relations / 假日包 / 门户 / Search / Insights 仅 pins）  
- 守 E63 `f`+`r` 路由

---

## 2. 非目标

- Activity Push / 浏览器 Notification / FCM  
- Customer 门户再厚、Initiative 甘特、附件 ACL 再开  
- 假日包 ICS/州包/2028、Search / Insights 再开  
- per-user 时区、RRULE、日历拖拽 UI、进程内 cron  
- 批量 rewrite 既有 `next_run_at` / `due_reminder_delivery.bucket_date` 历史行  
- Formula emit；远程 push / 开 PR / 自开 E68

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | WS `Asia/Shanghai`：UTC 16:00 前日 → 本地已次日；due soon/overdue/`bucket_date` 跟本地日 |
| B | recurrence title `{date}` = 本地日；`next_run_at` 无 migration；UTC 比较逻辑仍绿 |
| C | `timezone` null → 行为同今日 UTC（回归 E35/E39） |
| D | FE 文案对齐；vitest 跨日边界；build ok |
| E | CLI **1.51.0** pins + help 注明 |
| F | 无新 webhook；不改 E57–E66 邻面；formula no-emit spy；E63 f+r 仍在 |
| 门禁 | BE 定向（due reminders + recurrences + 新 TZ helper）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E68 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **WS 时区进 due/recurrence mid**（方案 A）；本地日历日 + FE/CLI；**无** Push / 甘特 / 门户 / 附件再开 |
| D2 | 复用 `workspaces.timezone`；空/非法 → UTC；不引入 per-user TZ |
| D3 | due 分类与 dedupe `bucket_date` 用本地日；recurrence **仅** title 本地日；`next_run_at` 仍 UTC naive |
| D4 | 不新开通用时区设置页；SLA/既有 workspace timezone 入口为准 |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.51.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E57–E66 邻面；不 push；不自开 E68 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | due 账本日历？ | **Q1a** soon/overdue/`bucket_date` 一律 WS 本地日；备选 Q1b 账本 UTC、仅文案本地（双轨易懵） |
| Q2 | recurrence advance？ | **Q2a** 本轮不改 advance/墙钟，只改 title 本地日 + 文档；备选 Q2b 锚本地午夜（震存量，拒默认） |
| Q3 | 空 timezone？ | **Q3a** 回退 UTC（与 SLA 风格一致）；备选 Q3b 强制 owner 先设 TZ 否则 tick 400（过噪） |
| Q4 | FE 入口？ | **Q4a** 不新开时区页；通知/周期文案 + 链到既有 SLA/workspace TZ；备选 Q4b 新建「工作区·时区」页（重复） |
| Q5 | webhook？ | **Q5a** 不新增、不 fire；备选 Q5b `workspace.timezone_changed`（本轮无关） |
| Q6 | CLI 表面？ | **Q6a** pins **1.51.0** + due/recurrence help 注明；备选 Q6b 新增 `workspace tz` 子命令（冗余） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. `local_today` / `resolve_workspace_tz` helper + 单测（跨日边界）  
3. due reminders 接本地日（TDD）  
4. recurrence title 扩本地日（TDD）；文档/FE 文案  
5. CLI 1.51.0 pins + help  
6. no-emit / 邻面不动 / E63 f+r spy + acceptance

---

## 7. 测试要点

- WS `Asia/Shanghai`，固定 `now=UTC 2026-11-05 16:30` → 本地 `2026-11-06`；due `2026-11-06` → soon（非 overdue）  
- 同场景 `timezone=None` → 仍按 UTC `2026-11-05`  
- recurrence title `{date}` 随 TZ 变；`next_run_at` 行不被 rewrite  
- 非法 TZ 存库路径仍拒（既有）；resolve 回退 UTC 不抛  
- spy：无新 webhook；不触 E66 signed-url / E65 relations / E64 holiday / E63 status；formula no-emit  
- CLI 1.51.0 pins  
- FE vitest；build ok；elegant-router `f`+`r` 仍在

---

## 附录 · runners-up（供 E68+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— 单列易溢；非「明显最优」不重开。  
2. **Customer 门户再厚 thin-mid**（公开回复线程 UI / Form 成功页深链）— 多轮让路后再评。  
3. **Initiative 甘特/时间线精修** — E65 关系数据已在；有明确排程需求再开。  
4. **Recurrence 本地午夜 advance（Q2b 升级）** — 本 Epic 刻意不震存量 `next_run_at`；若运营需要「每天本地 09:00」再开薄刀。

（备选扫描但本轮不推：附件 ACL 再开 — 刚闭 E66。假日 ICS/州包 — 刚闭 E64。Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / RRULE — 过厚。Formula emit — 永不。）

## CLI 版本

**1.51.0**
