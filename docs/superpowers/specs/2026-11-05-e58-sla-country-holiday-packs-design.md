# E58 Design：国家/地区假日包 mid — 精选包一键合并进 WS/policy exceptions · CLI 1.42.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E58  
基线拟：`sprint/E57-S1` @ `0ef66a6`（全文 `0ef66a6904a9d8cfa4b25ea9c8a24ebf035a4d29`；E57 design 基线 `5752cb4`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E58-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E59**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e58-sla-country-holiday-packs-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E58-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E57 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 → Formula query → Activity Feed → SLA first-response → Formula Display → SLA business hours（E50）→ webhook pack（E51）→ Activity 加厚（E52）→ SLA 例外日（E53）→ Webhook 可观测（E54）→ Insights 效能加厚（E55）→ SLA policy 日历覆盖（E56）→ **Webhook 死信告警（E57：阈值 Inbox/邮件 + 去重 + 可选自动停用）**。

E57 附录 runners-up（不绑定）：

1. **国家/地区假日包 mid**（CN/US/… 精选包一键合并进 WS 或 policy.calendar.exceptions；按年；仍砍 ICS 订阅 / 冲突矩阵）— E56 覆盖已齐后下一刀日历增强；E57 为轮换出站弧让路 → **本草案收之**  
2. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非本轮最优  
3. **Insights 再厚 / 效能日报**（多 label OR、持久化「我的报表」、可选邮件 digest）— E55 已隔 E56+E57 两轮；可作 runners-up

代码实证 @ `0ef66a6`：

| 面 | 现状 |
|----|------|
| SLA 日历 | E50 周窗 + E53 WS exceptions（`closed`/`forced_open`）+ E56 policy.calendar 字段级覆盖；`add_business_minutes` / recompute 共用；**无**国家/地区假日包、**无**一键导入、**无**按年刷新、**无**包元数据 |
| FE SLA | `settings/sla`：周窗 + 例外列表手工增删 + policy「日历覆盖」；**无**「应用假日包」入口 |
| CLI | **1.41.0**；`sla business-hours … exceptions …` + policy `--calendar-json`；**无** holiday-packs 子命令 |
| Webhook | E44→E51→E54→E57 出站弧已闭合（账本→pack→可观测→告警）；本轮宜轮换离开 |
| Activity | E52 watching+反应+铃铛；**无** Push / 浏览器 Notification |
| Insights | E55 切片+估点速度+CSV；再厚仍易变报表构建器；已隔两轮可作附录 |
| Search | 现网 `ILIKE` 多实体搜索；**无** FTS/tsvector |
| Customer | 内部 Customers + Requests + Forms 联动；**无**公开门户 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | 厚 Linear 主面近期已交；E57 闭合出站告警后，最高 ROI 缺口回到 **SLA 日历可用性**——手工录例外对支持台国庆/感恩节不可规模化；精选假日包正好接在 E53/E56 之上，且不重开 Push / ICS / 冲突矩阵 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **国家/地区假日包 mid**：仓内精选包（建议 **CN + US**，按年；`closed` 日为主，CN 可选调休 `forced_open`）；`POST …/holiday-packs/apply` 合并进 **WS business_hours.exceptions** 或 **policy.calendar.exceptions**；冲突策略明确；应用后按既有 E50/E56 路径重算时钟（cap 500）；FE 假日包选择器 + 预览 diff；CLI **1.42.0**；**无** ICS 订阅 / **无** 冲突矩阵 / **无** Push / **无** 在线拉取第三方 API | **中厚且闭合 E50→E53→E56→E58 日历弧**；轮换离开刚闭合的 webhook 弧；单 sprint 可交付；版权面用「精选静态包 + 注明来源/年份」可控 |
| B | Insights 再厚 / 效能日报（多 label OR、持久化「我的报表」、可选邮件 digest） | E55 已隔两轮，ROI 高；但假日包是 E57 明确 #1 让路项，且日历手工债对支持台更痛；作 runners-up |
| C | Activity 实时/Push（WS 扇出 / 浏览器 Notification / FCM） | 单列易溢；仓内 realtime≠产品闭环；**默认不重开** |
| D | Search FTS mid（Postgres tsvector / SQLite FTS5 双方言） | 用户面有价值但偏基建；方言分叉测本大；作 runners-up |
| E | Customer 公开门户 / 真 GitHub App / Initiative 依赖图 / Formula emit | 门户·App·依赖图偏厚或排除；emit **永不** |
| F | 仅「贴一份 CN 2026 JSON 到 docs」无 apply API | **过薄**；与 prefer mid-thick 冲突 |

