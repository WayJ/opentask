# E59 Design：Insights 再厚 / 效能日报 mid — 多 label OR +「我的报表」+ 可选邮件 digest · CLI 1.43.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E59  
基线拟：`sprint/E58-S1` @ `0494871`（全文 `04948719b6637a5c889d6db3ab292bede135fbdb`；E58 design 基线 `ed17b2d`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E59-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E60**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e59-insights-saved-reports-digest-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E59-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E58 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ Insights 效能加厚（E55）→ SLA policy 日历覆盖（E56）→ Webhook 死信告警（E57）→ **国家/地区假日包（E58：CN+US 2026 静态包 + preview/apply + applied 账本）**。

E58 附录 runners-up（不绑定）：

1. **Insights 再厚 / 效能日报 mid**（多 label OR、持久化「我的报表」、可选邮件 digest；仍砍拖拽报表构建器）— E55 已隔 E56+E57+E58 三轮；假日包让路后下一刀效能面 → **本草案收之**  
2. **Search FTS mid**（Postgres `tsvector` + SQLite FTS5 或统一 trigram 降级；Issue/Project/Doc）— 现网 ILIKE 可规模化前的基建刀；方言测本需控  
3. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」

代码实证 @ `0494871`：

| 面 | 现状 |
|----|------|
| Insights | E24 lite + E55：`summary` 支持单 `projectId`/`labelId`/`cycleId` + `estimateVelocity` + `export.csv`；FE `/insights` 过滤条；CLI `insights summary|export`；**无**多 label OR、**无**持久化「我的报表」、**无**效能邮件 digest |
| SLA 日历 | E50→E53→E56→E58 弧已闭合（周窗→例外→policy overlay→国家包）；本轮宜 **轮换离开** |
| Webhook | E44→E51→E54→E57 出站弧已闭合；再厚 / PagerDuty 非本轮 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification |
| Search | 现网 `ILIKE` 多实体；**无** FTS/tsvector |
| Notif/Email | E27 prefs + E30 `email_enabled` + E39 due-reminder digest + 外部 tick；可复用「账本去重 + Inbox + 邮件钩」模式给 Insights digest |
| Saved Views | Issue 列表有 personal/shared saved views；Insights **无**对等「我的报表」 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | 厚 Linear 主面近期已交；E58 闭合 SLA 日历产品弧后，最高 ROI 缺口回到 **效能面二次刀**——E55 明示砍掉的多 label / 持久化报表 / 邮件日报正是日常用法缺口；且明确要求轮换离开刚闭的 SLA 日历弧 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Insights 再厚 / 效能日报 mid**：summary/export 支持 **多 label OR**（`labelIds`）；新增 **个人「我的报表」**（命名切片预设：project/label(s)/cycle + 可选窗口）；可选 **效能 digest**（外部 tick → Inbox `insights_digest` + 尊 `email_enabled` 走 E30）；FE `/insights` 薄加「我的报表」条 + digest 开关；CLI **1.43.0**；**无**拖拽报表构建器 / **无** BI 大屏 / **无** Slack Incoming / **无** Activity Push / **不**改 E58 SLA / E57 webhook | **中厚且轮换离开 SLA 日历弧**；接 E55 明示让路项；复用 E39 tick/账本模式可控；单 sprint 可交付 |
| B | Search FTS mid（PG tsvector + SQLite FTS5） | 用户面有价值但偏基建；方言分叉测本大；作 runners-up |
| C | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | 单列易溢；仓内 realtime≠产品闭环；**默认不重开** |
| D | 再开 SLA 日历（更多国家包 / ICS / 冲突矩阵） | **刚闭 E50→E58**；与「轮换离开」冲突；非最高 ROI |
| E | Customer 公开门户 / 真 GitHub App / Initiative 依赖图 / Formula emit | 门户·App·依赖图偏厚或排除；emit **永不** |
| F | 仅多 label OR、无「我的报表」/无 digest | **过薄**；与 prefer mid-thick 冲突 |

**建议拍板：A（Insights 再厚 / 效能日报 mid）。**  
Search FTS、Activity Push、（可选）更多国家包列入附录 runners-up。

自检：多 label 语义、「我的报表」存哪、digest 收件人/去重/tick、FE/CLI **1.43.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Search FTS | 偏基建；方言双栈测本；Insights 产品债更贴日常 |
| Activity 实时/Push | 单列易溢；非「明显最优」；不重开 |
| 再开 SLA 日历 / ICS / 州包 | E58 刚闭弧；明确要求轮换离开 |
| Customer 门户 / GitHub App / Initiative 依赖图 | 过厚或排除 |
| 再开 webhook / Formula emit / 重做 E52–E58 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E55 已让成员「能按单项目/标签切片、看估点速度、导出 CSV」，但多标签组合、一键回到常用切片、以及「不用每天打开 Insights」的邮件摘要仍缺——E56→E58 刚把 SLA 日历弧闭完后轮换回来，用中厚刀把 **多 label OR +「我的报表」+ 可选效能 digest** 补上，正好把效能面从「能看」抬到「能复用 / 能送上门」，且不重开 Push、报表构建器或 SLA 大战。

