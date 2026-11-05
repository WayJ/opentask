# E54 Design：Webhook 投递可观测加厚 mid-thick — 指标 + 死信箱 · CLI 1.38.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E54  
基线拟：`sprint/E53-S1` @ `0eeb1d1`（全文 `0eeb1d1269ce58073dffdd6bdf1b3573fc07c80d`；design 基线 `5fbb63e`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E54-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E55**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e54-webhook-delivery-observability-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E54-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E53 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性（E44）→ SLA v2 → Formula query → Activity Feed v1（E47）→ SLA first-response → Formula Display v2 → SLA business hours（E50）→ 专用 webhook pack + 订阅过滤 FE（E51）→ Activity 加厚 v2（E52）→ **SLA 节假日/例外日 thin（E53）**。

E53 附录 runners-up（不绑定）：

1. **Webhook 投递可观测加厚**（按钩子成功率仪表 / 死信箱 UI）— 偏运维；单列偏薄，宜与小刀并捆成中厚  
2. **Activity 实时/Push 加厚**（WS 扇出 / 浏览器 Notification）— E52 刚交薄铃铛；单 sprint 易溢  
3. **SLA policy 级日历覆盖 thin**（仍砍完整优先级矩阵）— E53 刚闭合 WS 例外；默认再隔

代码实证 @ `0eeb1d1`：

| 面 | 现状 |
|----|------|
| Webhook 投递账本 | E44：`WebhookDeliveryLog`（success / pending_retry / dead + payload）；`run-due-deliveries`；单条 replay；FE 详情失败过滤 + 行内重试；CLI `deliveries` / `retry` / `run-due` |
| E51 | 专用事件包 + 订阅过滤 FE；投递日志可按 **event** 过滤；**仍无**成功率仪表 / WS 级死信箱专页 / 聚合指标 API |
| FE webhooks | `settings/webhooks` ~404 行：钩子详情内 deliveries 表；**无**顶栏指标卡、**无**跨钩子 dead inbox、**无**时间窗聚合 |
| API | `GET /{webhook_id}` 含 deliveries；**无** `GET …/stats`；**无** WS 级 `dead-letter` 列表；**无** bulk retry |
| CLI | **1.37.0**；下一刀 **1.38.0** |
| SLA | E50–E53 周窗+例外齐；policy 覆盖刻意未做 |
| Activity | E52 watching+反应+铃铛；**无** Push / 实时 WS |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | Initiatives/Docs、Estimates、Relations、Customer、Insights、Git-PR、Search 等厚 Linear 面近期已交；当前最高 ROI 缺口落在 **出站集成可观测**（E44 账本已齐、产品化仪表未齐），而非再开 SLA/Activity 大战 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Webhook 投递可观测 mid-thick**：按钩子（+可选 WS 汇总）成功率/计数/延迟指标 API + **跨钩子死信箱** FE（过滤 + 单条/批量重试）+ 设置页顶栏指标卡 + CLI **1.38.0**（`webhook stats` / `webhook dead-letter …`）；**不**改 HMAC / **不**扩 E51 事件包 / **不**引入进程内 cron | **中厚且连贯**；把「偏薄运维刀」捆成可交付 Epic；E51 已隔 E52+E53 两轮 |
| B | Activity 实时/Push（浏览器 Notification / FCM / WS 扇出） | E52 刚厚；单 sprint 易溢；默认再隔 |
| C | SLA policy 级营业时/例外覆盖 thin | E53 刚交 WS 例外；再开日历层 ROI 弱；除非多品牌强信号 |
| D | 仅死信箱 UI **或**仅指标卡（不并捆） | **过薄**；与 prefer mid-thick 冲突 |
| E | Formula emit / 重做 E51 pack / 重做 E52 Activity / 重做 E53 例外 | 破 D7 或无增量；**永不本轮** |

**拍板：A（Webhook 投递可观测 mid-thick）。**  
Activity Push、SLA policy 日历列入附录供 E55+ / runners-up。

自检：指标语义、死信箱范围、权限、FE/CLI **1.38.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity 实时/Push | E52 铃铛落地未满两轮产品观察；Push/WS 必溢 |
| SLA policy 日历覆盖 | E53 刚闭合例外弧；再叠 policy 易变厚且信号弱 |
| 仅指标或仅死信（不并捆） | 单列撑不起 Epic 厚度（E52/E53 附录已指出） |
| Formula emit / 重做 E50–E53 SLA / E51–E52 表面 | 无增量或破 D7；永不本轮 |
| Initiatives 依赖图 / 原生移动 / Redis 真队列 | Roadmap 明确排除或运维面过大 |