**建议拍板：A（国家/地区假日包 mid）。**  
Insights 再厚/日报、Search FTS、Activity Push 列入附录 runners-up。

自检：包形状、apply 目标（WS vs policy）、合并/冲突、重算、FE/CLI **1.42.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Insights 再厚 / 效能日报 | 高 ROI 且已沉淀；但 E57 附录把假日包列为轮换出站弧后的下一刀；日历手工债更贴支持台 SLA |
| Activity 实时/Push | 单列易溢；非「明显最优」；不重开 |
| Search FTS | 偏基建；方言双栈测本 |
| Customer 门户 / GitHub App / Initiative 依赖图 | 过厚或排除 |
| 再开 webhook 表面 / Formula emit / 重做 E52–E57 | 无增量或破 D7；永不本轮 |

### Why this Epic now（一句话）

E50→E53→E56 已让 owner「能配周窗、能录例外、能按 policy 覆盖」，但国庆/感恩节仍靠人肉逐日录入——E57 刚闭合出站告警弧后轮换回来，用中厚刀把 **精选国家包一键合并 + 预览 + 按年** 补上，正好闭合 SLA 日历产品弧，且不重开 Push、ICS 订阅或冲突矩阵大战。

---

## 1. 目标

成功标准：owner 可浏览仓内精选假日包（至少 **CN、US**；按 **公历年**）；可 **预览** 将包合并进目标日历（WS `business_hours.exceptions` 或某 `SlaPolicy.calendar.exceptions`）的增删/覆盖 diff；确认后 **apply** 写入并触发既有重算路径（WS 变更→WS 钟；policy 变更→仅该 policy；cap 500）；FE 在既有 `settings/sla` 薄加「假日包」折叠；CLI **1.42.0**；跨租户隔离；**不**引入 ICS/Outlook 订阅、**不**在线拉取政府 API、**不**多 policy 冲突矩阵、**不** Activity Push、**不**改 E57 webhook 告警 / E55 Insights 主表面、**不** formula emit。

### A · 假日包模型（BE）

- 包为 **静态只读资源**（建议落 `backend/opentask/data/holiday_packs/{region}/{year}.json` 或等价 Python 常量模块；**Q1**）  
  - 形状建议：`{ region: "CN"|"US"|…, year: 2026, name, sourceNote, holidays: [{ date: YYYY-MM-DD, kind: "closed"|"forced_open", windows?: [...], label?: string }] }`  
  - `kind` **必须**落在 E53 已支持的 `closed` / `forced_open`；未知 kind → 包校验失败（启动或加载时）  
  - CN：法定假 `closed` + 调休上班日 `forced_open`（若该年有）  
  - US：联邦常见假 `closed`；**不做**州级变体（砍）  
- `GET /api/sla/holiday-packs` → 列表（region/year/name/sourceNote/count）  
- `GET /api/sla/holiday-packs/{region}/{year}` → 包全文  
- 非法 region/year → 404；**不**按租户隔离包目录（全局只读）

### B · 预览与 Apply

- 目标建议 **Q2a**：`target=workspace`（默认）| `target=policy&policyId=`  
  - workspace → 合并进 `workspaces.business_hours.exceptions`（E53）  
  - policy → 合并进 `sla_policies.calendar.exceptions`；若 policy.calendar 为 null，apply 时 **物化**一层仅含 exceptions 的 overlay（其它字段仍 inherit；对齐 E56 字段级语义）  
- 冲突策略建议 **Q3a**：**同 date 以包为准覆盖**（pack wins）；包外既有例外保留；返回 `{ added, replaced, unchanged, skipped }`  
  - 备选 Q3b：同 date 跳过（keep existing）— 更保守但「一键国庆」体感弱  
