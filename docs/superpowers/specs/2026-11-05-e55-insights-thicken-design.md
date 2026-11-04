# E55 Design：Insights 效能加厚 mid-thick — 切片过滤 + 估点速度 + CSV · CLI 1.39.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E55  
基线拟：`sprint/E54-S1` @ `db42d7e`（全文 `db42d7e87a0d7222cc1a8b08846175f9e20e47e0`；内容 tip `4e82871`；design 基线 `7dc7f56`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E55-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E56**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e55-insights-thicken-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E55-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E54 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours → webhook pack → Activity 加厚 → SLA 例外日 → **Webhook 投递可观测（E54：stats + 死信箱）**。

E54 附录 runners-up（不绑定）：

1. **Activity 实时/Push 加厚**（WS 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢  
2. **SLA policy 级营业时/例外覆盖 thin**（仍砍完整优先级矩阵 / 国家包）— E53 刚交 WS 例外；可隔一轮再开  
3. **Webhook 失败告警薄刀**（Inbox/email 当死信超过阈值）— E54 刚闭合可观测；单列过薄，默认再隔

代码实证 @ `db42d7e`：

| 面 | 现状 |
|----|------|
| Insights | E24 lite：`GET /api/insights/summary`（status/priority/assignee + cycleSnapshot + 近 14 日 createdVsCompleted）；FE `/insights`；CLI `insights summary`；**无** project/label 切片、**无**估点速度序列、**无** CSV 导出 |
| SLA | E50–E53 周窗+例外齐；**policy 级日历覆盖刻意未做** |
| Webhook | E44 账本 + E51 pack + E54 stats/死信箱齐；**无**告警引擎 / 失败日报 |
| Activity | E52 watching+反应+铃铛；**无** Push / 实时 WS |
| Formula | E40 D2/D7 **永不 emit** |
| Customer / Relations / Git-PR / Estimates / Initiatives | 厚主面近期已交；残差多为更厚二次刀（门户、依赖图、真 GitHub App）或运维面 |
| Roadmap 扫描 | 当前最高 ROI 缺口落在 **效能只读面产品化**（E24 明确 lite），而非再开 Push / 死信告警 / 立刻叠 SLA policy |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Insights 效能加厚 mid-thick**：summary **可按 project / label(tag) / cycle 切片**；新增 **估点速度**（近 N 日 completed points 日桶 + 可选 cycle 内 points）；**CSV 导出**（summary 切片）；FE 过滤条 + 速度卡 + 导出；CLI **1.39.0**（`insights summary` 增筛 + `insights export`）；**不**做自定义报表构建器 / BI 大屏 / Slack 推送 | **中厚且 Linear 对齐**；补 E24 明示砍掉的过滤/导出/估点趋势；跳出 E50–E54 的 SLA↔webhook↔Activity 循环 |
| B | SLA policy 级营业时/例外覆盖 thin | E53 刚闭合 WS 例外；再叠 policy 易变厚且多品牌信号弱；**可作附录** |
| C | Activity 实时/Push | E52 刚厚；Push/WS/FCM 单 sprint 必溢；默认再隔 |
| D | Webhook 死信告警薄刀（阈值→Inbox/email） | E54 刚交可观测；单列过薄；宜再沉淀或与更厚刀并捆 |
| E | Customer Requests 加深 / Search FTS / GitHub App / Initiative 依赖图 / 原生移动 / Formula emit | 门户·App·依赖图偏厚或排除；FTS 偏基建；emit **永不** |

**拍板：A（Insights 效能加厚 mid-thick）。**  
SLA policy 日历、Activity Push、Webhook 告警列入附录供 E56+ / runners-up。