---

## 1. 目标

成功标准：Workspace 成员（viewer+，对齐 E24/E55）可对 Insights summary/export 使用 **多 label OR** 过滤；可 **CRUD 个人「我的报表」**（命名切片预设，至少含 projectId / labelIds / cycleId）；可选开启 **效能 digest**（外部 tick 按预设或默认切片写 Inbox，尊 `email_enabled` 走 E30 邮件）；FE `/insights` 薄加「我的报表」条 + digest 开关；CLI **1.43.0**；跨租户隔离；聚合仍 SQL `GROUP BY`（禁 N+1）；**不**引入拖拽报表构建器、**不** Slack Incoming、**不** Activity Push、**不**改 E58 SLA / E57 webhook 主表面、**不** formula emit。

### A · 多 label OR（BE）

- 扩展 `GET /api/insights/summary` 与 `GET /api/insights/export.csv`：  
  - 新增 `labelIds`（重复 query 或逗号分隔；**Q1**）— **OR** 语义（Issue 命中任一即可）  
  - 保留既有单 `labelId` 作兼容别名（与 `labelIds=[id]` 等价；两者同传时以 `labelIds` 为准或 400 — **Q1a** 建议：同传 → 400）  
  - 非法 / 跨租户 label → 404（对齐 E55）  
- 过滤作用于 status/priority/assignee/createdVsCompleted/estimateVelocity；`cycleSnapshot` 在显式 `cycleId` 或默认 active 时 **一并收窄**（对齐 E55 Q2a）  
- **不做** AND 语义、**不做**「无标签」特殊哨兵（可用既有未分配逻辑若已有；本轮不扩）

### B ·「我的报表」Saved Insights Reports（BE）

- 新表建议 `insights_saved_reports`（**Q2**）：  
  - `id`, `workspace_id`, `owner_user_id`, `name`, `filters` JSON（`{ projectId?, labelIds?, cycleId?, assigneeLimit? }`）, `created_at`, `updated_at`  
  - 范围：**仅 personal**（本轮不做 shared；**Q3a**）  
  - 上限建议每用户每 WS **20** 条（防炸）  
- API：  
  - `GET /api/insights/reports` → 当前用户列表  
  - `POST /api/insights/reports` → 创建  
  - `PATCH /api/insights/reports/{id}` / `DELETE …`  
  - `GET /api/insights/reports/{id}/summary`（可选便利；或 FE 读 filters 再打既有 summary — **Q4a** 建议 FE 组合，少一跳）  
- 跨租户 / 非本人 → 404；viewer+ 可读写 **自己的**；不做 owner-only 管理面

### C · 效能 digest（BE）

- 偏好：在既有 notif prefs 增 `insights_digest` bool（默认 **false**；类 E39 `due_reminder_digest`）  
- Inbox type：`insights_digest`（映射到同一 pref 门）  
- 外部 tick：`POST /api/insights/run-digest`（owner 或对齐 E39 的 tick 权限；**Q5**）  
  - 对开启 `insights_digest` 的成员：取 **默认报表**（见 Q6）或 WS 级默认切片 → 跑 summary → 写 1 条 Inbox（扁平行：status top / velocity 合计 / createdVsCompleted 窗口和）  
  - 去重账本：`(workspace_id, user_id, bucket_date)` 唯一；同日再 tick **不改写**（对齐 E39 D5）  
  - 邮件：Inbox create 后走既有 `_maybe_send_email`（尊 `email_enabled` + SMTP 配置）  
- **不做**内置 cron；**不做** per-report 多封并行（本轮最多每用户每日 1 封）

### D · FE

- `/insights`：Label 多选（OR 提示）；「我的报表」下拉（应用 / 另存为 / 删除）；digest 开关入口（链到既有 notif prefs 或本地折叠）  
- vitest：labelIds 归一化、OR 空集=不过滤、报表 filters round-trip  
- **不做**拖拽自定义报表、多看板并存、分享报表到 WS

### E · CLI **1.43.0**

- `insights summary [--project-id] [--label-id] [--label-ids id,id] [--cycle] [--json]`  
- `insights export …`（同筛）  
- `insights reports list|create|delete`（薄 CRUD）  
- `insights run-digest [--yes]`（tick）  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.43.0**

### F · 安全 / 租户 / no-emit

- 读权限对齐 E24/E55（viewer+）；tick 写对齐 E39  
- 跨租户 404；label/project id 白名单校验  
- **不**新增 outbound webhook 事件、**不**改 fire 路径、**不**改 SLA / Webhook 告警 / Activity 主表面  
- formula **no-emit**；读路径与 digest 路径 spy 不触发 `fire_webhooks` / automations（除 Inbox/邮件既有副作用）

## 2. 非目标