- `POST /api/sla/holiday-packs/{region}/{year}/preview` body `{ target, policyId?, yearAlreadyApplied? }` → diff，**不写库**  
- `POST /api/sla/holiday-packs/{region}/{year}/apply` → 写库 + 重算（复用 E50/E56 recompute；cap 500）  
- 幂等建议 **Q4a**：同一 `(workspace|policy, region, year)` 再 apply → 结果收敛（覆盖后集合等于「非包日既有 ∪ 包日」）；可选轻量 `applied_holiday_packs` JSON 账本仅作 FE「已应用」徽章（非强制唯一约束）  
- 权限：owner 写；member+ 可读包列表/预览（与 SLA 设置对齐）  
- 跨租户 policyId → 404

### C · 存储 / migration

- **包本体不进 DB**（静态文件/模块）  
- 可选 alembic：`workspaces.applied_holiday_packs` / `sla_policies.applied_holiday_packs` JSON nullable（`[{region, year, appliedAt}]`）— 见 **Q4**；若砍账本则零迁移，仅改 exceptions  
- SQLite 测友好  
- **禁止**新 webhook 事件；**禁止**改 E57 alert 路径；**禁止** priority/conflict-rank 列

### D · FE

- 既有 `settings/sla`：折叠「假日包」—— region + year 选择、包说明、预览表（added/replaced）、确认应用、目标切换（本 WS / 某 policy）  
- policy 日历覆盖区可显示「从假日包填充」快捷入口（同一 API）  
- vitest：merge/conflict 纯函数（pack wins / keep-existing 若改选）；非法 date 过滤  
- **不做**月历拖拽大战、ICS 上传、在线「同步最新」按钮连外网

### E · CLI **1.42.0**

- `sla holiday-packs list`  
- `sla holiday-packs show --region CN --year 2026`  
- `sla holiday-packs preview --region CN --year 2026 [--policy-id ID]`  
- `sla holiday-packs apply --region CN --year 2026 [--policy-id ID] [--yes]`  
- 既有 `business-hours` / policy calendar 保留  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.42.0**

### F · 安全 / 租户 / no-emit

- apply 写：owner；包只读：认证成员  
- 跨租户 404  
- **不**改 Activity / Insights / Webhook 告警主表面  
- formula **no-emit**；apply/recompute 路径 spy 不借机 `fire_webhooks`（除既有 SLA 时钟事件若本就存在——**本 Epic 不新增**事件名；若触及既有 `sla_*` emit 则保持 E45+ 既有行为，不扩包）  
- 包内容为静态；**禁止**运行时 HTTP 拉取外部日历源

## 2. 非目标