自检：过滤语义、估点速度口径、CSV 边界、权限、FE/CLI **1.39.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| SLA policy 日历覆盖 | E53 刚闭合例外弧；E54 才隔一轮；无多品牌强信号则 ROI 弱于 Insights 产品化 |
| Activity 实时/Push | E52 铃铛未满产品观察；Push/WS 必溢 |
| Webhook 死信告警 | E54 刚交仪表+死信；告警引擎单列过薄 |
| Customer / Relations / Estimates / Git-PR App / Initiative 依赖图 | 主面已交或明确排除/过厚；非当前最高缺口 |
| Formula emit / 重做 E50–E54 表面 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E24 只交付「能看一眼」的 WS 级 summary；E50–E54 把 SLA/集成/Activity 运维弧闭合后，效能面仍缺 **按项目/标签切片、估点速度、可导出**——这正是 Linear Insights 日常用法。隔开运维大战后用中厚刀把 Insights 从 lite 抬到可用，比立刻叠 SLA policy 或 Push 更贴产品主路径。

---

## 1. 目标

成功标准：Workspace 成员（viewer+，对齐 E24）可对 Insights summary **按 project / label(tag) / cycle 过滤**；可查看 **估点完成速度**（日桶 completed `estimate_points`）；可 **导出 CSV**；FE `/insights` 过滤条 + 速度卡 + 导出按钮；CLI **1.39.0**；跨租户隔离；聚合仍 SQL `GROUP BY`（禁 N+1）；**不**引入自定义报表构建器、**不** Slack/邮件日报、**不**改 E52 Activity / E53 SLA / E54 webhook、**不** formula emit。

### A · Summary 切片过滤（BE）

- 扩展 `GET /api/insights/summary` query（建议）：  
  - `projectId`（可选；跨租户 → 404）  
  - `labelId` / `tagId`（可选；与现网 Labels/Tags 命名对齐，**Q1**）  
  - 保留既有 `cycleId` / `assigneeLimit`  
- 过滤作用于 status/priority/assignee/createdVsCompleted；`cycleSnapshot` 在显式 `cycleId` 或默认 active 时仍按 cycle 语义（**Q2**：过滤 project/label 是否同时收窄 cycleSnapshot）  
- 非法组合 / 未知 id → 400 或 404（与现网资源风格一致）

### B · 估点速度（BE）

- summary 增字段建议：`estimateVelocity: { windowDays, buckets: [{ date, completedPoints }] }`（**Q3** 窗口默认 14，对齐 createdVsCompleted）  
- 口径：完成日桶内 `Σ coalesce(estimate_points, 0)`，完成时刻对齐 E24（`coalesce(closed_at, resolved_at)`）  
- **不做**预测/置信区间/仿真 burn-down 大战

### C · CSV 导出（BE）

- `GET /api/insights/export.csv?…`（同 summary 过滤；**Q4**）或 `Accept: text/csv` 同路径二选一  
- 导出内容：至少 statusCounts / priorityCounts / assigneeCounts / estimateVelocity buckets（扁平行）；上限防炸（如 10k 行级，本轮聚合本就小）  
- 只读；跨租户 404

### D · FE

- `/insights`：Project / Label 下拉（可空=全 WS）+ 既有 Cycle；速度折线/柱（Naive 轻量，**不**新引重 BI）  
- 「导出 CSV」按钮  
- vitest：过滤参数归一化 / velocity 空窗样例  
- **不做**拖拽自定义报表、多看板并存

### E · CLI **1.39.0**

- `insights summary [--project-id] [--label-id] [--cycle] [--json]`  
- `insights export [--project-id] [--label-id] [--cycle] [-o path]`  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.39.0**

### F · 安全 / 租户 / no-emit

- 读权限对齐 E24（viewer+）  
- 跨租户 404；过滤 id 白名单校验  
- **不**新增 webhook 事件、**不**改 fire 路径、**不**改 SLA / Activity 主表面  
- formula **no-emit**；读路径 spy 不触发 fire_webhooks / automations

## 2. 非目标