- 拖拽自定义报表构建器 / 任意维度 / 持久化共享「团队报表」大战  
- Slack Incoming / PagerDuty / 浏览器 Notification / Activity Push / FCM  
- Search FTS / tsvector / trigram 替换 ILIKE  
- 再开 SLA 日历（ICS、州包、冲突矩阵、更多国家包主表面）  
- 改 E57 webhook 告警 / E58 holiday-packs / E51 pack/HMAC  
- Formula 物化 emit（E40 D2/D7）  
- Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动  
- 内置 cron / Celery beat（外部 tick only）  
- 远程 push / 开 PR / 自开 E60

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | 单 `labelId` 回归 E55；`labelIds` OR 收窄计数；非法/跨租户 404；同传冲突按 Q1 处理 |
| B | 个人报表 CRUD；上限；非本人/跨租户 404；filters 应用到 summary 结果一致 |
| C | `insights_digest` 默认关；tick 开则每用户每日 ≤1 条；尊 email_enabled；同日幂等 |
| D | FE 多选 label + 我的报表 + digest 入口；vitest；build ok |
| E | CLI **1.43.0** + summary/export 多 label + reports CRUD + run-digest + pins |
| F | 无新 webhook 事件名；formula no-emit spy；不改 E57/E58 主表面 |
| 门禁 | BE 定向（E59+E55+E24 insights + digest 相关）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E60 |

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Insights 再厚 / 效能日报 mid**（方案 A）；多 label OR +「我的报表」+ 可选邮件 digest 并捆；**无** Push / FTS / SLA 再开 / 报表构建器 |
| D2 | 过滤仍挂既有 `GET /api/insights/summary`（+ export.csv）；不新建第二套聚合引擎 |
| D3 | 多 label = **OR**；单 `labelId` 保留兼容 |
| D4 | 「我的报表」= **personal-only** JSON filters 表；不做 shared；每用户每 WS cap 20 |
| D5 | digest = 外部 tick + Inbox + E30 邮件钩 + 日账本去重；默认关 |
| D6 | CLI = **1.43.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E57 webhook 告警 / E58 SLA 假日包主表面；非目标见 §2；不 push；不自开 E60 |

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | `labelIds` 传参形态？与单 `labelId` 同传？ | **Q1a** 支持重复 query `labelIds=1&labelIds=2` **与** 逗号串；与 `labelId` 同传 → **400**；空数组=不过滤。备选 Q1b 同传时合并去重（易歧义） |
| Q2 | 「我的报表」存哪？ | **Q2a** 新表 `insights_saved_reports` + alembic；备选 Q2b 塞进既有 saved_views 用 type 区分（耦合 Issue 视图，砍） |
| Q3 | 是否支持 shared 报表？ | **Q3a personal-only**（中厚可控）；备选 Q3b personal+shared（偏厚，砍） |
| Q4 | 应用报表是否要专用 summary 端点？ | **Q4a** FE/CLI 读 filters 再打既有 summary（少表面）；备选 Q4b `GET …/reports/{id}/summary` |
| Q5 | digest tick 权限与默认切片？ | **Q5a** 对齐 E39：WS owner（或现 tick 角色）可触发；对每用户用其 **default report**（见 Q6），无则用「全 WS + 默认 14d」切片。备选 Q5b 仅自助 `run-my-digest`（运维不便） |
| Q6 | 用户如何指定 digest 用哪份报表？ | **Q6a** 报表可标 `isDefault=true`（每用户至多 1）；无默认 → 全 WS 切片。备选 Q6b 独立 pref 存 reportId |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE 多 label OR + 回归 E55/E24（TDD）  
3. BE insights_saved_reports CRUD + alembic（TDD）  
4. BE digest pref + run-digest + 账本（TDD；复用 E30/E39 邮件钩）  
5. FE 多选 + 我的报表 + digest 入口  
6. CLI 1.43.0  
7. 门禁 + acceptance tip  

## 7. 测试要点

- 单 labelId 回归；labelIds OR；同传 400；跨租户 label/project  
- 报表 CRUD / cap 20 / 非本人 404；filters → summary 对账  
- digest 默认关；开后同日二次 tick 不双投；email_enabled 关则仅 Inbox  
- spy：无 fire_webhooks；不触 E57 alert eval / E58 holiday apply；formula no-emit  
- CLI 1.43.0 pins + 新参数/子命令  

---

## 附录 · runners-up（供 E60+；若 Yuri 改选可替换本草案）

1. **Search FTS mid**（Postgres `tsvector` + SQLite FTS5 或统一 trigram 降级；Issue/Project/Doc）— 现网 ILIKE 可规模化前的基建刀；方言测本需控。  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」不重开。  
3. **假日包扩容 thin**（再加 EU/UK 或 2027 年文件；仍砍 ICS / 州包 / 外网拉取）— E58 刚交；非轮换优先；作附录备选。

（备选扫描但本轮不推：Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动 — Roadmap 排除或过厚。Webhook 再厚 / PagerDuty — 出站弧已闭，轮换离开。Formula emit — 永不本轮。重做 E52–E58 表面 — 无增量，不推。）

## CLI 版本

**1.43.0**