### Why this Epic now（一句话）

E44 已有失败可恢复的投递账本，E51 已把「订什么事件」产品化；集成方下一个痛点是 **「钩子到底稳不稳、死信堆在哪」**。隔开 E52（Activity）+ E53（SLA 日历）后，把 **成功率/延迟指标 + 跨钩子死信箱** 捆成中厚刀，正好闭合 webhook 运维弧，且不重开 Push 或 SLA policy 大战。

---

## 1. 目标

成功标准：工作区 Owner（对齐现 webhook 设置权限）可查看 **按钩子（及可选 WS 汇总）** 的投递指标（时间窗内成功/失败/死信计数、成功率、可选延迟摘要）；可打开 **跨钩子死信箱** 浏览 `status=dead` 投递并单条/批量重试（复用 E44 replay 语义）；FE 设置页顶栏指标卡 + 死信箱入口；CLI **1.38.0**；跨租户隔离；**不**引入 Redis/Celery、**不**改 HMAC 主算法、**不**扩 E51 事件名、**不**改 E52 Activity / E53 SLA、**不** formula emit。

### A · 投递指标 API（BE）

- 新读路径（建议挂现有 webhooks router）：  
  - `GET /api/webhooks/stats?window=24h|7d|30d` → WS 汇总 + 按 `webhook_id` 分解  
  - `GET /api/webhooks/{id}/stats?window=…` → 单钩子  
- 指标字段建议（**Q1**）：`{ window, totals: { success, pending_retry, dead, attempts }, successRate, latencyMs?: { p50, p95 } }`  
  - `successRate` = success / (success + dead + 仍 pending_retry？) — **Q2** 分母口径  
- 只读；按 `workspace_id` 过滤；跨租户 404  
- **禁止**为指标物化新事实表（本轮扫 `WebhookDeliveryLog`；可选时间索引沿用既有）

### B · 跨钩子死信箱（BE）

- `GET /api/webhooks/dead-letter?limit=&cursor=&webhook_id=&event=` → 仅 `status=dead`，跨钩子，新→旧  
- 单条重试：沿用 E44 `POST /{webhook_id}/deliveries/{delivery_log_id}/retry`  
- 批量重试（**Q3**）：`POST /api/webhooks/dead-letter/retry` body `{ deliveryLogIds: string[] }`（cap 如 50）；逐条复用 replay；部分失败返回 per-id 结果  
- **不做**「dismiss/归档死信」持久态（**Q4a** 本轮不做；避免新列）——死信保留直到成功 replay 或自然被日志保留策略清理（若已有保留策略则不改）

### C · FE

- `settings/webhooks` 顶栏：时间窗切换 + 汇总成功率/死信数卡片；点死信数进入死信箱抽屉/子页  
- 死信箱：跨钩子表（时间、钩子名、event、statusCode、error、重试按钮）；支持按钩子/事件过滤；可选「批量重试所选」  
- 单钩子详情：保留 E44/E51 列表，可嵌入迷你成功率  
- vitest：stats 归一化 / dead-letter 过滤样例  
- **不做**完整 Grafana 式图表大战、告警订阅、邮件日报

### D · CLI **1.38.0**

- `webhook stats [--webhook-id] [--window 24h|7d|30d] [--json]`  
- `webhook dead-letter list [--webhook-id] [--event] [--json]`  
- `webhook dead-letter retry --id …`（可重复 / 或 `--ids a,b`）  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.38.0**

### E · 安全 / 租户 / no-emit

- 读写权限对齐 E29/E44 webhook 设置（Owner；member 只读若现网已如此则保持）  
- 跨租户 404；批量 cap；window 白名单  
- 本 Epic **只读指标 + 复用既有 replay 写路径**；**不**新增 webhook 事件、**不**改 fire 路径契约  
- formula **no-emit**；不改 SLA / Activity 主表面  
- 无 Redis / 进程内 cron（`run-due-deliveries` 外部 tick 保持）

## 2. 非目标