- 自定义报表构建器 / 任意维度拖拽 / 持久化「我的报表」  
- Slack / 邮件 Insights 日报、Webhook 死信告警引擎  
- Activity Push / FCM / 实时 WS / 浏览器 Notification  
- SLA policy 级日历覆盖 / 国家日历包 / 重做 E53 例外  
- 扩 E51 事件包 / 改 HMAC / Redis / Celery  
- Formula 物化 emit（E40 D2/D7）  
- Customer 公开门户大战、GitHub App 安装 UX、Initiative 依赖图、原生移动端  
- 远程 push / 开 PR / 自开 E56

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | summary 无过滤 ≡ E24 行为（回归）；`projectId`/`labelId` 收窄计数；跨租户 404 |
| B | estimateVelocity 日桶点数与手工样例一致；空窗可空数组 |
| C | export.csv 含关键切片；同过滤参数与 JSON summary 对账 |
| D | FE 过滤 + 速度卡 + 导出 + vitest；build ok |
| E | CLI **1.39.0** + summary 筛 + export + version pins |
| F | 不新增 webhook 事件名；formula no-emit spy；不改 E52/E53/E54 主表面 |
| 门禁 | BE 定向（E55+E24 insights）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E56 |

## 4. ADR（Yuri 已确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Insights 效能加厚 mid-thick**（方案 A）；过滤 + 估点速度 + CSV 并捆；**无** Push / SLA policy / 死信告警 / 报表构建器 |
| D2 | 过滤挂既有 `GET /api/insights/summary` query；不新建第二套聚合引擎 |
| D3 | 估点速度 = 完成日桶 `Σ estimate_points`；窗口默认对齐 createdVsCompleted（14d，可 Q3 调） |
| D4 | CSV = 只读导出端点；不持久化导出任务表 |
| D5 | FE 落点 = 既有 `/insights` 加厚；不新开导航大战 |
| D6 | CLI = **1.39.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E52 Activity / E53 SLA / E54 webhook 主表面；非目标见 §2；不 push；不自开 E56 |

## 5. 开放问题（已全部按建议关闭）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 标签过滤参数名 `labelId` 还是 `tagId`？ | **Q1a `labelId`**（对外 Linear 语；内部映射现 Tag 表）；备选 Q1b `tagId` 直出 |
| Q2 | project/label 过滤是否同时收窄 `cycleSnapshot`？ | **Q2a 收窄**（切片一致）；备选 Q2b cycleSnapshot 始终全 cycle，仅其它块过滤 |
| Q3 | estimateVelocity 窗口？ | **Q3a 14d**（对齐 createdVsCompleted）；备选 Q3b 独立 `velocityDays` query |
| Q4 | CSV 独立路径还是同 summary 内容协商？ | **Q4a `GET /api/insights/export.csv`**（清晰）；备选 Q4b `Accept: text/csv` |
| Q5 | 多 label 过滤（AND/OR）？ | **Q5a 本轮单 labelId**（中厚可控）；备选 Q5b 多 id OR |
| Q6 | CLI export 默认 stdout 还是强制 `-o`？ | **Q6a stdout 默认** + 可选 `-o`；备选 Q6b 强制文件 |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE summary 过滤 + 回归 E24（TDD）  
3. BE estimateVelocity + CSV（TDD）  
4. FE 过滤条 + 速度卡 + 导出  
5. CLI 1.39.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- 无过滤回归 E24 计数  
- project/label/cycle 组合；跨租户；未知 id  
- velocity：无估点、跨日完成、软删 Issue 不计  
- CSV 头/行与 JSON 对账  
- 权限 viewer 可读；spy：无 fire_webhooks / 无 formula emit；不触碰 webhook stats / SLA exceptions / activity cursors  
- CLI 1.39.0 pins + 新参数/子命令  

---

## 附录 · runners-up（供 E56+；若 Yuri 改选可替换本草案）

1. **SLA policy 级营业时/例外覆盖 thin**（仍砍完整优先级矩阵 / 国家包）— E53 WS 例外再沉淀后、多品牌支持台有强信号时开。  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢。  
3. **Webhook 失败告警薄刀**（Inbox/email 当死信超过阈值）— 可挂在 E54 之后；本轮刻意不做告警引擎。  

（Formula emit — 永不本轮。重做 E50–E54 SLA/webhook/Activity 表面 — 无增量，不推。原生移动 / Initiative 依赖图 / 真 GitHub App — Roadmap 排除或过厚。）

## CLI 版本

**1.39.0**