- ICS / Outlook / Google Calendar 订阅同步  
- 在线拉取政府/第三方假日 API；包自动逐年爬取  
- 州/省/市细粒度包（US 州假、CN 地方调休变体）  
- 多 SlaPolicy 冲突优先级矩阵 / 按客户选包规则引擎  
- Activity Push / FCM / 浏览器 Notification  
- Insights 报表构建器 / 效能邮件日报（本轮不做，见附录）  
- Search FTS、Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动  
- 重做 E57 webhook 告警 / 改 E51 pack/HMAC / 改 E55 Insights 主表面  
- Formula 物化 emit（E40 D2/D7）  
- 远程 push / 开 PR / 自开 E59

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | `list/show` 返回 CN+US（或拍板区域）指定年包；非法 region/year → 404；包 kind 仅 closed/forced_open |
| B | preview 不写库；apply 合并进 WS 或 policy.calendar.exceptions；Q3a 同日包覆盖；非包日保留 |
| C | apply 后触发既有重算（WS 全量 / policy 仅本 policy；cap 500）；可选 applied 账本；alembic 可升级或明确零迁移 |
| D | FE 假日包折叠 + 预览 diff + 应用到 WS/policy；vitest；build ok |
| E | CLI **1.42.0** + holiday-packs list/show/preview/apply + version pins |
| F | 无 ICS/外网拉取；无新 E51 事件名；formula no-emit；不改 E55/E57 主表面 |
| 门禁 | BE 定向（E58+E56+E53/E50 相关）+ 全量记 passed/skip；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E59 |

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **国家/地区假日包 mid**（方案 A）；精选静态包 + preview/apply 合并进 exceptions；**无** ICS / 外网同步 / 冲突矩阵 / Push / Insights 再厚 |
| D2 | 包为仓内静态只读（按 region+year）；首批 **CN + US**；kind ⊆ E53 `{closed, forced_open}` |
| D3 | 默认 apply 目标 = **WS business_hours.exceptions**；可选 policy.calendar.exceptions（null overlay 时物化 exceptions-only） |
| D4 | 冲突 = **pack wins**（同 date 覆盖）；包外例外保留；preview 必经或 CLI `--yes` 跳过确认 |
| D5 | FE 落点 = 既有 `settings/sla` 薄加；不新开导航 |
| D6 | CLI = **1.42.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不改 E55 Insights / E57 webhook 告警主表面；非目标见 §2；不 push；不自开 E59 |

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | 包落地形态？首批区域与年份？ | **Q1a** 静态 JSON/模块 `holiday_packs/{region}/{year}`；首批 **CN+US**；至少提供 **2026**（与「Today's date」对齐），允许同结构加 2025/2027 文件；备选 Q1b 仅 Python 常量单文件（少文件但难审 diff） |
| Q2 | apply 默认目标？ | **Q2a** 默认 WS；`--policy-id` / body.policyId 改打 policy overlay；备选 Q2b 强制每次显式选目标（FE 可，CLI 吵） |
| Q3 | 同 date 冲突？ | **Q3a pack wins**（覆盖 kind/windows/label）；备选 Q3b keep existing；Q3c 拒绝 apply（过严） |
| Q4 | 是否持久化「已应用包」账本？ | **Q4a** 轻量 JSON 数组账本（WS/policy 各一）供徽章与幂等展示；备选 Q4b 不记账本、仅看 exceptions 内容 |
| Q5 | CN 调休 `forced_open` 的 windows？ | **Q5a** 缺省 windows → 用「工作日默认窗」或当日原周窗（对齐 E53 Q2 既有语义）；备选 Q5b 包内写死 09:00–18:00 |
| Q6 | 年界与跨年包？ | **Q6a** 单年包；跨年法定假（少见）按 date 落入对应 year 文件；apply 一次一年；备选 Q6b 允许 multi-year zip（偏厚，砍） |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. 静态包 CN/US 2026 + loader/校验（TDD）  
3. BE preview/apply merge + 重算挂钩（TDD；回归 E53/E56）  
4. FE 假日包折叠 + 预览  
5. CLI 1.42.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- list 含 CN/US 2026；show 含 closed（+ CN forced_open 若有）  
- preview 不落库；apply 后 exceptions 含包日；非包日保留  
- 同日既有 closed vs 包 forced_open → Q3a 包覆盖  
- policy 目标：null calendar → 物化 exceptions-only overlay；effective 继承 WS windows/tz  
- 再 apply 同包幂等收敛  
- 跨租户 policy；非法 region/year；包内非法 kind 加载失败  
- recompute cap 行为与 E50/E56 一致  
- spy：不新增 webhook 事件名；不触 E57 alert eval / Insights export  
- CLI 1.42.0 pins + list/show/preview/apply  

---

## 附录 · runners-up（供 E59+；若 Yuri 改选可替换本草案）

1. **Insights 再厚 / 效能日报 mid**（多 label OR、持久化「我的报表」、可选邮件 digest；仍砍拖拽报表构建器）— E55 已隔 E56+E57；假日包让路后下一刀效能面。  
2. **Search FTS mid**（Postgres `tsvector` + SQLite FTS5 或统一 trigram 降级；Issue/Project/Doc）— 现网 ILIKE 可规模化前的基建刀；方言测本需控。  
3. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52 铃铛后再评估；单列易溢；非「明显最优」不重开。

（备选扫描但本轮不推：Customer 公开门户、真 GitHub App、Initiative 依赖图、原生移动 — Roadmap 排除或过厚。Webhook 再厚 / PagerDuty — 出站弧刚闭，轮换离开。Formula emit — 永不本轮。重做 E52–E57 表面 — 无增量，不推。）

## CLI 版本

**1.42.0**