- 扩 E51 专用事件包 / 改订阅事件白名单  
- 改 HMAC 算法 / 签名头 / payload envelope 主契约  
- Redis / Celery / 进程内 cron  
- Activity Push / FCM / 实时 WS / 浏览器 Notification  
- SLA policy 级日历覆盖 / 国家日历包 / 重做 E53 例外  
- Formula 物化 emit（E40 D2/D7）  
- 死信「归档/忽略」持久态、告警规则引擎、邮件/Slack 失败日报  
- 完整 APM/Grafana、按客户计费级 Insights  
- 远程 push / 开 PR / 自开 E55

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | `GET …/stats` 返回窗口内计数 + successRate；非法 window → 400；跨租户 404 |
| B | 单钩子 stats 与 WS 汇总一致可对账（分解之和 = 汇总，允许空钩子） |
| C | dead-letter 列表仅 `dead`；可按 webhook/event 过滤；单条 retry 成功后该条离开 dead（或变 success） |
| D | 批量 retry（若 Q3a）cap 内部分失败可观测；超 cap → 400 |
| E | FE 顶栏指标卡 + 死信箱 + vitest；build ok |
| F | CLI **1.38.0** + stats/dead-letter 命令 + version pins |
| G | 不新增 webhook 事件名；formula no-emit spy；不改 E52/E53 主表面 |
| 门禁 | BE 定向（E54+E44+E51 webhook）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E55 |

## 4. ADR（Yuri 已确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Webhook 投递可观测 mid-thick**（方案 A）；指标 + 死信箱并捆；**无** Push / SLA policy / 事件包扩容 |
| D2 | 指标扫既有 `WebhookDeliveryLog`；本轮不物化汇总表 |
| D3 | 死信箱 = WS 级 `status=dead` 视图；replay 语义复用 E44 |
| D4 | FE 落点 = 既有 `settings/webhooks` 加厚（顶栏 + 抽屉/子页）；不新开独立 App 导航大战 |
| D5 | CLI = **1.38.0** |
| D6 | 守 E40 D2/D7：本 Epic **永不** formula emit；不扩 E51 pack；不改 E52 Activity / E53 SLA；非目标见 §2；不 push；不自开 E55 |

## 5. 开放问题（已全部按建议关闭）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 指标是否含延迟分位（p50/p95），还是只做计数+成功率？ | **Q1a 计数+成功率必做；延迟 p50/p95 若 `latency_ms` 列已有则一并做**（E44 已记 latency）；若缺列则本轮只做计数 |
| Q2 | successRate 分母是否含 `pending_retry`？ | **Q2a 分母 = success + dead + pending_retry**（「已尝试未稳」也进分母）；备选 Q2b 仅 success+dead |
| Q3 | 是否做批量 retry？ | **Q3a 做**（cap 50）；死信箱主路径需要；备选 Q3b 仅单条 |
| Q4 | 是否做 dead「dismiss/忽略」？ | **Q4a 不做**（免新列/新语义）；备选 Q4b 加 `dismissed_at` |
| Q5 | 默认时间窗？ | **Q5a 7d**（FE/CLI 默认）；备选 Q5b 24h |
| Q6 | CLI 子命令挂点？ | **Q6a** `webhook stats` + `webhook dead-letter list\|retry`（挂既有 webhook 组） |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE stats 聚合纯函数/查询 + 单测（TDD）  
3. BE dead-letter list + bulk retry（TDD）  
4. FE 顶栏指标卡 + 死信箱  
5. CLI 1.38.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- stats：空窗、跨窗边界、按钩子分解之和、跨租户  
- dead-letter：只返回 dead；过滤；retry 后状态迁移；bulk 部分失败  
- 权限：非 Owner 行为与现网 webhook 一致  
- spy：无新增 fire_webhooks 事件名；formula no-emit；不触碰 SLA exceptions / Activity cursors  
- CLI 1.38.0 pins + 新命令  

---

## 附录 · runners-up（供 E55+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢。  
2. **SLA policy 级营业时/例外覆盖 thin**（仍砍完整优先级矩阵 / 国家包）— 仅多品牌支持台强需求时开；E53 刚交 WS 例外宜再沉淀。  
3. **Webhook 失败告警薄刀**（Inbox/email 当死信超过阈值）— 可挂在本 Epic 之后；本轮刻意不做告警引擎。

（Formula emit — 永不本轮。重做 E51 webhook pack / E52 Activity / E53 例外 — 无增量，不推。）

## CLI 版本

**1.38.0**
