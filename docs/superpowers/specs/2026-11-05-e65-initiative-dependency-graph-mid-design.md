# E65 Design：Initiative 依赖图 mid — blocks/blocked_by/relates_to · CLI 1.49.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E65  
基线拟：`sprint/E64-S1` @ `ab746df`（全文 `ab746dfebda210d31f13da5086a41c20a27061f1`；E64 design 基线 `63d7c4f`；E63 tip `0a53ef7` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E65-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E66**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e65-initiative-dependency-graph-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E65-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E64 连续闭合 … → Search FTS（E60）→ Insights 共享（E61）→ 评论 FTS（E62）→ Customer 公开状态门户（E63）→ **假日包扩容 mid（E64：EU/UK + 2027 · CLI 1.48.0）**。

E64 附录 runners-up（不绑定）：

1. **Activity 实时/推送加厚**（WS 扇出 / 浏览器 Notification / FCM）— 单列易溢；非「明显最优」；**默认不重开**  
2. **Initiative 依赖图 mid**（Initiative↔Initiative blocks/blocked_by + FE 轻量关系条；仍砍甘特精修）— E10 后置项 → **本草案收之**  
3. **Customer 门户再厚**（公开回复线程 / Form 成功页深链）— E63 仅隔 E64 一轮；**prefer skip**（非本轮最高 ROI）

代码实证 @ `ab746df`：

| 面 | 现状 |
|----|------|
| Initiative | E10：`initiatives` + `initiative_projects`；健康汇总挂 Project；详情/列表/**无** Initiative↔Initiative 边 |
| Issue Relations | E20：`issue_relations`（`blocks` / `is_blocked_by` / `relates_to` / …）；列表徽章；可作模式参考，**勿混表** |
| 假日包 | E58→E64 弧刚闭（CN/US/EU/UK × 2026/2027）；本轮宜 **轮换离开** |
| Customer 公开 | E63 刚闭；隔一轮不够，再厚非最高 ROI |
| Search / Insights | E60–E62 / E59–E61 刚闭；宜轮换离开 |
| Activity | E52 watching+反应+薄铃铛；E23 有 `WorkspaceRealtimeHub`；**无**浏览器 Notification / FCM 产品化 |
| Formula | E40 D2/D7 **永不 emit** |
| Roadmap 扫描 | E10 明示 Initiative 依赖图后置；要求轮换离开假日包/Customer/Search/Insights；Activity Push 勿默认；依赖图可用 IssueRelation 同构薄刀做成 mid，单 sprint 可交付 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Initiative 依赖图 mid**：新表 `initiative_relations`（source_id/target_id/type∈{blocks,is_blocked_by,relates_to}）；同 WS 校验；禁自环；可选环检测；API CRUD + 详情嵌入；列表轻量 `blocksCount`/`blockedByCount`；FE 详情「依赖」区（增删+方向展示，**非**甘特/力导向大图）；CLI **1.49.0**；**无** Push、**无** 假日/Customer/Search 再开 | **中厚**；接 E64 #2；对齐 Linear Initiative 依赖叙事；复用 E20 关系语义；单 sprint 可交付 |
| B | Activity Push（WS 扇出 / Notification / FCM） | 单列易溢；E52 已刻意砍；**默认不重开** |
| C | Customer 门户再厚 | E63 仅隔一轮；任务 prefer skip |
| D | 再开假日包（州包/ICS/2028） | **刚闭 E64**；与 rotate OFF 冲突 |
| E | 再开 Search / Insights / Webhook / Formula emit / 真 GitHub App | 刚闭或过厚/永不 |
| F | 仅在 Initiative 描述里手写「依赖 XXX」无结构化 | **过薄**；不可筛/不可 CLI |

**建议拍板：A（Initiative 依赖图 mid）。**  
Activity Push、Customer 门户再厚、（可选）下一刀甘特精修列入附录 runners-up。

自检：同构关系模型、环/自环、跨租户、FE 轻量条、CLI **1.49.0**、非目标与 no-emit 已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 单列易溢；非「明显最优」；任务明确勿默认 |
| Customer 门户再厚 | E63 刚交且仅隔假日包一轮；prefer skip |
| 假日包再扩 / ICS / 州包 | 刚闭 E64；非目标 |
| 再开 Search / Insights | 刚闭；轮换离开 |
| 甘特大图 / 真 GitHub App | 过厚 |

### Why this Epic now（一句话）

E10 把 Initiative 立成「多 Project 战略容器」，但 **Initiative 之间仍无法表达阻塞/相关**——路线图对齐只能靠口头或 Issue 级关系迂回；E64 假日包弧刚闭后轮换离开日历/门户/Search/Insights，用中厚刀补上 **同构于 E20 的 Initiative 依赖边 + 详情轻量条 + CLI**，正好把「能挂项目」抬到「能表达战略先后」，且不重开 Push、甘特或门户大战。

---

## 1. 目标

成功标准：Workspace **writer+** 可在同 WS 内为 Initiative 建立/删除 **blocks / is_blocked_by / relates_to** 关系；viewer+ 可读；详情展示依赖列表；列表可选返回计数；跨租户 404；禁自环；CLI **1.49.0**；**不**引入甘特/力导向图、**不** Activity Push、**不**改 E57–E64 邻面主表面、**不** formula emit。

### A · 模型（BE）

- 新表 `initiative_relations`：  
  - `id`、`workspace_id`、`source_initiative_id`、`target_initiative_id`  
  - `relation_type`：`blocks` | `is_blocked_by` | `relates_to`（Q1a；本轮 **不含** duplicates/parent）  
  - `created_by`、`created_at`  
  - Unique `(source, target, relation_type)`；Index `(workspace_id, source)` / `(workspace_id, target)`  
- alembic 新修订（建议 `w9f0a1b2c3d7` 一类）  
- **不**复用 `issue_relations` 表（实体轴不同；避免 FK 混乱）

### B · API（BE）

- `GET /api/initiatives/{id}/relations` → `{ items: [{ id, type, direction, initiative: { id, name, status } }] }`  
- `POST /api/initiatives/{id}/relations` body `{ targetInitiativeId, type }`  
  - 写权限 writer+；两端须同 WS；自环 → 400  
  - `is_blocked_by` 可存原样或规范化为反向 `blocks`（**Q2a：存调用方字面 type，读时双向展开**）  
- `DELETE /api/initiatives/{id}/relations/{relationId}`  
- 列表/详情加法：可选 `blocksCount` / `blockedByCount`（Q3a 详情默认带；列表 opt-in `?include=relationCounts`）  
- 环检测：**Q4a** POST 时若 `blocks` 链成环 → 400（深度 cap 32）；`relates_to` 不参与环检

### C · FE

- Initiative 详情：「依赖」折叠区——列出阻塞/被阻塞/相关；增删控件  
- 列表：可选小徽章计数（若 payload 有 counts）  
- **不做**画布/甘特/拖拽排程  
- vitest：关系 flatten/方向文案；build ok

### D · CLI **1.49.0**

- `opentask initiative relations list <id>`  
- `opentask initiative relation add <id> --target <id> --type blocks|is_blocked_by|relates_to`  
- `opentask initiative relation remove <id> --relation-id <rid>`  
- pins → **1.49.0**

### E · 安全 / 租户 / no-emit

- 跨 WS 目标 → 404  
- 公开 Customer / 假日包 / Search 路径不动  
- formula **no-emit**；关系变更 **Q5a**：不新增 webhook 事件名（本轮静默；后置 `initiative.relation_changed`）  
- **不**改 E57–E64 主表面（仅 CLI version pins）

---

## 2. 非目标

- 甘特图 / 力导向依赖画布 / 关键路径排程  
- Activity Push / 浏览器 Notification / FCM / 实时 WS 产品化加厚  
- Customer 门户再厚、假日包 ICS/州包/2028  
- Search / Insights 再开  
- Issue↔Initiative 跨轴依赖、PGE 复活  
- 真 GitHub App、原生移动  
- Formula emit  
- 远程 push / 开 PR / 自开 E66

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | CRUD 关系；同 WS；自环 400；跨租户 404 |
| B | blocks 环检测（Q4a）；relates_to 可多对；计数正确 |
| C | FE 详情依赖区增删；无甘特；vitest+build |
| D | CLI **1.49.0** + relations 子命令 + pins |
| E | 无新 webhook 事件名（Q5a）；不改 E57–E64 邻面；formula no-emit spy |
| 门禁 | BE 定向（E65+E10 initiatives）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E66 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Initiative 依赖图 mid**（方案 A）；结构化关系 + 详情轻量条 + CLI；**无** Push / 甘特 / 假日/Customer 再开 |
| D2 | 独立表 `initiative_relations`；语义对齐 E20 子集（blocks / is_blocked_by / relates_to） |
| D3 | 同 WS + 禁自环；blocks 链环检测 |
| D4 | FE 列表/详情轻量呈现；不做画布 |
| D5 | 关系变更本轮不新增 webhook 事件名 |
| D6 | CLI = **1.49.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E57–E64 邻面；不 push；不自开 E66 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 支持哪些 type？ | **Q1a** `blocks` / `is_blocked_by` / `relates_to`；备选 Q1b 再加 `duplicates`（战略容器上语义弱） |
| Q2 | `is_blocked_by` 存储？ | **Q2a** 按调用方字面存储；GET 从两端边展开；备选 Q2b 一律规范化成 `blocks` 反向边（写路径更吵） |
| Q3 | 列表是否总带 counts？ | **Q3a** 详情默认带；列表 `?include=relationCounts` opt-in；备选 Q3b 列表总带（多一次聚合） |
| Q4 | 环检测？ | **Q4a** 仅对 `blocks`/`is_blocked_by` 做有向环拒绝；备选 Q4b 不检环（易形成死锁叙事） |
| Q5 | webhook？ | **Q5a** 本轮不新增事件名、不 fire 新出站；备选 Q5b 发 `initiative.updated` 泛化事件（易噪） |
| Q6 | CLI 表面？ | **Q6a** `initiative relations list` + `relation add/remove`；备选 Q6b 仅 JSON dump（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic `initiative_relations` + 模型（TDD）  
3. API CRUD + 环检 + 跨租户（TDD）  
4. 详情/列表 counts（TDD）  
5. FE 依赖区 + vitest  
6. CLI 1.49.0  
7. no-emit spy + acceptance

---

## 7. 测试要点

- add blocks A→B；list 两端可见方向  
- 自环 400；跨 WS target 404；viewer 写 403  
- 环：A blocks B blocks A → 第二次 400  
- relates_to 不触发环检  
- counts 与边一致  
- spy：无新 webhook 事件；不触 E64 holiday apply / E63 status-link / E57 alert / E61 share；formula no-emit  
- CLI 1.49.0 pins  
- FE vitest；build ok

---

## 附录 · runners-up（供 E66+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification / 可选 FCM）— E52/E23 后再评估；单列易溢；非「明显最优」不重开。  
2. **Customer 门户再厚 thin-mid**（公开回复线程 UI / Form 成功页深链 status URL）— E63 已隔假日包一轮；本轮为 Initiative 让路后再评。  
3. **Initiative 甘特/时间线精修**（依赖边之上的排程视图）— 本 Epic 刻意砍画布；有关系数据后再开。

（备选扫描但本轮不推：假日包 ICS/州包/2028 — 刚闭 E64。再开 Search/Insights — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App — 过厚。Formula emit — 永不。重做 E52–E64 表面 — 无增量，不推。）

## CLI 版本

**1.49.0**
